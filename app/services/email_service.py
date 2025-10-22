"""
Email Service - Send magic link emails for payment approval

This service prioritizes Auth0's email infrastructure for the Auth0 contest,
falling back to SMTP if Auth0 is not available.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os
from app.config import settings


class EmailService:
    """
    Service for sending emails

    Priority:
    1. Auth0 Email Infrastructure (for contest submission)
    2. SMTP (fallback)
    3. Console output (development)
    """

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@agentbounty.com")
        self.base_url = os.getenv("BASE_URL", "http://localhost:8000")
        self.use_auth0_email = os.getenv("USE_AUTH0_EMAIL", "true").lower() == "true"

    async def send_payment_approval_email(
        self,
        to_email: str,
        user_name: str,
        task_description: str,
        amount: float,
        approval_token: str
    ) -> bool:
        """
        Send payment approval email with magic link

        Priority:
        1. Try Auth0 email infrastructure (for Auth0 contest)
        2. Fall back to SMTP if configured
        3. Console output for development

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
            # Priority 1: Try Auth0 email infrastructure
            if self.use_auth0_email:
                try:
                    from app.services.auth0_email_service import get_auth0_email_service
                    auth0_email_service = get_auth0_email_service()

                    print("🎯 Using Auth0 email infrastructure (Auth0 Contest Feature)")
                    success = await auth0_email_service.send_payment_approval_email(
                        to_email=to_email,
                        user_name=user_name,
                        task_description=task_description,
                        amount=amount,
                        approval_token=approval_token
                    )

                    if success:
                        return True
                    else:
                        print("⚠️  Auth0 email failed, falling back to SMTP")
                except Exception as e:
                    print(f"⚠️  Auth0 email error: {e}, falling back to SMTP")

            # Priority 2: SMTP (original implementation)
            return await self._send_via_smtp(
                to_email, user_name, task_description, amount, approval_token
            )

        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _send_via_smtp(
        self,
        to_email: str,
        user_name: str,
        task_description: str,
        amount: float,
        approval_token: str
    ) -> bool:
        """Send email via SMTP (fallback method)"""
        try:
            # Create approval and denial URLs
            approve_url = f"{self.base_url}/api/payments/magic-link/approve/{approval_token}"
            deny_url = f"{self.base_url}/api/payments/magic-link/deny/{approval_token}"

            # Create email content
            subject = f"Payment Approval Required: ${amount:.4f}"

            # HTML email body
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 30px;
                        border-radius: 10px 10px 0 0;
                        text-align: center;
                    }}
                    .content {{
                        background: #f7f7f7;
                        padding: 30px;
                        border-radius: 0 0 10px 10px;
                    }}
                    .task-box {{
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        margin: 20px 0;
                        border-left: 4px solid #667eea;
                    }}
                    .amount {{
                        font-size: 32px;
                        font-weight: bold;
                        color: #667eea;
                        text-align: center;
                        margin: 20px 0;
                    }}
                    .button-container {{
                        text-align: center;
                        margin: 30px 0;
                    }}
                    .button {{
                        display: inline-block;
                        padding: 15px 40px;
                        margin: 10px;
                        border-radius: 8px;
                        text-decoration: none;
                        font-weight: bold;
                        font-size: 16px;
                    }}
                    .approve {{
                        background: #10B981;
                        color: white;
                    }}
                    .deny {{
                        background: #EF4444;
                        color: white;
                    }}
                    .footer {{
                        text-align: center;
                        color: #666;
                        font-size: 12px;
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #ddd;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🤖 AgentBounty</h1>
                    <p>Payment Approval Request</p>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>

                    <p>An AI agent has requested to use AgentBounty on your behalf and requires payment approval.</p>

                    <div class="task-box">
                        <h3>Task Details</h3>
                        <p><strong>Description:</strong> {task_description}</p>
                        <div class="amount">${amount:.4f} USDC</div>
                    </div>

                    <p><strong>Please review and approve or deny this payment:</strong></p>

                    <div class="button-container">
                        <a href="{approve_url}" class="button approve">✅ Approve Payment</a>
                        <a href="{deny_url}" class="button deny">❌ Deny Payment</a>
                    </div>

                    <p style="color: #666; font-size: 14px;">
                        This approval request will expire in 10 minutes.
                    </p>

                    <div class="footer">
                        <p>If you didn't authorize this request, please ignore this email or click "Deny Payment".</p>
                        <p>© 2025 AgentBounty. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Plain text alternative
            text_body = f"""
AgentBounty - Payment Approval Request

Hi {user_name},

An AI agent has requested to use AgentBounty on your behalf and requires payment approval.

Task Details:
- Description: {task_description}
- Amount: ${amount:.4f} USDC

To approve this payment, click here:
{approve_url}

To deny this payment, click here:
{deny_url}

This approval request will expire in 10 minutes.

If you didn't authorize this request, please ignore this email.

© 2025 AgentBounty
            """

            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.from_email
            message["To"] = to_email

            # Attach both plain text and HTML versions
            message.attach(MIMEText(text_body, "plain"))
            message.attach(MIMEText(html_body, "html"))

            # Send email
            if self.smtp_user and self.smtp_password:
                # Real SMTP
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)
                print(f"✅ Payment approval email sent to {to_email}")
            else:
                # Development mode - just print email
                print("📧 [DEV MODE] Payment approval email (not sent, SMTP not configured):")
                print(f"To: {to_email}")
                print(f"Subject: {subject}")
                print(f"Approve URL: {approve_url}")
                print(f"Deny URL: {deny_url}")

            return True

        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            import traceback
            traceback.print_exc()
            return False


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service instance"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
