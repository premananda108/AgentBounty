"""
Wallet Router - Web3 wallet connection to Auth0 accounts
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from web3 import Web3
from eth_account.messages import encode_defunct
import httpx

from app.routers.auth import require_auth
from app.services.auth0_service import auth0_service
from app.config import settings


router = APIRouter(prefix="/api/wallet", tags=["wallet"])


# Request Models
class ConnectWalletRequest(BaseModel):
    """Request to connect wallet"""
    wallet_address: str
    signature: str
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "wallet_address": "0x1234567890123456789012345678901234567890",
                "signature": "0xabcdef...",
                "message": "Connect wallet 0x1234... to AgentBounty at 1234567890"
            }
        }


# Endpoints
@router.post("/connect")
async def connect_wallet(
    request: Request,
    data: ConnectWalletRequest,
    user: dict = Depends(require_auth)
):
    """
    Connect Web3 wallet to Auth0 account

    User must be logged in with Auth0 first.
    Verifies wallet ownership via signature.
    Saves wallet_address to Auth0 user_metadata.
    """

    auth0_user_id = user.get('sub')
    user_email = user.get('email', 'unknown')

    print(f"🔗 Connecting wallet for user: {user_email}")
    print(f"   Wallet: {data.wallet_address}")

    # Verify signature (proof of wallet ownership)
    w3 = Web3()
    message = encode_defunct(text=data.message)

    try:
        recovered_address = w3.eth.account.recover_message(
            message,
            signature=data.signature
        )

        if recovered_address.lower() != data.wallet_address.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Invalid signature. Expected {data.wallet_address}, recovered {recovered_address}"
            )

        print(f"   ✅ Signature verified")

    except Exception as e:
        print(f"   ❌ Signature verification failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Signature verification failed: {str(e)}"
        )

    # Save wallet to Auth0 user_metadata via Management API
    try:
        mgmt_token = await auth0_service.get_management_token()

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f'https://{settings.AUTH0_DOMAIN}/api/v2/users/{auth0_user_id}',
                headers={
                    'Authorization': f'Bearer {mgmt_token}',
                    'Content-Type': 'application/json'
                },
                json={
                    'user_metadata': {
                        'wallet_address': data.wallet_address.lower(),
                        'wallet_connected_at': datetime.utcnow().isoformat()
                    }
                },
                timeout=10.0
            )
            response.raise_for_status()

        print(f"   ✅ Wallet saved to Auth0 user_metadata")

    except Exception as e:
        print(f"   ❌ Failed to save wallet to Auth0: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save wallet: {str(e)}"
        )

    # Cache wallet in session for quick access
    request.session['wallet_address'] = data.wallet_address.lower()

    return {
        "success": True,
        "auth0_user_id": auth0_user_id,
        "wallet_address": data.wallet_address.lower(),
        "message": "Wallet connected successfully"
    }


@router.get("/info")
async def get_wallet_info(
    request: Request,
    user: dict = Depends(require_auth)
):
    """
    Get connected wallet information

    Returns wallet address and USDC balance.
    """

    auth0_user_id = user.get('sub')
    wallet_address = request.session.get('wallet_address')

    # If not in session, fetch from Auth0 user_metadata
    if not wallet_address:
        user_profile = await auth0_service.get_user_profile(auth0_user_id)

        if user_profile:
            user_metadata = user_profile.get('user_metadata', {})
            wallet_address = user_metadata.get('wallet_address')

            # Cache in session
            if wallet_address:
                request.session['wallet_address'] = wallet_address
                print(f"📦 Wallet loaded from Auth0: {wallet_address}")

    # Check USDC balance if wallet is connected
    balance = 0.0
    if wallet_address:
        try:
            from app.services.payment_service import get_payment_service
            payment_service = get_payment_service()
            balance = await payment_service.check_balance(wallet_address)
        except Exception as e:
            print(f"⚠️  Failed to check balance: {e}")

    return {
        "wallet_address": wallet_address,
        "connected": wallet_address is not None,
        "usdc_balance": balance,
        "chain": "base-sepolia",
        "chain_id": 84532
    }


@router.post("/disconnect")
async def disconnect_wallet(
    request: Request,
    user: dict = Depends(require_auth)
):
    """
    Disconnect wallet from session

    Note: Wallet remains in Auth0 user_metadata for history.
    Only clears from session cache.
    """

    # Clear from session
    wallet_address = request.session.pop('wallet_address', None)

    if wallet_address:
        print(f"🔌 Wallet disconnected from session: {wallet_address}")

    return {
        "success": True,
        "message": "Wallet disconnected from session"
    }


@router.get("/history")
async def get_wallet_history(
    user: dict = Depends(require_auth)
):
    """
    Get wallet connection history from Auth0

    Returns when wallet was connected.
    """

    auth0_user_id = user.get('sub')
    user_profile = await auth0_service.get_user_profile(auth0_user_id)

    if not user_profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    user_metadata = user_profile.get('user_metadata', {})

    return {
        "wallet_address": user_metadata.get('wallet_address'),
        "connected_at": user_metadata.get('wallet_connected_at'),
        "has_wallet": 'wallet_address' in user_metadata
    }
