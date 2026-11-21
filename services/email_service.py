"""services/email_service.py

Fault-tolerant SMTP order confirmation and store administrator notification
service for Setuvo. Supports implicit SSL (port 465 via SMTP_SSL) as well as
STARTTLS (port 587). Email delivery failures are caught and logged so a
successfully persisted SQLite order is never cancelled or rolled back.
"""

from email.message import EmailMessage
from html import escape
import logging
import smtplib
import ssl
from typing import Any, Dict, Optional

from config import Config
from models.entities import Order, format_naira
from services.exceptions import EmailDeliveryError

logger = logging.getLogger(__name__)


class EmailService:
    """Dispatches order confirmation emails to customers and alerts to store admins."""

    def __init__(
        self,
        mail_enabled: Optional[bool] = None,
        mail_server: Optional[str] = None,
        mail_port: Optional[int] = None,
        mail_use_tls: Optional[bool] = None,
        mail_use_ssl: Optional[bool] = None,
        mail_username: Optional[str] = None,
        mail_password: Optional[str] = None,
        default_sender: Optional[str] = None,
        admin_email: Optional[str] = None,
    ) -> None:
        self.mail_enabled: bool = (
            Config.MAIL_ENABLED if mail_enabled is None else bool(mail_enabled)
        )
        self.mail_server: str = str(
            Config.MAIL_SERVER if mail_server is None else mail_server
        ).strip()
        self.mail_port: int = int(
            Config.MAIL_PORT if mail_port is None else mail_port
        )
        self.mail_use_tls: bool = (
            Config.MAIL_USE_TLS if mail_use_tls is None else bool(mail_use_tls)
        )
        self.mail_use_ssl: bool = (
            Config.MAIL_USE_SSL if mail_use_ssl is None else bool(mail_use_ssl)
        )
        self.mail_username: str = str(
            Config.MAIL_USERNAME if mail_username is None else mail_username
        ).strip()
        self.mail_password: str = str(
            Config.MAIL_PASSWORD if mail_password is None else mail_password
        )
        self.default_sender: str = str(
            Config.MAIL_DEFAULT_SENDER if default_sender is None else default_sender
        ).strip()
        self.admin_email: str = str(
            Config.ADMIN_NOTIFICATION_EMAIL if admin_email is None else admin_email
        ).strip()

    def is_configured(self) -> bool:
        """Returns True when SMTP notifications are enabled and a server host is set."""
        return bool(self.mail_enabled and self.mail_server)

    # ------------------------------------------------------------------
    # Message Builders
    # ------------------------------------------------------------------
    def build_customer_confirmation_message(self, order: Order) -> EmailMessage:
        """Constructs a multipart plain-text + HTML order confirmation EmailMessage."""
        msg = EmailMessage()
        msg["Subject"] = f"Setuvo Order Confirmation — {order.order_number}"
        msg["From"] = self.default_sender
        msg["To"] = order.customer_email

        plain_lines = [
            f"Hello {order.customer_name},",
            "",
            f"Thank you for shopping with {Config.APP_NAME}. Your order has been recorded.",
            "",
            f"Order Number: {order.order_number}",
            f"Order Status: {order.status}",
            f"Payment Method: {order.payment_method}",
            f"Delivery Zone: {order.delivery_zone_label} ({order.delivery_eta})",
            f"Delivery Address: {order.delivery_address}",
            "",
            "Purchased Items:",
        ]
        html_rows = []
        for item in order.items:
            unit_str = format_naira(item.unit_price)
            line_str = format_naira(item.line_total)
            plain_lines.append(
                f"  - {item.product_name} [{item.product_sku}] x{item.quantity} "
                f"@ {unit_str} = {line_str}"
            )
            html_rows.append(
                "<tr>"
                f"<td style='padding:6px 8px;border-bottom:1px solid #e2e8f0;'>{escape(item.product_name)} "
                f"<small style='color:#64748b;'>({escape(item.product_sku)})</small></td>"
                f"<td style='padding:6px 8px;border-bottom:1px solid #e2e8f0;text-align:center;'>{item.quantity}</td>"
                f"<td style='padding:6px 8px;border-bottom:1px solid #e2e8f0;text-align:right;'>{escape(unit_str)}</td>"
                f"<td style='padding:6px 8px;border-bottom:1px solid #e2e8f0;text-align:right;'>{escape(line_str)}</td>"
                "</tr>"
            )

        shipping_str = (
            "Free" if order.delivery_fee == 0 else format_naira(order.delivery_fee)
        )
        plain_lines.extend(
            [
                "",
                f"Subtotal: {format_naira(order.subtotal)}",
                f"Delivery Fee: {shipping_str}",
                f"Order Total: {format_naira(order.total_amount)}",
                "",
                "You can track your order anytime using your order number and email address on Setuvo.",
                f"— {Config.APP_NAME} Team",
            ]
        )

        msg.set_content("\n".join(plain_lines))

        html_body = f"""
        <html>
          <body style="font-family:Arial,sans-serif;color:#0f172a;line-height:1.5;">
            <h2 style="color:#0f766e;margin-bottom:4px;">{escape(Config.APP_NAME)} Order Confirmation</h2>
            <p>Hello <strong>{escape(order.customer_name)}</strong>, thank you for your order.</p>
            <p>
              <strong>Order Number:</strong> {escape(order.order_number)}<br>
              <strong>Status:</strong> {escape(order.status)}<br>
              <strong>Payment Method:</strong> {escape(order.payment_method)}<br>
              <strong>Delivery Zone:</strong> {escape(order.delivery_zone_label)} ({escape(order.delivery_eta)})<br>
              <strong>Delivery Address:</strong> {escape(order.delivery_address)}
            </p>
            <table style="width:100%;border-collapse:collapse;margin:16px 0;">
              <thead>
                <tr style="background:#f1f5f9;text-align:left;">
                  <th style="padding:8px;">Product</th>
                  <th style="padding:8px;text-align:center;">Qty</th>
                  <th style="padding:8px;text-align:right;">Unit Price</th>
                  <th style="padding:8px;text-align:right;">Total</th>
                </tr>
              </thead>
              <tbody>
                {''.join(html_rows)}
              </tbody>
            </table>
            <p style="text-align:right;">
              <strong>Subtotal:</strong> {escape(format_naira(order.subtotal))}<br>
              <strong>Delivery Fee:</strong> {escape(shipping_str)}<br>
              <span style="font-size:1.1em;color:#0f766e;">
                <strong>Order Total:</strong> {escape(format_naira(order.total_amount))}
              </span>
            </p>
            <p style="color:#475569;font-size:0.9em;">
              Track your order status anytime on Setuvo using <strong>{escape(order.order_number)}</strong>
              and <strong>{escape(order.customer_email)}</strong>.
            </p>
          </body>
        </html>
        """
        msg.add_alternative(html_body.strip(), subtype="html")
        return msg

    def build_admin_notification_message(self, order: Order) -> EmailMessage:
        """Constructs an administrative order alert email for store fulfillment."""
        msg = EmailMessage()
        msg["Subject"] = (
            f"[New Setuvo Order] {order.order_number} ({format_naira(order.total_amount)})"
        )
        msg["From"] = self.default_sender
        msg["To"] = self.admin_email

        lines = [
            f"New order received on {Config.APP_NAME}:",
            "",
            f"Order Number: {order.order_number}",
            f"Customer: {order.customer_name}",
            f"Email: {order.customer_email}",
            f"Phone: {order.customer_phone}",
            f"Delivery Zone: {order.delivery_zone_label}",
            f"Delivery Address: {order.delivery_address}",
            f"Notes: {order.notes or 'None'}",
            "",
            "Line Items:",
        ]
        for item in order.items:
            lines.append(
                f"  - {item.product_sku} | {item.product_name} x{item.quantity} "
                f"({format_naira(item.line_total)})"
            )
        lines.extend(
            [
                "",
                f"Subtotal: {format_naira(order.subtotal)}",
                f"Delivery Fee: {format_naira(order.delivery_fee)}",
                f"Grand Total: {format_naira(order.total_amount)}",
            ]
        )
        msg.set_content("\n".join(lines))
        return msg

    # ------------------------------------------------------------------
    # Low-Level SMTP Transport & Fault-Tolerant Dispatcher
    # ------------------------------------------------------------------
    def _dispatch_message(self, message: EmailMessage) -> None:
        """Opens an SMTP_SSL (port 465) or STARTTLS (port 587) session and sends."""
        ssl_context = ssl.create_default_context()
        use_implicit_ssl = self.mail_use_ssl or (
            self.mail_port == 465 and not self.mail_use_tls
        )

        if use_implicit_ssl:
            with smtplib.SMTP_SSL(
                self.mail_server,
                self.mail_port,
                timeout=15,
                context=ssl_context,
            ) as smtp:
                smtp.ehlo()
                if self.mail_username and self.mail_password:
                    smtp.login(self.mail_username, self.mail_password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(
                self.mail_server, self.mail_port, timeout=15
            ) as smtp:
                smtp.ehlo()
                if self.mail_use_tls:
                    smtp.starttls(context=ssl_context)
                    smtp.ehlo()
                if self.mail_username and self.mail_password:
                    smtp.login(self.mail_username, self.mail_password)
                smtp.send_message(message)

    def send_order_notifications(
        self,
        order: Order,
        raise_on_error: bool = False,
    ) -> Dict[str, Any]:
        """Sends customer confirmation and admin alert emails safely.

        Never raises by default when SMTP fails, ensuring completed orders
        remain intact even if the mail server is offline or misconfigured.
        """
        if not self.is_configured():
            return {
                "sent": False,
                "customer_sent": False,
                "admin_sent": False,
                "skipped": True,
                "error": None,
            }

        customer_sent = False
        admin_sent = False
        errors: list[str] = []

        if order.customer_email:
            try:
                customer_msg = self.build_customer_confirmation_message(order)
                self._dispatch_message(customer_msg)
                customer_sent = True
            except Exception as exc:
                logger.warning(
                    "Failed to send customer confirmation email for %s: %s",
                    order.order_number,
                    exc,
                )
                errors.append(f"Customer email error: {exc}")

        if self.admin_email:
            try:
                admin_msg = self.build_admin_notification_message(order)
                self._dispatch_message(admin_msg)
                admin_sent = True
            except Exception as exc:
                logger.warning(
                    "Failed to send admin notification email for %s: %s",
                    order.order_number,
                    exc,
                )
                errors.append(f"Admin email error: {exc}")

        error_summary = "; ".join(errors) if errors else None
        if error_summary and raise_on_error:
            raise EmailDeliveryError(details=error_summary)

        return {
            "sent": customer_sent,
            "customer_sent": customer_sent,
            "admin_sent": admin_sent,
            "skipped": False,
            "error": error_summary,
        }