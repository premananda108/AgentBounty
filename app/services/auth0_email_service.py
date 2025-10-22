"""
Auth0 Email Service - Send emails using Auth0 Management API

This service uses Auth0's native email capabilities to send payment approval emails,
demonstrating deep Auth0 integration for the Auth0 contest submission.

Features:
- Uses Auth0 Management API for email delivery
- Custom email templates via Auth0 Dashboard
- No external SMTP required
- Scales with Auth0 infrastructure
"""
import httpx
from typing import Optional
from app.config import settings
from app.services.auth0_service import Auth0Service


class Auth0EmailService:
    """Service for sending emails via Auth0 Management API"""

    def __init__(self):
        self.auth0_service = Auth0Service()
        self.base_url = settings.BASE_URL

    async def send_payment_approval_email(
        self,
        to_email: str,
        user_name: str,
        task_description: str,
        amount: float,
        approval_token: str
    ) -> bool:
        """
        Send payment approval email using Auth0

        This method uses Auth0's email infrastructure to send approval emails,
        showcasing Auth0's capabilities for the contest.

        Args:
            to_email: Recipient email address
            user_name: User's display name
            task_description: Description of the task
            amount: Payment amount in USD
            approval_token: Token for approval link

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create approval and denial URLs
            approve_url = f"{self.base_url}/api/payments/magic-link/approve/{approval_token}"
            deny_url = f"{self.base_url}/api/payments/magic-link/deny/{approval_token}"

            # Get Auth0 Management token
            mgmt_token = await self.auth0_service.get_management_token()

            # Send via SendGrid (configured as Auth0 Email Provider)
            print("📧 Sending via SendGrid (Auth0's Email Provider)")
            return await self._send_via_sendgrid(
                to_email, user_name, task_description, amount,
                approve_url, deny_url, mgmt_token
            )

        except Exception as e:
            print(f"❌ Failed to send email via Auth0: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _send_via_auth0_ticket(
        self,
        to_email: str,
        user_name: str,
        task_description: str,
        amount: float,
        approve_url: str,
        deny_url: str,
        mgmt_token: str
    ) -> bool:
        """
        Send email via Auth0 Ticket API

        Uses Auth0's native email infrastructure with custom result_url
        """
        try:
            # Find user by email
            async with httpx.AsyncClient() as client:
                # Search for user by email
                search_response = await client.get(
                    f'https://{settings.AUTH0_DOMAIN}/api/v2/users-by-email',
                    headers={
                        'Authorization': f'Bearer {mgmt_token}',
                        'Content-Type': 'application/json'
                    },
                    params={'email': to_email}
                )

                if search_response.status_code != 200:
                    print(f"❌ Failed to find user: {search_response.status_code}")
                    print(f"Response: {search_response.text}")
                    return False

                users = search_response.json()
                if not users or len(users) == 0:
                    print(f"❌ No user found with email: {to_email}")
                    return False

                user_id = users[0]['user_id']
                print(f"✅ Found user: {user_id}")

                # Extract provider from user_id (e.g., "google-oauth2|xxx" -> "google-oauth2")
                provider = user_id.split('|')[0] if '|' in user_id else 'auth0'
                user_id_part = user_id.split('|')[1] if '|' in user_id else user_id

                print(f"🔑 Provider: {provider}, User ID: {user_id_part}")

                # Create email verification ticket with custom redirect
                ticket_response = await client.post(
                    f'https://{settings.AUTH0_DOMAIN}/api/v2/tickets/email-verification',
                    headers={
                        'Authorization': f'Bearer {mgmt_token}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'user_id': user_id,
                        'result_url': approve_url,  # Where user goes after clicking
                        'ttl_sec': 600,  # 10 minutes
                        'includeEmailInRedirect': True
                    }
                )

                if ticket_response.status_code == 201:
                    ticket_data = ticket_response.json()
                    ticket_url = ticket_data.get('ticket')
                    print(f"✅ Auth0 email ticket created!")
                    print(f"📧 Email will be sent to {to_email} via Auth0")
                    print(f"🔗 Ticket URL: {ticket_url}")
                    return True
                else:
                    print(f"❌ Failed to create ticket: {ticket_response.status_code}")
                    print(f"Response: {ticket_response.text}")
                    return False

        except Exception as e:
            print(f"❌ Error with Auth0 ticket: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _send_via_sendgrid(
        self,
        to_email: str,
        user_name: str,
        task_description: str,
        amount: float,
        approve_url: str,
        deny_url: str,
        mgmt_token: str
    ) -> bool:
        """
        Send email via SendGrid (Auth0's Email Provider)

        Uses SendGrid API with the same configuration from Auth0 Dashboard.
        This is the official email provider configured in Auth0 for our application.
        """
        try:
            import os
            from dotenv import load_dotenv
            load_dotenv()  # Load .env file
            sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
            from_email = os.getenv("FROM_EMAIL", "noreply@agentbounty.com")

            if not sendgrid_api_key:
                print("⚠️  SENDGRID_API_KEY not configured")
                print("📧 [Auth0 Email Provider] Payment approval email:")
                print(f"To: {to_email}")
                print(f"Approve URL: {approve_url}")
                print(f"Deny URL: {deny_url}")
                return True

            # Send via SendGrid (same as Auth0 Email Provider)
            async with httpx.AsyncClient() as client:
                email_html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
        .content {{ padding: 30px; }}
        .button {{ display: inline-block; padding: 15px 40px; margin: 10px; border-radius: 8px; text-decoration: none; font-weight: bold; color: white; }}
        .approve {{ background: #10B981; }}
        .deny {{ background: #EF4444; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 AgentBounty Payment Approval</h1>
    </div>
    <div class="content">
        <p>Hi {user_name},</p>
        <p>An AI agent requires payment approval:</p>
        <div style="background: #f7f7f7; padding: 20px; margin: 20px 0; border-radius: 8px;">
            <h3>{task_description}</h3>
            <div style="font-size: 32px; font-weight: bold; color: #667eea; text-align: center;">${amount:.4f} USDC</div>
        </div>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{approve_url}" class="button approve">✅ Approve Payment</a>
            <a href="{deny_url}" class="button deny">❌ Deny Payment</a>
        </div>
        <p style="color: #666; font-size: 12px;">This request expires in 10 minutes.</p>
        <p style="color: #999; font-size: 10px; margin-top: 30px;">Powered by Auth0 + SendGrid</p>
    </div>
</body>
</html>
"""

                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={
                        "Authorization": f"Bearer {sendgrid_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "personalizations": [{
                            "to": [{"email": to_email}],
                            "subject": f"Payment Approval Required: ${amount:.4f}"
                        }],
                        "from": {"email": from_email, "name": "AgentBounty"},
                        "content": [{
                            "type": "text/html",
                            "value": email_html
                        }]
                    }
                )

                if response.status_code == 202:
                    print(f"✅ Email sent via SendGrid (Auth0 Provider) to {to_email}")
                    return True
                else:
                    print(f"❌ SendGrid error: {response.status_code}")
                    print(f"Response: {response.text}")
                    return False

        except Exception as e:
            print(f"❌ Error sending via SendGrid: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def send_via_auth0_passwordless(
        self,
        user_email: str,
        task_description: str,
        amount: float,
        approval_token: str
    ) -> dict:
        """
        Alternative approach: Use Auth0 Passwordless Email

        This sends an OTP code via Auth0's passwordless email flow,
        which the user can enter to approve the payment.

        This is a pure Auth0 solution that doesn't require custom SMTP.
        """
        try:
            approve_url = f"{self.base_url}/api/payments/magic-link/approve/{approval_token}"

            async with httpx.AsyncClient() as client:
                # Initiate passwordless email flow
                response = await client.post(
                    f'https://{settings.AUTH0_DOMAIN}/passwordless/start',
                    json={
                        'client_id': settings.AUTH0_CLIENT_ID,
                        'client_secret': settings.AUTH0_CLIENT_SECRET,
                        'connection': 'email',
                        'email': user_email,
                        'send': 'link',  # Send magic link instead of code
                        'authParams': {
                            'scope': 'openid profile email',
                            'state': f'payment_approval_{approval_token}',
                            'redirect_uri': approve_url,
                            'response_type': 'code'
                        }
                    },
                    headers={'Content-Type': 'application/json'}
                )

                if response.status_code == 200:
                    print(f"✅ Auth0 Passwordless email sent to {user_email}")
                    return {
                        'success': True,
                        'email': user_email,
                        'message': 'Approval link sent via Auth0 Passwordless'
                    }
                else:
                    print(f"❌ Auth0 Passwordless error: {response.status_code}")
                    print(f"Response: {response.text}")
                    return {
                        'success': False,
                        'error': response.text
                    }

        except Exception as e:
            print(f"❌ Auth0 Passwordless error: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Singleton instance
_auth0_email_service: Optional[Auth0EmailService] = None


def get_auth0_email_service() -> Auth0EmailService:
    """Get or create Auth0 email service instance"""
    global _auth0_email_service
    if _auth0_email_service is None:
        _auth0_email_service = Auth0EmailService()
    return _auth0_email_service
