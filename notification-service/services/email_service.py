"""Email notification service."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send email. Returns True if sent successfully."""
        try:
            # For development, just log the email
            if self.smtp_host == "localhost" and not self.smtp_user:
                logger.info(f"📧 EMAIL (dev mode):\n  To: {to_email}\n  Subject: {subject}\n  Body: {body[:100]}...")
                return True

            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as exc:
            logger.error(f"Failed to send email to {to_email}: {exc}")
            return False


def compose_order_paid_email(order_id: str, amount: float) -> tuple[str, str]:
    """Generate subject and body for order paid notification."""
    subject = f"Order Confirmation - Order #{order_id}"
    body = f"""
Dear Customer,

Thank you for your order! Your payment has been successfully processed.

Order ID: {order_id}
Amount Paid: ${amount:.2f}

We'll send you another notification when your order ships.

Best regards,
Bookstore Team
"""
    return subject, body


def compose_shipment_created_email(order_id: str, method_name: str) -> tuple[str, str]:
    """Generate subject and body for shipment created notification."""
    subject = f"Shipment Created - Order #{order_id}"
    body = f"""
Dear Customer,

Your order has been prepared for shipment!

Order ID: {order_id}
Shipping Method: {method_name}

You'll receive a tracking update once your package is picked up.

Best regards,
Bookstore Team
"""
    return subject, body


def compose_shipment_updated_email(order_id: str, status: str) -> tuple[str, str]:
    """Generate subject and body for shipment status update."""
    subject = f"Shipment Update - Order #{order_id}"
    body = f"""
Dear Customer,

Your shipment status has been updated!

Order ID: {order_id}
Status: {status.upper()}

Thank you for your order!

Best regards,
Bookstore Team
"""
    return subject, body
