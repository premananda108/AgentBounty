"""
Payment Router - API endpoints for payment processing
"""
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from typing import Dict, Optional

from app.services.payment_service import get_payment_service, PaymentService
from app.services.task_service import get_task_service, TaskService
from app.services.async_approval_service import get_async_approval_service, AsyncApprovalService
from app.services.magic_link_service import get_magic_link_service, MagicLinkService

router = APIRouter(prefix="/api/payments", tags=["payments"])


# Request/Response Models
class PaymentAuthorizationRequest(BaseModel):
    """Request model for payment authorization"""
    task_id: str = Field(..., description="Task ID requiring payment")
    from_address: str = Field(..., description="User's wallet address")
    amount_usdc: int = Field(..., description="Amount in USDC (6 decimals)")
    valid_after: int = Field(..., description="Valid after timestamp")
    valid_before: int = Field(..., description="Valid before timestamp")
    nonce: str = Field(..., description="Unique nonce (hex)")
    signature: Dict = Field(..., description="Signature with v (int), r (str), s (str)")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "from_address": "0x1234567890123456789012345678901234567890",
                "amount_usdc": 1500000,
                "valid_after": 1697000000,
                "valid_before": 1697003600,
                "nonce": "0x1234...",
                "signature": {
                    "v": 27,
                    "r": "12345678901234567890123456789012345678901234567890",
                    "s": "98765432109876543210987654321098765432109876543210"
                }
            }
        }


class PaymentResponse(BaseModel):
    """Response model for payment processing"""
    success: bool
    tx_hash: Optional[str] = None
    error: Optional[str] = None
    task_id: str
    amount_usd: float


class CIBAApprovalRequest(BaseModel):
    """Request model for CIBA approval"""
    task_id: str = Field(..., description="Task ID")
    user_id: str = Field(..., description="User ID from Auth0")
    amount: float = Field(..., description="Payment amount in USD")
    task_description: str = Field(..., description="Task description")


class CIBAStatusResponse(BaseModel):
    """Response model for CIBA status"""
    ciba_request_id: str
    status: str
    task_id: str
    amount: float
    expires_at: Optional[str] = None
    approved_at: Optional[str] = None


class CIBACallbackRequest(BaseModel):
    """Request model for CIBA callback (from Auth0)"""
    auth_req_id: str = Field(..., description="Authorization request ID")
    status: str = Field(..., description="Status: approved, denied, expired")
    user_code: Optional[str] = Field(None, description="User verification code")


# Dependency for getting current user (mock for now)
async def get_current_user() -> str:
    """Get current user ID - TODO: Replace with Auth0"""
    return "test_user_123"


# Endpoints
@router.post("/authorize", response_model=PaymentResponse)
async def process_payment(
    request: PaymentAuthorizationRequest,
    user_id: str = Depends(get_current_user),
    payment_service: PaymentService = Depends(get_payment_service),
    task_service = Depends(get_task_service)
):
    """
    Process payment with transferWithAuthorization

    Executes the USDC transfer on Base Sepolia using EIP-3009.
    The user must have signed the authorization off-chain.

    Returns transaction hash on success.
    """
    try:
        print(f"Processing payment: task_id={request.task_id}, from={request.from_address}, amount={request.amount_usdc}")

        # Execute payment
        success, tx_hash, error = await payment_service.execute_payment(
            from_address=request.from_address,
            amount_usdc=request.amount_usdc,
            valid_after=request.valid_after,
            valid_before=request.valid_before,
            nonce=request.nonce,
            signature=request.signature
        )

        # Convert USDC to USD for response
        amount_usd = float(request.amount_usdc) / 1_000_000

        if success:
            print(f"Payment successful: tx_hash={tx_hash}")
            # Update task payment_status in database
            await task_service.update_task_payment_status(
                task_id=request.task_id,
                tx_hash=tx_hash,
                status="paid"
            )
            return PaymentResponse(
                success=True,
                tx_hash=tx_hash,
                task_id=request.task_id,
                amount_usd=amount_usd
            )
        else:
            print(f"Payment failed: {error}")
            return PaymentResponse(
                success=False,
                error=error or "Payment execution failed",
                task_id=request.task_id,
                amount_usd=amount_usd
            )

    except Exception as e:
        print(f"Payment processing exception: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Payment processing failed: {str(e)}")


