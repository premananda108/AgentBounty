"""
Async Approval Service - Email-based payment approval for AI agents

This service implements asynchronous authorization pattern recommended by Auth0 for AI agents.
Uses email-based approval instead of CIBA push notifications.
"""
import uuid
import json
import aiosqlite
from datetime import datetime, timedelta
from typing import Dict, Optional

import httpx

from app.config import get_settings
from app.services.auth0_service import Auth0Service

settings = get_settings()


class AsyncApprovalService:
    """Service for managing async payment approval flow via email"""

    def __init__(self):
        self.auth0_service = Auth0Service()
        self.db_path = settings.DATABASE_PATH

    async def initiate_payment_approval(
        self,
        task_id: str,
        user_id: str,
        amount: float,
        task_description: str
    ) -> Dict:
        """
        Initiate async approval flow for payment

        Args:
            task_id: Task ID requiring payment
            user_id: User ID from Auth0
            amount: Payment amount in USD
            task_description: Description of what user is paying for

        Returns:
            Approval request details
        """
        try:
            # Get Auth0 Management token
            mgmt_token = await self.auth0_service.get_management_token()

            # Get user details
            user_profile = await self.auth0_service.get_user_profile(user_id)

            if not user_profile:
                raise ValueError("User profile not found")

            # Create approval request ID (keeping ciba_request_id for backward compatibility)
            ciba_request_id = str(uuid.uuid4())

            # Use Async Authorization with Email Approval (Auth0 for AI Agents pattern)
            print(f"🤖 Async Authorization: Email-based approval for AI agent payment")
            auth_req_id = f"auth_req_{ciba_request_id[:8]}"
            expires_at = datetime.utcnow() + timedelta(minutes=10)  # 10 minutes for email

            # Send approval email via Auth0 + SendGrid
            try:
                from app.services.magic_link_service import get_magic_link_service
                magic_link_service = get_magic_link_service()

                user_email = user_profile.get('email')
                user_name = user_profile.get('name', user_email)

                print(f"📧 Sending approval email to {user_email} via Auth0")

                email_result = await magic_link_service.create_approval_request(
                    task_id=task_id,
                    user_id=user_id,
                    user_email=user_email,
                    user_name=user_name,
                    amount=amount,
                    task_description=task_description
                )

                if "error" in email_result:
                    print(f"⚠️ Failed to send approval email: {email_result['error']}")
                else:
                    print(f"✅ Approval email sent! Request ID: {email_result['request_id']}")

            except Exception as e:
                print(f"⚠️ Error sending approval email: {e}")
                import traceback
                traceback.print_exc()

            # Store approval request in database (table named ciba_requests for backward compatibility)
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO ciba_requests (
                        id, task_id, user_id, auth_req_id, status,
                        amount, created_at, expires_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ciba_request_id,
                        task_id,
                        user_id,
                        auth_req_id,
                        "pending",
                        amount,
                        datetime.utcnow().isoformat(),
                        expires_at.isoformat()
                    )
                )
                await db.commit()

            return {
                "ciba_request_id": ciba_request_id,  # Keep for backward compatibility
                "approval_request_id": ciba_request_id,
                "auth_req_id": auth_req_id,
                "status": "pending",
                "expires_at": expires_at.isoformat(),
                "message": f"Payment approval required: ${amount:.4f} for {task_description}"
            }

        except Exception as e:
            print(f"❌ Approval initiation error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "status": "failed"
            }

    async def check_approval_status(
        self,
        ciba_request_id: str
    ) -> Optional[Dict]:
        """
        Check status of async approval request

        Checks database for approval status from email link click

        Args:
            ciba_request_id: Approval request ID (kept as ciba_request_id for compatibility)

        Returns:
            Status dict or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM ciba_requests
                WHERE id = ?
                """,
                (ciba_request_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            request_data = dict(row)

            # Check if expired
            if request_data['status'] == 'pending':
                expires_at = datetime.fromisoformat(request_data['expires_at'])
                if datetime.utcnow() > expires_at:
                    # Mark as expired
                    await db.execute(
                        """
                        UPDATE ciba_requests
                        SET status = 'expired'
                        WHERE id = ?
                        """,
                        (ciba_request_id,)
                    )
                    await db.commit()
                    request_data['status'] = 'expired'

            return request_data

    async def handle_ciba_callback(
        self,
        auth_req_id: str,
        status: str,
        user_code: Optional[str] = None
    ) -> Dict:
        """
        Handle callback from Auth0 CIBA flow

        Args:
            auth_req_id: Authorization request ID from Auth0
            status: Status (approved, denied, expired)
            user_code: Optional user verification code

        Returns:
            Callback handling result
        """
        try:
            # Find CIBA request by auth_req_id
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    """
                    SELECT * FROM ciba_requests
                    WHERE auth_req_id = ?
                    """,
                    (auth_req_id,)
                )
                row = await cursor.fetchone()

                if not row:
                    return {
                        "success": False,
                        "error": "CIBA request not found"
                    }

                request_data = dict(row)

                # Update status
                update_time = datetime.utcnow().isoformat() if status == 'approved' else None

                await db.execute(
                    """
                    UPDATE ciba_requests
                    SET status = ?, approved_at = ?
                    WHERE auth_req_id = ?
                    """,
                    (status, update_time, auth_req_id)
                )

                # If approved, also update task payment_status
                if status == 'approved':
                    await db.execute(
                        """
                        UPDATE tasks
                        SET payment_status = 'approved',
                            payment_auth_req_id = ?
                        WHERE id = ?
                        """,
                        (auth_req_id, request_data['task_id'])
                    )

                await db.commit()

                return {
                    "success": True,
                    "ciba_request_id": request_data['id'],
                    "task_id": request_data['task_id'],
                    "status": status,
                    "approved_at": update_time
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def simulate_approval(
        self,
        ciba_request_id: str,
        approved: bool = True
    ) -> Dict:
        """
        Simulate CIBA approval (for testing)

        Args:
            ciba_request_id: CIBA request ID
            approved: Whether to approve or deny

        Returns:
            Simulation result
        """
        request_data = await self.check_approval_status(ciba_request_id)

        if not request_data:
            return {
                "success": False,
                "error": "CIBA request not found"
            }

        if request_data['status'] != 'pending':
            return {
                "success": False,
                "error": f"CIBA request already {request_data['status']}"
            }

        # Simulate callback
        status = 'approved' if approved else 'denied'
        return await self.handle_ciba_callback(
            request_data['auth_req_id'],
            status
        )


# Singleton instance
_async_approval_service = None

def get_async_approval_service() -> AsyncApprovalService:
    """Get or create AsyncApprovalService singleton"""
    global _async_approval_service
    if _async_approval_service is None:
        _async_approval_service = AsyncApprovalService()
    return _async_approval_service

# Backward compatibility alias
get_ciba_service = get_async_approval_service
CIBAService = AsyncApprovalService
