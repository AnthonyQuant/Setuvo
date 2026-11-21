"""services/receipt_service.py

Renders a branded PNG order receipt in memory for Setuvo guest orders
so customers can download a copy directly from the order confirmation page.
"""

from datetime import datetime
import io
from pathlib import Path
from typing import Any, List, Tuple

from PIL import Image, ImageDraw, ImageFont

from config import Config


class ReceiptService:
    """Generates clean, print-ready PNG receipt images from Order domain objects."""

    CANVAS_WIDTH = 820
    OUTER_PAD = 36
    CARD_PAD = 36
    BG_COLOR = "#f1f5f9"
    CARD_BG = "#ffffff"
    BORDER_COLOR = "#cbd5e1"
    HEADER_BG = "#0f172a"
    ACCENT_COLOR = "#059669"
    TEXT_PRIMARY = "#0f172a"
    TEXT_MUTED = "#475569"
    ROW_ALT_BG = "#f8fafc"

    def __init__(self) -> None:
        self.font_title = self._load_font(size=26, bold=True)
        self.font_heading = self._load_font(size=16, bold=True)
        self.font_body_bold = self._load_font(size=14, bold=True)
        self.font_body = self._load_font(size=14, bold=False)
        self.font_small = self._load_font(size=12, bold=False)
        self.font_total = self._load_font(size=18, bold=True)

    @staticmethod
    def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Loads a crisp system TrueType font with safe cross-platform fallbacks."""
        candidates = (
            [
                r"C:\Windows\Fonts\segoeuib.ttf",
                r"C:\Windows\Fonts\arialbd.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ]
            if bold
            else [
                r"C:\Windows\Fonts\segoeui.ttf",
                r"C:\Windows\Fonts\arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
        )
        for font_path in candidates:
            if Path(font_path).is_file():
                try:
                    return ImageFont.truetype(font_path, size=size)
                except OSError:
                    continue
        return ImageFont.load_default()

    @staticmethod
    def _format_ngn(amount: Any) -> str:
        """Formats numeric values consistently in NGN for receipt rendering."""
        try:
            value = float(amount or 0.0)
        except (TypeError, ValueError):
            value = 0.0
        return f"NGN {value:,.2f}"

    @staticmethod
    def _format_timestamp(raw_ts: Any) -> str:
        """Converts ISO timestamps into a readable receipt date string."""
        if not raw_ts:
            return "—"
        text = str(raw_ts).strip()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return parsed.strftime("%d %b %Y, %H:%M UTC")
        except ValueError:
            return text[:19]

    @staticmethod
    def _wrap_text(
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
    ) -> List[str]:
        """Wraps text cleanly to fit within max_width pixels."""
        words = str(text or "").split()
        if not words:
            return ["—"]

        lines: List[str] = []
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if draw.textlength(trial, font=font) <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def _extract_order_fields(self, order: Any) -> dict[str, Any]:
        """Normalizes attributes from an Order entity or dictionary."""
        customer = getattr(order, "customer", None)
        full_name = (
            getattr(order, "customer_name", None)
            or getattr(customer, "full_name", None)
            or "Valued Customer"
        )
        email = (
            getattr(order, "customer_email", None)
            or getattr(customer, "email", None)
            or "—"
        )
        phone = (
            getattr(order, "customer_phone", None)
            or getattr(customer, "phone", None)
            or "—"
        )
        address = (
            getattr(order, "delivery_address", None)
            or getattr(customer, "address", None)
            or "—"
        )
        zone_key = str(getattr(order, "delivery_zone", "") or "").strip()
        zone_meta = Config.DELIVERY_ZONES.get(zone_key, {})
        zone_label = zone_meta.get("label") or zone_key.replace("_", " ").title() or "Standard"

        raw_items = getattr(order, "items", None) or []
        items: List[dict[str, Any]] = []
        for item in raw_items:
            items.append(
                {
                    "name": getattr(item, "product_name", None)
                    or getattr(item, "name", "Product"),
                    "sku": getattr(item, "product_sku", None)
                    or getattr(item, "sku", ""),
                    "quantity": int(getattr(item, "quantity", 1) or 1),
                    "unit_price": float(getattr(item, "unit_price", 0.0) or 0.0),
                    "line_total": float(getattr(item, "line_total", 0.0) or 0.0),
                }
            )

        return {
            "order_number": str(getattr(order, "order_number", "STV-ORDER")),
            "status": str(getattr(order, "status", "Order placed")),
            "created_at": self._format_timestamp(getattr(order, "created_at", None)),
            "full_name": str(full_name),
            "email": str(email),
            "phone": str(phone),
            "address": str(address),
            "zone_label": str(zone_label),
            "payment_method": str(
                getattr(order, "payment_method", None) or "Pay on Delivery (Demo)"
            ),
            "notes": str(getattr(order, "notes", "") or "").strip(),
            "items": items,
            "subtotal": float(getattr(order, "subtotal", 0.0) or 0.0),
            "delivery_fee": float(getattr(order, "delivery_fee", 0.0) or 0.0),
            "total_amount": float(getattr(order, "total_amount", 0.0) or 0.0),
        }

    def generate_receipt_png(self, order: Any) -> io.BytesIO:
        """Builds a PNG receipt image for the given order and returns a rewound BytesIO stream."""
        data = self._extract_order_fields(order)

        # Temporary draw context to measure wrapped text heights accurately
        scratch_img = Image.new("RGB", (self.CANVAS_WIDTH, 200), self.BG_COLOR)
        scratch_draw = ImageDraw.Draw(scratch_img)

        card_width = self.CANVAS_WIDTH - (self.OUTER_PAD * 2)
        inner_width = card_width - (self.CARD_PAD * 2)
        name_col_width = 330

        address_lines = self._wrap_text(
            scratch_draw, data["address"], self.font_body, inner_width - 140
        )
        notes_lines = (
            self._wrap_text(
                scratch_draw, data["notes"], self.font_small, inner_width - 24
            )
            if data["notes"]
            else []
        )

        wrapped_items: List[Tuple[dict[str, Any], List[str]]] = []
        items_block_height = 42  # Table header height
        for item in data["items"]:
            lines = self._wrap_text(
                scratch_draw, item["name"], self.font_body_bold, name_col_width
            )
            wrapped_items.append((item, lines))
            row_h = max(46, (len(lines) * 20) + 24)
            items_block_height += row_h

        header_height = 122
        meta_height = 104
        customer_height = 132 + (len(address_lines) * 20)
        notes_height = (44 + len(notes_lines) * 18) if notes_lines else 0
        totals_height = 148
        footer_height = 68

        card_height = (
            header_height
            + meta_height
            + customer_height
            + items_block_height
            + notes_height
            + totals_height
            + footer_height
        )
        canvas_height = card_height + (self.OUTER_PAD * 2)

        img = Image.new("RGB", (self.CANVAS_WIDTH, canvas_height), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        card_left = self.OUTER_PAD
        card_top = self.OUTER_PAD
        card_right = card_left + card_width
        card_bottom = card_top + card_height

        # Outer white receipt card
        draw.rectangle(
            [card_left, card_top, card_right, card_bottom],
            fill=self.CARD_BG,
            outline=self.BORDER_COLOR,
            width=2,
        )

        # Dark navy header banner
        draw.rectangle(
            [card_left, card_top, card_right, card_top + header_height],
            fill=self.HEADER_BG,
        )
        x_start = card_left + self.CARD_PAD
        x_end = card_right - self.CARD_PAD

        draw.text(
            (x_start, card_top + 28),
            Config.APP_NAME.upper(),
            fill="#ffffff",
            font=self.font_title,
        )
        draw.text(
            (x_start, card_top + 66),
            "OFFICIAL ORDER RECEIPT  •  NIGERIA WORKSTATION STORE",
            fill="#94a3b8",
            font=self.font_small,
        )

        # Status pill on top right of header
        status_text = data["status"].upper()
        badge_w = int(draw.textlength(status_text, font=self.font_small)) + 28
        badge_x1 = x_end - badge_w
        badge_y1 = card_top + 42
        draw.rounded_rectangle(
            [badge_x1, badge_y1, x_end, badge_y1 + 32],
            radius=16,
            fill=self.ACCENT_COLOR,
        )
        draw.text(
            (badge_x1 + 14, badge_y1 + 8),
            status_text,
            fill="#ffffff",
            font=self.font_small,
        )

        y = card_top + header_height + 24

        # Order metadata band
        draw.text((x_start, y), "ORDER NUMBER", fill=self.TEXT_MUTED, font=self.font_small)
        draw.text((x_start, y + 18), data["order_number"], fill=self.TEXT_PRIMARY, font=self.font_heading)

        mid_x = x_start + 260
        draw.text((mid_x, y), "ORDER DATE", fill=self.TEXT_MUTED, font=self.font_small)
        draw.text((mid_x, y + 18), data["created_at"], fill=self.TEXT_PRIMARY, font=self.font_body_bold)

        right_col_x = x_start + 490
        draw.text((right_col_x, y), "PAYMENT", fill=self.TEXT_MUTED, font=self.font_small)
        draw.text((right_col_x, y + 18), data["payment_method"], fill=self.TEXT_PRIMARY, font=self.font_body_bold)

        y += 62
        draw.line([x_start, y, x_end, y], fill=self.BORDER_COLOR, width=1)
        y += 20

        # Customer & delivery block
        draw.text((x_start, y), "BILLED & DELIVERED TO", fill=self.TEXT_MUTED, font=self.font_small)
        y += 22
        draw.text((x_start, y), data["full_name"], fill=self.TEXT_PRIMARY, font=self.font_body_bold)
        y += 22
        draw.text(
            (x_start, y),
            f"{data['email']}   •   {data['phone']}",
            fill=self.TEXT_MUTED,
            font=self.font_body,
        )
        y += 22
        draw.text(
            (x_start, y),
            f"Zone: {data['zone_label']}",
            fill=self.TEXT_PRIMARY,
            font=self.font_body_bold,
        )
        y += 22
        for line in address_lines:
            draw.text((x_start, y), line, fill=self.TEXT_MUTED, font=self.font_body)
            y += 20

        y += 16

        # Items table header
        draw.rectangle([x_start, y, x_end, y + 36], fill="#e2e8f0")
        col_qty_x = x_start + 365
        col_unit_x = x_start + 445
        col_total_x = x_end - 12

        draw.text((x_start + 12, y + 10), "ITEM", fill=self.TEXT_PRIMARY, font=self.font_small)
        draw.text((col_qty_x, y + 10), "QTY", fill=self.TEXT_PRIMARY, font=self.font_small)
        draw.text((col_unit_x, y + 10), "UNIT PRICE", fill=self.TEXT_PRIMARY, font=self.font_small)
        total_hdr = "LINE TOTAL"
        total_hdr_w = draw.textlength(total_hdr, font=self.font_small)
        draw.text((col_total_x - total_hdr_w, y + 10), total_hdr, fill=self.TEXT_PRIMARY, font=self.font_small)
        y += 38

        # Item rows
        for idx, (item, lines) in enumerate(wrapped_items):
            row_h = max(46, (len(lines) * 20) + 24)
            if idx % 2 == 1:
                draw.rectangle([x_start, y, x_end, y + row_h], fill=self.ROW_ALT_BG)

            text_y = y + 10
            for line in lines:
                draw.text((x_start + 12, text_y), line, fill=self.TEXT_PRIMARY, font=self.font_body_bold)
                text_y += 20
            if item["sku"]:
                draw.text((x_start + 12, text_y), f"SKU: {item['sku']}", fill=self.TEXT_MUTED, font=self.font_small)

            draw.text((col_qty_x + 8, y + 12), str(item["quantity"]), fill=self.TEXT_PRIMARY, font=self.font_body)
            draw.text(
                (col_unit_x, y + 12),
                self._format_ngn(item["unit_price"]),
                fill=self.TEXT_MUTED,
                font=self.font_body,
            )
            line_total_str = self._format_ngn(item["line_total"])
            lt_w = draw.textlength(line_total_str, font=self.font_body_bold)
            draw.text(
                (col_total_x - lt_w, y + 12),
                line_total_str,
                fill=self.TEXT_PRIMARY,
                font=self.font_body_bold,
            )

            y += row_h
            draw.line([x_start, y, x_end, y], fill="#e2e8f0", width=1)

        # Optional order notes
        if notes_lines:
            y += 14
            box_h = 26 + (len(notes_lines) * 18)
            draw.rectangle([x_start, y, x_end, y + box_h], fill=self.ROW_ALT_BG, outline="#e2e8f0")
            draw.text((x_start + 12, y + 6), "Delivery Note:", fill=self.TEXT_PRIMARY, font=self.font_small)
            ny = y + 22
            for line in notes_lines:
                draw.text((x_start + 12, ny), line, fill=self.TEXT_MUTED, font=self.font_small)
                ny += 18
            y += box_h

        y += 20

        # Totals summary (right-aligned)
        summary_label_x = x_end - 290
        sub_str = self._format_ngn(data["subtotal"])
        deliv_str = "FREE" if data["delivery_fee"] == 0 else self._format_ngn(data["delivery_fee"])
        grand_str = self._format_ngn(data["total_amount"])

        draw.text((summary_label_x, y), "Items Subtotal:", fill=self.TEXT_MUTED, font=self.font_body)
        draw.text(
            (x_end - draw.textlength(sub_str, font=self.font_body_bold), y),
            sub_str,
            fill=self.TEXT_PRIMARY,
            font=self.font_body_bold,
        )
        y += 26

        draw.text((summary_label_x, y), "Delivery Fee:", fill=self.TEXT_MUTED, font=self.font_body)
        draw.text(
            (x_end - draw.textlength(deliv_str, font=self.font_body_bold), y),
            deliv_str,
            fill=self.TEXT_PRIMARY,
            font=self.font_body_bold,
        )
        y += 30

        draw.line([summary_label_x, y, x_end, y], fill=self.TEXT_PRIMARY, width=2)
        y += 14

        draw.text((summary_label_x, y + 2), "TOTAL PAID:", fill=self.TEXT_PRIMARY, font=self.font_heading)
        draw.text(
            (x_end - draw.textlength(grand_str, font=self.font_total), y),
            grand_str,
            fill=self.ACCENT_COLOR,
            font=self.font_total,
        )

        # Footer note
        footer_y = card_bottom - 44
        draw.line([x_start, footer_y - 12, x_end, footer_y - 12], fill=self.BORDER_COLOR, width=1)
        draw.text(
            (x_start, footer_y),
            f"Thank you for shopping with {Config.APP_NAME}. Track your order anytime at /track-order.",
            fill=self.TEXT_MUTED,
            font=self.font_small,
        )

        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        return buffer