"""
Payment Service - Handles X402 payments with USDC transferWithAuthorization
"""
import time
import hashlib
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal

from web3 import Web3
from web3.contract import Contract
from eth_account import Account
from eth_account.messages import encode_defunct, encode_typed_data

from app.config import get_settings

settings = get_settings()


# ERC-3009 transferWithAuthorization signature
TRANSFER_WITH_AUTHORIZATION_TYPEHASH = Web3.keccak(
    text="TransferWithAuthorization(address from,address to,uint256 value,uint256 validAfter,uint256 validBefore,bytes32 nonce)"
)

# USDC Contract ABI (minimal - only what we need)
USDC_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "validAfter", "type": "uint256"},
            {"name": "validBefore", "type": "uint256"},
            {"name": "nonce", "type": "bytes32"},
            {"name": "v", "type": "uint8"},
            {"name": "r", "type": "bytes32"},
            {"name": "s", "type": "bytes32"}
        ],
        "name": "transferWithAuthorization",
        "outputs": [],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    }
]


class PaymentService:
    """Service for handling X402 Protocol payments"""

    def __init__(self):
        try:
            print(f"Initializing PaymentService with RPC: {settings.BASE_RPC_URL}")

            self.w3 = Web3(Web3.HTTPProvider(settings.BASE_RPC_URL))

            # Check connection
            if not self.w3.is_connected():
                raise Exception(f"Failed to connect to RPC at {settings.BASE_RPC_URL}")

            print(f"✅ Connected to Base RPC (Chain ID: {self.w3.eth.chain_id})")

            self.usdc_address = Web3.to_checksum_address(settings.USDC_CONTRACT_ADDRESS)
            self.server_address = Web3.to_checksum_address(settings.SERVER_WALLET_ADDRESS)

            print(f"USDC Contract: {self.usdc_address}")
            print(f"Server Address: {self.server_address}")

            # Initialize USDC contract
            self.usdc: Contract = self.w3.eth.contract(
                address=self.usdc_address,
                abi=USDC_ABI
            )

            # Server account for signing transactions
            self.server_account = Account.from_key(settings.SERVER_PRIVATE_KEY)

            print(f"✅ PaymentService initialized successfully")

        except Exception as e:
            print(f"❌ PaymentService initialization failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise

    def create_payment_requirements(
        self,
        task_id: str,
        amount_usd: float,
        user_address: Optional[str] = None
    ) -> Dict:
        """
        Create X402 payment requirements for a task result

        Args:
            task_id: Task ID
            amount_usd: Amount in USD
            user_address: User's wallet address (optional)

        Returns:
            Payment requirements dict with X402 headers
        """
        # Convert USD to USDC (6 decimals)
        amount_usdc = int(Decimal(str(amount_usd)) * Decimal('1000000'))

        # Generate nonce (unique per payment)
        nonce = Web3.keccak(text=f"{task_id}-{int(time.time())}")

        # Validity window (1 hour from now)
        valid_after = int(time.time())
        valid_before = valid_after + 3600  # 1 hour

        # EIP-712 domain for Base Sepolia USDC
        # IMPORTANT: name must be "USDC", not "USD Coin" for Base Sepolia!
        domain = {
            "name": "USDC",
            "version": "2",
            "chainId": 84532,  # Base Sepolia
            "verifyingContract": self.usdc_address
        }

        # Payment message
        message = {
            "from": user_address if user_address else "0x0000000000000000000000000000000000000000",
            "to": self.server_address,
            "value": amount_usdc,
            "validAfter": valid_after,
            "validBefore": valid_before,
            "nonce": nonce.hex()
        }

        return {
            "payment_required": True,
            "amount": amount_usd,
            "amount_usdc": amount_usdc,
            "currency": "USDC",
            "chain": "base-sepolia",
            "chain_id": 84532,
            "recipient": self.server_address,
            "contract": self.usdc_address,
            "valid_after": valid_after,
            "valid_before": valid_before,
            "nonce": nonce.hex(),
            "domain": domain,
            "message": message,
            "task_id": task_id,
            "headers": {
                "X-Payment-Required": "true",
                "X-Payment-Amount": str(amount_usd),
                "X-Payment-Currency": "USDC",
                "X-Payment-Chain": "base-sepolia",
                "X-Payment-Address": self.server_address,
                "X-Payment-Contract": self.usdc_address
            }
        }

    async def verify_signature(
        self,
        from_address: str,
        amount_usdc: int,
        valid_after: int,
        valid_before: int,
        nonce: str,
        signature: Dict
    ) -> bool:
        """
        Verify EIP-712 signature for transferWithAuthorization

        Args:
            from_address: Sender address
            amount_usdc: Amount in USDC (with 6 decimals)
            valid_after: Valid after timestamp
            valid_before: Valid before timestamp
            nonce: Unique nonce
            signature: Signature dict with v, r, s

        Returns:
            True if signature is valid
        """
        try:
            # EIP-712 domain
            # IMPORTANT: name must be "USDC" for Base Sepolia!
            domain = {
                "name": "USDC",
                "version": "2",
                "chainId": 84532,
                "verifyingContract": self.usdc_address
            }

            # Message
            # Convert nonce to bytes for bytes32 type in EIP-712
            # eth_account requires bytes objects for bytes32 fields
            nonce_hex = nonce if nonce.startswith('0x') else f"0x{nonce}"
            nonce_bytes = bytes.fromhex(nonce_hex[2:])  # Remove 0x and convert

            print(f"Verifying signature - nonce: {nonce}")
            print(f"  nonce_hex: {nonce_hex}")
            print(f"  nonce_bytes length: {len(nonce_bytes)}, type: {type(nonce_bytes)}")
            print(f"  nonce_bytes: {nonce_bytes.hex()}")

            # Ensure nonce is exactly 32 bytes
            if len(nonce_bytes) != 32:
                raise ValueError(f"Nonce must be exactly 32 bytes, got {len(nonce_bytes)} bytes")

            message = {
                "from": Web3.to_checksum_address(from_address),
                "to": self.server_address,
                "value": amount_usdc,
                "validAfter": valid_after,
                "validBefore": valid_before,
                "nonce": nonce_bytes  # Must be bytes for bytes32 type
            }

            # Type data for EIP-712 (exactly as in working example)
            typed_data = {
                "types": {
                    "EIP712Domain": [
                        {"name": "name", "type": "string"},
                        {"name": "version", "type": "string"},
                        {"name": "chainId", "type": "uint256"},
                        {"name": "verifyingContract", "type": "address"}
                    ],
                    "TransferWithAuthorization": [
                        {"name": "from", "type": "address"},
                        {"name": "to", "type": "address"},
                        {"name": "value", "type": "uint256"},
                        {"name": "validAfter", "type": "uint256"},
                        {"name": "validBefore", "type": "uint256"},
                        {"name": "nonce", "type": "bytes32"}
                    ]
                },
                "primaryType": "TransferWithAuthorization",
                "domain": domain,
                "message": message
            }

            # Encode and recover signer (exactly as in working example)
            signable_message = encode_typed_data(full_message=typed_data)

            # Reconstruct signature
            v = signature['v']
            r = signature['r']
            s = signature['s']

            # Convert r and s to integers (they come as decimal strings from frontend)
            if isinstance(r, str):
                # Try to parse as decimal first (from BigInt.toString()), then hex
                try:
                    r_int = int(r)  # Decimal string
                except ValueError:
                    r_int = int(r, 16) if r.startswith('0x') else int(r, 16)
            else:
                r_int = r

            if isinstance(s, str):
                # Try to parse as decimal first (from BigInt.toString()), then hex
                try:
                    s_int = int(s)  # Decimal string
                except ValueError:
                    s_int = int(s, 16) if s.startswith('0x') else int(s, 16)
            else:
                s_int = s

            r_bytes = r_int.to_bytes(32, 'big')
            s_bytes = s_int.to_bytes(32, 'big')

            sig_bytes = r_bytes + s_bytes + bytes([v])

            # Recover address
            recovered = Account.recover_message(signable_message, signature=sig_bytes)

            print(f"Recovered address: {recovered}")
            print(f"Expected address: {from_address}")

            return recovered.lower() == from_address.lower()

        except Exception as e:
            print(f"Signature verification error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def execute_payment(
        self,
        from_address: str,
        amount_usdc: int,
        valid_after: int,
        valid_before: int,
        nonce: str,
        signature: Dict
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Execute transferWithAuthorization on USDC contract

        Args:
            from_address: Sender address
            amount_usdc: Amount in USDC (6 decimals)
            valid_after: Valid after timestamp
            valid_before: Valid before timestamp
            nonce: Unique nonce (bytes32)
            signature: Signature dict with v, r, s

        Returns:
            Tuple of (success, tx_hash, error_message)
        """
        try:
            # Verify signature first
            is_valid = await self.verify_signature(
                from_address, amount_usdc, valid_after,
                valid_before, nonce, signature
            )

            if not is_valid:
                return False, None, "Invalid signature"

            # Check if current time is within validity window
            current_time = int(time.time())
            if current_time < valid_after:
                return False, None, "Payment not yet valid"
            if current_time > valid_before:
                return False, None, "Payment expired"

            # Check server wallet has ETH for gas
            server_balance = self.w3.eth.get_balance(self.server_address)
            print(f"Server wallet balance: {self.w3.from_wei(server_balance, 'ether')} ETH")
            if server_balance == 0:
                return False, None, "Server wallet has no ETH for gas fees"

            # Check user has enough USDC
            user_usdc_balance = await self.check_balance(from_address)
            print(f"User USDC balance: {user_usdc_balance} USDC (need {amount_usdc / 1_000_000} USDC)")
            if user_usdc_balance * 1_000_000 < amount_usdc:
                return False, None, f"Insufficient USDC balance. Have {user_usdc_balance}, need {amount_usdc / 1_000_000}"

            # Prepare transaction
            from_addr = Web3.to_checksum_address(from_address)
            nonce_bytes = Web3.to_bytes(hexstr=nonce) if nonce.startswith('0x') else Web3.to_bytes(hexstr=f"0x{nonce}")

            v = signature['v']

            # Convert r and s to bytes32
            # They come as decimal strings from frontend (BigInt.toString())
            r_val = signature['r']
            s_val = signature['s']

            if isinstance(r_val, bytes):
                r_bytes = r_val
            elif isinstance(r_val, str):
                # Try decimal first, then hex
                try:
                    r_int = int(r_val)  # Decimal string
                except ValueError:
                    r_int = int(r_val, 16) if r_val.startswith('0x') else int(r_val, 16)
                r_bytes = r_int.to_bytes(32, 'big')
            else:
                r_bytes = r_val.to_bytes(32, 'big')

            if isinstance(s_val, bytes):
                s_bytes = s_val
            elif isinstance(s_val, str):
                # Try decimal first, then hex
                try:
                    s_int = int(s_val)  # Decimal string
                except ValueError:
                    s_int = int(s_val, 16) if s_val.startswith('0x') else int(s_val, 16)
                s_bytes = s_int.to_bytes(32, 'big')
            else:
                s_bytes = s_val.to_bytes(32, 'big')

            # Build transaction
            tx = self.usdc.functions.transferWithAuthorization(
                from_addr,
                self.server_address,
                amount_usdc,
                valid_after,
                valid_before,
                nonce_bytes,
                v,
                r_bytes,
                s_bytes
            ).build_transaction({
                'from': self.server_address,
                'nonce': self.w3.eth.get_transaction_count(self.server_address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })

            # Sign and send transaction
            print(f"Building transaction with:")
            print(f"  from: {from_addr}")
            print(f"  to: {self.server_address}")
            print(f"  value: {amount_usdc}")
            print(f"  validAfter: {valid_after}")
            print(f"  validBefore: {valid_before}")
            print(f"  v: {v}, r: {r_bytes.hex()[:10]}..., s: {s_bytes.hex()[:10]}...")

            signed_tx = self.server_account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

            print(f"Transaction sent: {tx_hash.hex()}")
            print(f"View on BaseScan: https://sepolia.basescan.org/tx/{tx_hash.hex()}")

            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            print(f"Transaction receipt status: {receipt['status']}")
            print(f"Gas used: {receipt['gasUsed']}")

            if receipt['status'] == 1:
                return True, tx_hash.hex(), None
            else:
                # Try to get revert reason
                try:
                    self.w3.eth.call(tx, block_identifier=receipt['blockNumber'])
                except Exception as call_error:
                    revert_reason = str(call_error)
                    print(f"Transaction reverted: {revert_reason}")
                    return False, tx_hash.hex(), f"Transaction failed: {revert_reason}"

                return False, tx_hash.hex(), "Transaction failed - check transaction on BaseScan"

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"Payment execution error: {error_msg}")
            import traceback
            traceback.print_exc()
            return False, None, error_msg

    async def check_balance(self, address: str) -> float:
        """
        Check USDC balance of an address

        Args:
            address: Wallet address

        Returns:
            Balance in USDC (human readable)
        """
        try:
            addr = Web3.to_checksum_address(address)
            balance_wei = self.usdc.functions.balanceOf(addr).call()
            # USDC has 6 decimals
            balance = float(balance_wei) / 1_000_000
            return balance
        except Exception as e:
            print(f"Balance check error: {e}")
            return 0.0


# Singleton instance
_payment_service = None

def get_payment_service() -> PaymentService:
    """Get or create PaymentService singleton"""
    global _payment_service
    if _payment_service is None:
        _payment_service = PaymentService()
    return _payment_service