@router.post("/ciba/initiate", response_model=Dict)
async def initiate_ciba_approval(
    request: CIBAApprovalRequest,
    async_approval_service: AsyncApprovalService = Depends(get_async_approval_service)
):
    """
    Initiate CIBA flow for payment approval

    Starts Client Initiated Backchannel Authentication flow
    for user to approve payment via Auth0.

    Returns CIBA request details including auth_req_id.
    """
    try:
        result = await async_approval_service.initiate_payment_approval(
            task_id=request.task_id,
            user_id=request.user_id,
            amount=request.amount,
            task_description=request.task_description
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CIBA initiation failed: {str(e)}")


@router.get("/ciba/status/{ciba_request_id}", response_model=CIBAStatusResponse)
async def check_ciba_status(
    ciba_request_id: str,
    async_approval_service: AsyncApprovalService = Depends(get_async_approval_service)
):
    """
    Check status of CIBA approval request

    Returns current status: pending, approved, denied, expired
    """
    request_data = await async_approval_service.check_approval_status(ciba_request_id)

    if not request_data:
        raise HTTPException(status_code=404, detail="CIBA request not found")

    return CIBAStatusResponse(
        ciba_request_id=request_data['id'],
        status=request_data['status'],
        task_id=request_data['task_id'],
        amount=request_data['amount'],
        expires_at=request_data.get('expires_at'),
        approved_at=request_data.get('approved_at')
    )


@router.post("/ciba/simulate/{ciba_request_id}")
async def simulate_ciba_approval(
    ciba_request_id: str,
    approved: bool = True,
    async_approval_service: AsyncApprovalService = Depends(get_async_approval_service)
):
    """
    Simulate CIBA approval (for testing only)

    Allows simulating user approval/denial without actual Auth0 CIBA flow.
    Should be disabled in production.
    """
    result = await async_approval_service.simulate_approval(ciba_request_id, approved)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Simulation failed"))

    return result


@router.post("/webhooks/auth0/ciba")
async def ciba_callback(
    request: CIBACallbackRequest,
    async_approval_service: AsyncApprovalService = Depends(get_async_approval_service),
    x_auth0_signature: Optional[str] = Header(None)
):
    """
    Webhook endpoint for Auth0 CIBA callbacks

    Receives callbacks from Auth0 when user approves/denies payment.

    Should verify webhook signature in production.
    """
    try:
        # TODO: Verify Auth0 webhook signature
        # if not verify_auth0_signature(request, x_auth0_signature):
        #     raise HTTPException(status_code=401, detail="Invalid signature")

        result = await async_approval_service.handle_ciba_callback(
            auth_req_id=request.auth_req_id,
            status=request.status,
            user_code=request.user_code
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Callback handling failed"))

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Callback processing failed: {str(e)}")


@router.get("/balance/{address}")
async def check_balance(
    address: str,
    payment_service: PaymentService = Depends(get_payment_service)
):
    """
    Check USDC balance of an address

    Returns balance in USDC (human readable format).
    """
    try:
        balance = await payment_service.check_balance(address)
        return {
            "address": address,
            "balance": balance,
            "currency": "USDC",
            "chain": "base-sepolia"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Balance check failed: {str(e)}")


# ==================== MAGIC LINK PAYMENT APPROVAL ====================

class MagicLinkApprovalRequest(BaseModel):
    """Request model for initiating magic link payment approval"""
    task_id: str = Field(..., description="Task ID requiring payment")
    user_id: str = Field(..., description="User ID (Auth0 sub)")
    user_email: str = Field(..., description="User's email address")
    user_name: str = Field(..., description="User's display name")
    amount: float = Field(..., description="Payment amount in USD")
    task_description: str = Field(..., description="Task description")


class MagicLinkStatusResponse(BaseModel):
    """Response model for magic link approval status"""
    request_id: str
    status: str
    task_id: str
    amount: float
    expires_at: str
    approved_at: Optional[str] = None
    denied_at: Optional[str] = None


@router.post("/magic-link/request", response_model=Dict)
async def request_magic_link_approval(
    request: MagicLinkApprovalRequest,
    magic_link_service: MagicLinkService = Depends(get_magic_link_service)
):
    """
    Request payment approval via email magic link

    Sends an email to the user with approve/deny links.
    Used by MCP servers and AI agents to request payment approval.

    Returns request_id and status.
    """
    try:
        result = await magic_link_service.create_approval_request(
            task_id=request.task_id,
            user_id=request.user_id,
            user_email=request.user_email,
            user_name=request.user_name,
            amount=request.amount,
            task_description=request.task_description
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to request approval: {str(e)}")


@router.get("/magic-link/status/{request_id}", response_model=MagicLinkStatusResponse)
async def check_magic_link_status(
    request_id: str,
    magic_link_service: MagicLinkService = Depends(get_magic_link_service)
):
    """
    Check status of magic link approval request

    Returns current status: pending, approved, denied, expired
    Used by MCP to poll for approval status.
    """
    request_data = await magic_link_service.check_approval_status(request_id)

    if not request_data:
        raise HTTPException(status_code=404, detail="Approval request not found")

    return MagicLinkStatusResponse(
        request_id=request_data['id'],
        status=request_data['status'],
        task_id=request_data['task_id'],
        amount=request_data['amount'],
        expires_at=request_data['expires_at'],
        approved_at=request_data.get('approved_at'),
        denied_at=request_data.get('denied_at')
    )


@router.get("/magic-link/approve/{token}", response_class=HTMLResponse)
async def approve_payment_magic_link(
    token: str,
    magic_link_service: MagicLinkService = Depends(get_magic_link_service)
):
    """
    Approve payment via magic link (from email)

    This endpoint is accessed when user clicks "Approve" in email.
    """
    result = await magic_link_service.approve_payment(token)

    if not result["success"]:
        # Show error page
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Payment Approval Failed</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 600px;
                    margin: 100px auto;
                    padding: 40px;
                    text-align: center;
                }}
                .error {{
                    background: #FEE2E2;
                    color: #991B1B;
                    padding: 30px;
                    border-radius: 12px;
                    border: 2px solid #FCA5A5;
                }}
                h1 {{ color: #DC2626; }}
            </style>
        </head>
        <body>
            <div class="error">
                <h1>❌ Payment Approval Failed</h1>
                <p>{result.get("error", "Unknown error")}</p>
            </div>
        </body>
        </html>
        """)

    # Show success page
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment Approved</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 600px;
                margin: 100px auto;
                padding: 40px;
                text-align: center;
            }}
            .success {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }}
            h1 {{ margin-top: 0; }}
            .amount {{
                font-size: 32px;
                font-weight: bold;
                margin: 20px 0;
            }}
            .task-id {{
                background: rgba(255,255,255,0.2);
                padding: 10px;
                border-radius: 8px;
                font-family: monospace;
                margin: 20px 0;
            }}
            a {{
                display: inline-block;
                margin-top: 20px;
                padding: 12px 30px;
                background: white;
                color: #667eea;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="success">
            <h1>✅ Payment Approved!</h1>
            <p>Your payment has been successfully approved.</p>
            <div class="amount">${result['amount']:.4f} USDC</div>
            <div class="task-id">Task ID: {result['task_id']}</div>
            <p>The AI agent can now proceed with your task.</p>
            <a href="/">Return to AgentBounty</a>
        </div>
    </body>
    </html>
    """)


@router.get("/magic-link/deny/{token}", response_class=HTMLResponse)
async def deny_payment_magic_link(
    token: str,
    magic_link_service: MagicLinkService = Depends(get_magic_link_service)
):
    """
    Deny payment via magic link (from email)

    This endpoint is accessed when user clicks "Deny" in email.
    """
    result = await magic_link_service.deny_payment(token)

    if not result["success"]:
        # Show error page
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Action Failed</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 600px;
                    margin: 100px auto;
                    padding: 40px;
                    text-align: center;
                }}
                .error {{
                    background: #FEE2E2;
                    color: #991B1B;
                    padding: 30px;
                    border-radius: 12px;
                    border: 2px solid #FCA5A5;
                }}
                h1 {{ color: #DC2626; }}
            </style>
        </head>
        <body>
            <div class="error">
                <h1>❌ Action Failed</h1>
                <p>{result.get("error", "Unknown error")}</p>
            </div>
        </body>
        </html>
        """)

    # Show denial confirmation page
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment Denied</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 600px;
                margin: 100px auto;
                padding: 40px;
                text-align: center;
            }}
            .denied {{
                background: #EF4444;
                color: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }}
            h1 {{ margin-top: 0; }}
            .task-id {{
                background: rgba(255,255,255,0.2);
                padding: 10px;
                border-radius: 8px;
                font-family: monospace;
                margin: 20px 0;
            }}
            a {{
                display: inline-block;
                margin-top: 20px;
                padding: 12px 30px;
                background: white;
                color: #EF4444;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="denied">
            <h1>❌ Payment Denied</h1>
            <p>You have denied the payment request.</p>
            <div class="task-id">Task ID: {result['task_id']}</div>
            <p>The AI agent will not proceed with this task.</p>
            <a href="/">Return to AgentBounty</a>
        </div>
    </body>
    </html>
    """)
