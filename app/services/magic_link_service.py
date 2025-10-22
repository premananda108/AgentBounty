"""
Magic Link Service - Handle payment approval via email magic links
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict
import aiosqlite
from app.config import settings
from app.services.email_service import get_email_service


class MagicLinkService:
    """Service for managing payment approval magic links"""

    def __init__(self):
        self.email_service = get_email_service()
        self.token_expiry_minutes = 10  # Magic links expire in 10 minutes

    def generate_token(self) -> str:
        """Generate secure random token for magic link"""
        # Generate 32 bytes (256 bits) of randomness
        random_bytes = secrets.token_bytes(32)
        # Hash it to get a hex string
        token = hashlib.sha256(random_bytes).hexdigest()
        return token

    async def create_approval_request(
        self,
        task_id: str,
        user_id: str,
        user_email: str,
        user_name: str,
        amount: float,
        task_description: str
    ) -> Dict:
        """
        Create a payment approval request and send magic link email

        Args:
            task_id: Task ID requiring payment
            user_id: User ID (Auth0 sub)
            user_email: User's email address
            user_name: User's display name
            amount: Payment amount in USD
            task_description: Description of the task

        Returns:
            Dict with request_id, status, and expires_at
        """
        try:
            # Generate unique token
            token = self.generate_token()
            request_id = f"mla_{secrets.token_hex(12)}"  # Magic Link Approval ID
            expires_at = datetime.utcnow() + timedelta(minutes=self.token_expiry_minutes)

            # Store in database
            async with aiosqlite.connect(settings.DATABASE_PATH) as db:
                await db.execute("""
                    INSERT INTO magic_link_approvals
                    (id, task_id, user_id, token, status, amount, task_description, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    request_id,
                    task_id,
                    user_id,
                    token,
                    "pending",
                    amount,
                    task_description,
                    datetime.utcnow().isoformat(),
                    expires_at.isoformat()
                ))
                await db.commit()

            # Send email
            email_sent = await self.email_service.send_payment_approval_email(
                to_email=user_email,
                user_name=user_name,
                task_description=task_description,
                amount=amount,
                approval_token=token
            )

            if not email_sent:
                return {
                    "error": "Failed to send approval email",
                    "request_id": request_id
                }

            return {
                "request_id": request_id,
                "status": "pending",
                "expires_at": expires_at.isoformat(),
                "message": f"Approval email sent to {user_email}"
            }

        except Exception as e:
            print(f"❌ Failed to create approval request: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    async def check_approval_status(self, request_id: str) -> Optional[Dict]:
        """
        Check status of a magic link approval request

        Args:
            request_id: Approval request ID

        Returns:
            Dict with request details or None if not found
        """
        try:
            async with aiosqlite.connect(settings.DATABASE_PATH) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM magic_link_approvals
                    WHERE id = ?
                """, (request_id,))
                row = await cursor.fetchone()

                if not row:
                    return None

                # Check if expired
                expires_at = datetime.fromisoformat(row['expires_at'])
                if datetime.utcnow() > expires_at and row['status'] == 'pending':
                    # Mark as expired
                    await db.execute("""
                        UPDATE magic_link_approvals
                        SET status = 'expired'
                        WHERE id = ?
                    """, (request_id,))
                    await db.commit()
                    status = 'expired'
                else:
                    status = row['status']

                # Convert Row to dict
                row_dict = dict(row)
                return {
                    "id": row_dict['id'],
                    "task_id": row_dict['task_id'],
                    "user_id": row_dict['user_id'],
                    "status": status,
                    "amount": row_dict['amount'],
                    "task_description": row_dict['task_description'],
                    "created_at": row_dict['created_at'],
                    "expires_at": row_dict['expires_at'],
                    "approved_at": row_dict.get('approved_at'),
                    "denied_at": row_dict.get('denied_at')
                }

        except Exception as e:
            print(f"❌ Failed to check approval status: {e}")
            return None

    async def approve_payment(self, token: str) -> Dict:
        """
        Approve payment using magic link token

        Args:
            token: Magic link token from email

        Returns:
            Dict with success status and details
        """
        try:
            async with aiosqlite.connect(settings.DATABASE_PATH) as db:
                db.row_factory = aiosqlite.Row

                # Find approval request by token
                cursor = await db.execute("""
                    SELECT * FROM magic_link_approvals
                    WHERE token = ?
                """, (token,))
                row = await cursor.fetchone()

                if not row:
                    return {
                        "success": False,
                        "error": "Invalid approval link"
                    }

                # Check if expired
                expires_at = datetime.fromisoformat(row['expires_at'])
                if datetime.utcnow() > expires_at:
                    await db.execute("""
                        UPDATE magic_link_approvals
                        SET status = 'expired'
                        WHERE token = ?
                    """, (token,))
                    await db.commit()
                    return {
                        "success": False,
                        "error": "Approval link has expired"
                    }

                # Check if already processed
                if row['status'] != 'pending':
                    return {
                        "success": False,
                        "error": f"Payment already {row['status']}"
                    }

                # Approve the payment
                approved_at = datetime.utcnow().isoformat()
                await db.execute("""
                    UPDATE magic_link_approvals
                    SET status = 'approved', approved_at = ?
                    WHERE token = ?
                """, (approved_at, token))

                # Also approve CIBA request for this task (if exists)
                task_id = row['task_id']
                await db.execute("""
                    UPDATE ciba_requests
                    SET status = 'approved', approved_at = ?
                    WHERE task_id = ? AND status = 'pending'
                """, (approved_at, task_id))

                await db.commit()

                print(f"✅ Payment approved via Magic Link for task {task_id}")

                return {
                    "success": True,
                    "status": "approved",
                    "request_id": row['id'],
                    "task_id": row['task_id'],
                    "amount": row['amount'],
                    "approved_at": approved_at
                }

        except Exception as e:
            print(f"❌ Failed to approve payment: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    async def deny_payment(self, token: str) -> Dict:
        """
        Deny payment using magic link token

        Args:
            token: Magic link token from email

        Returns:
            Dict with success status and details
        """
        try:
            async with aiosqlite.connect(settings.DATABASE_PATH) as db:
                db.row_factory = aiosqlite.Row

                # Find approval request by token
                cursor = await db.execute("""
                    SELECT * FROM magic_link_approvals
                    WHERE token = ?
                """, (token,))
                row = await cursor.fetchone()

                if not row:
                    return {
                        "success": False,
                        "error": "Invalid approval link"
                    }

                # Check if expired
                expires_at = datetime.fromisoformat(row['expires_at'])
                if datetime.utcnow() > expires_at:
                    await db.execute("""
                        UPDATE magic_link_approvals
                        SET status = 'expired'
                        WHERE token = ?
                    """, (token,))
                    await db.commit()
                    return {
                        "success": False,
                        "error": "Approval link has expired"
                    }

                # Check if already processed
                if row['status'] != 'pending':
                    return {
                        "success": False,
                        "error": f"Payment already {row['status']}"
                    }

                # Deny the payment
                denied_at = datetime.utcnow().isoformat()
                await db.execute("""
                    UPDATE magic_link_approvals
                    SET status = 'denied', denied_at = ?
                    WHERE token = ?
                """, (denied_at, token))

                # Also deny CIBA request for this task (if exists)
                task_id = row['task_id']
                await db.execute("""
                    UPDATE ciba_requests
                    SET status = 'denied'
                    WHERE task_id = ? AND status = 'pending'
                """, (task_id,))

                await db.commit()

                print(f"❌ Payment denied via Magic Link for task {task_id}")

                return {
                    "success": True,
                    "status": "denied",
                    "request_id": row['id'],
                    "task_id": row['task_id'],
                    "denied_at": denied_at
                }

        except Exception as e:
            print(f"❌ Failed to deny payment: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
_magic_link_service: Optional[MagicLinkService] = None


def get_magic_link_service() -> MagicLinkService:
    """Get or create magic link service instance"""
    global _magic_link_service
    if _magic_link_service is None:
        _magic_link_service = MagicLinkService()
    return _magic_link_service
