"""services/analytics_service.py

Pandas business analytics engine, Plotly interactive chart generator,
and CSV report exporter for Setuvo's local sales and inventory dashboard.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from config import Config
from database.db_manager import DatabaseManager
from models.entities import format_naira


class AnalyticsService:
    """Computes sales KPIs, builds Plotly visualizations, and exports CSV reports."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        exports_dir: Optional[Path] = None,
    ) -> None:
        self.db: DatabaseManager = db_manager
        self.exports_dir: Path = Path(exports_dir or Config.EXPORTS_DIR)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # SQLite -> Pandas DataFrame Loaders
    # ------------------------------------------------------------------
    def _load_dataframes(
        self,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Loads orders, order_items, and products into normalized Pandas DataFrames."""
        order_rows = self.db.fetch_all(
            """
            SELECT
                o.id,
                o.order_number,
                o.delivery_zone,
                o.subtotal,
                o.delivery_fee,
                o.total_amount,
                o.status,
                o.created_at,
                cu.full_name AS customer_name,
                cu.email AS customer_email
            FROM orders o
            JOIN customers cu ON o.customer_id = cu.id
            ORDER BY o.created_at ASC, o.id ASC;
            """
        )
        orders_cols = [
            "id",
            "order_number",
            "delivery_zone",
            "subtotal",
            "delivery_fee",
            "total_amount",
            "status",
            "created_at",
            "customer_name",
            "customer_email",
        ]
        orders_df = (
            pd.DataFrame([dict(r) for r in order_rows])
            if order_rows
            else pd.DataFrame(columns=orders_cols)
        )

        item_rows = self.db.fetch_all(
            """
            SELECT
                oi.id,
                oi.order_id,
                o.order_number,
                o.status AS order_status,
                o.created_at AS order_created_at,
                oi.product_id,
                oi.product_sku,
                oi.product_name,
                oi.quantity,
                oi.unit_price,
                oi.line_total,
                COALESCE(c.name, 'Uncategorized') AS category_name
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            LEFT JOIN products p ON oi.product_id = p.id
            LEFT JOIN categories c ON p.category_id = c.id
            ORDER BY o.created_at ASC, oi.id ASC;
            """
        )
        items_cols = [
            "id",
            "order_id",
            "order_number",
            "order_status",
            "order_created_at",
            "product_id",
            "product_sku",
            "product_name",
            "quantity",
            "unit_price",
            "line_total",
            "category_name",
        ]
        items_df = (
            pd.DataFrame([dict(r) for r in item_rows])
            if item_rows
            else pd.DataFrame(columns=items_cols)
        )

        prod_rows = self.db.fetch_all(
            """
            SELECT
                p.id,
                p.sku,
                p.name,
                p.brand,
                p.price,
                p.stock,
                p.is_active,
                p.is_featured,
                p.is_bestseller,
                c.name AS category_name,
                c.slug AS category_slug
            FROM products p
            JOIN categories c ON p.category_id = c.id
            ORDER BY c.display_order ASC, p.name ASC;
            """
        )
        prods_cols = [
            "id",
            "sku",
            "name",
            "brand",
            "price",
            "stock",
            "is_active",
            "is_featured",
            "is_bestseller",
            "category_name",
            "category_slug",
        ]
        products_df = (
            pd.DataFrame([dict(r) for r in prod_rows])
            if prod_rows
            else pd.DataFrame(columns=prods_cols)
        )

        return orders_df, items_df, products_df

    # ------------------------------------------------------------------
    # Pandas Sales & Inventory KPI Aggregations
    # ------------------------------------------------------------------
    def get_sales_summary(self, top_n: int = 8) -> Dict[str, Any]:
        """Calculates comprehensive business KPIs, category breakdowns, and stock alerts."""
        orders_df, items_df, products_df = self._load_dataframes()

        # Order status distribution (includes Cancelled orders)
        status_distribution: List[Dict[str, Any]] = []
        if not orders_df.empty:
            status_counts = (
                orders_df["status"]
                .value_counts()
                .reindex(Config.ORDER_STATUSES, fill_value=0)
            )
            for status_name, cnt in status_counts.items():
                if int(cnt) > 0:
                    status_distribution.append(
                        {"status": str(status_name), "count": int(cnt)}
                    )

        active_orders = (
            orders_df[orders_df["status"] != "Cancelled"].copy()
            if not orders_df.empty
            else orders_df.copy()
        )
        active_items = (
            items_df[items_df["order_status"] != "Cancelled"].copy()
            if not items_df.empty
            else items_df.copy()
        )

        total_sales = (
            round(float(active_orders["total_amount"].sum()), 2)
            if not active_orders.empty
            else 0.0
        )
        product_revenue = (
            round(float(active_orders["subtotal"].sum()), 2)
            if not active_orders.empty
            else 0.0
        )
        delivery_revenue = (
            round(float(active_orders["delivery_fee"].sum()), 2)
            if not active_orders.empty
            else 0.0
        )
        order_count = int(len(active_orders))
        cancelled_count = (
            int((orders_df["status"] == "Cancelled").sum())
            if not orders_df.empty
            else 0
        )
        average_order_value = (
            round(total_sales / order_count, 2) if order_count > 0 else 0.0
        )
        total_units_sold = (
            int(active_items["quantity"].sum()) if not active_items.empty else 0
        )

        # Bestselling products by units sold & revenue
        bestselling_products: List[Dict[str, Any]] = []
        if not active_items.empty:
            prod_grouped = (
                active_items.groupby(
                    ["product_sku", "product_name", "category_name"], as_index=False
                )
                .agg(
                    units_sold=("quantity", "sum"),
                    revenue=("line_total", "sum"),
                )
                .sort_values(
                    by=["units_sold", "revenue", "product_name"],
                    ascending=[False, False, True],
                )
                .head(max(1, int(top_n)))
            )
            for _, row in prod_grouped.iterrows():
                rev = round(float(row["revenue"]), 2)
                bestselling_products.append(
                    {
                        "sku": str(row["product_sku"]),
                        "product_name": str(row["product_name"]),
                        "category_name": str(row["category_name"]),
                        "units_sold": int(row["units_sold"]),
                        "revenue": rev,
                        "formatted_revenue": format_naira(rev),
                    }
                )

        # Revenue by product category
        revenue_by_category: List[Dict[str, Any]] = []
        if not active_items.empty:
            cat_grouped = (
                active_items.groupby("category_name", as_index=False)
                .agg(
                    units_sold=("quantity", "sum"),
                    revenue=("line_total", "sum"),
                )
                .sort_values(by=["revenue", "units_sold"], ascending=[False, False])
            )
            total_cat_rev = float(cat_grouped["revenue"].sum()) or 1.0
            for _, row in cat_grouped.iterrows():
                rev = round(float(row["revenue"]), 2)
                revenue_by_category.append(
                    {
                        "category_name": str(row["category_name"]),
                        "units_sold": int(row["units_sold"]),
                        "revenue": rev,
                        "formatted_revenue": format_naira(rev),
                        "share_pct": round((rev / total_cat_rev) * 100.0, 1),
                    }
                )

        # Monthly sales trend
        monthly_sales: List[Dict[str, Any]] = []
        if not active_orders.empty:
            parsed_dates = pd.to_datetime(
                active_orders["created_at"], errors="coerce", utc=True
            )
            valid_mask = parsed_dates.notna()
            if valid_mask.any():
                temp_orders = active_orders.loc[valid_mask].copy()
                temp_orders["month"] = parsed_dates.loc[valid_mask].dt.strftime("%Y-%m")
                month_grouped = (
                    temp_orders.groupby("month", as_index=False)
                    .agg(
                        order_count=("id", "count"),
                        revenue=("total_amount", "sum"),
                    )
                    .sort_values(by="month", ascending=True)
                )
                for _, row in month_grouped.iterrows():
                    rev = round(float(row["revenue"]), 2)
                    monthly_sales.append(
                        {
                            "month": str(row["month"]),
                            "order_count": int(row["order_count"]),
                            "revenue": rev,
                            "formatted_revenue": format_naira(rev),
                        }
                    )

        # Low-stock & out-of-stock active products + inventory valuation
        low_stock_products: List[Dict[str, Any]] = []
        inventory_items: List[Dict[str, Any]] = []
        total_stock_units = 0
        inventory_retail_value = 0.0

        if not products_df.empty:
            active_prods = products_df[products_df["is_active"] == 1].copy()
            if not active_prods.empty:
                total_stock_units = int(active_prods["stock"].sum())
                inventory_retail_value = round(
                    float((active_prods["price"] * active_prods["stock"]).sum()), 2
                )

                for _, row in active_prods.iterrows():
                    stock_qty = int(row["stock"])
                    price_val = round(float(row["price"]), 2)
                    if stock_qty == 0:
                        status_label = "Out of stock"
                    elif stock_qty <= Config.LOW_STOCK_THRESHOLD:
                        status_label = "Low stock"
                    else:
                        status_label = "In stock"

                    item_entry = {
                        "id": int(row["id"]),
                        "sku": str(row["sku"]),
                        "name": str(row["name"]),
                        "category_name": str(row["category_name"]),
                        "stock": stock_qty,
                        "stock_status": status_label,
                        "price": price_val,
                        "formatted_price": format_naira(price_val),
                    }
                    inventory_items.append(item_entry)
                    if stock_qty <= Config.LOW_STOCK_THRESHOLD:
                        low_stock_products.append(item_entry)

                low_stock_products.sort(key=lambda x: (x["stock"], x["name"]))

        return {
            "total_sales": total_sales,
            "formatted_total_sales": format_naira(total_sales),
            "product_revenue": product_revenue,
            "formatted_product_revenue": format_naira(product_revenue),
            "delivery_revenue": delivery_revenue,
            "formatted_delivery_revenue": format_naira(delivery_revenue),
            "order_count": order_count,
            "cancelled_count": cancelled_count,
            "total_orders_all": int(len(orders_df)),
            "average_order_value": average_order_value,
            "formatted_average_order_value": format_naira(average_order_value),
            "total_units_sold": total_units_sold,
            "total_stock_units": total_stock_units,
            "inventory_retail_value": inventory_retail_value,
            "formatted_inventory_retail_value": format_naira(inventory_retail_value),
            "bestselling_products": bestselling_products,
            "revenue_by_category": revenue_by_category,
            "monthly_sales": monthly_sales,
            "status_distribution": status_distribution,
            "low_stock_products": low_stock_products,
            "inventory_items": inventory_items,
        }

    # ------------------------------------------------------------------
    # Interactive Plotly Visualizations
    # ------------------------------------------------------------------
    @staticmethod
    def _figure_to_html(fig: go.Figure) -> str:
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#f8fafc",
            font=dict(family="Inter, system-ui, sans-serif", color="#0f172a", size=12),
            margin=dict(l=36, r=24, t=44, b=36),
            height=330,
        )
        return pio.to_html(
            fig,
            full_html=False,
            include_plotlyjs=False,
            config={"responsive": True, "displayModeBar": False},
        )

    @staticmethod
    def _empty_figure(title: str, message: str) -> go.Figure:
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=13, color="#64748b"),
        )
        fig.update_layout(
            title=dict(text=title, x=0.02, font=dict(size=15)),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        return fig

    def build_plotly_charts(
        self, summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Builds 5 interactive Plotly charts for Setuvo's business analytics page."""
        data = summary if summary is not None else self.get_sales_summary()

        # 1. Revenue Over Time (Monthly Trend)
        monthly = data.get("monthly_sales", [])
        if monthly:
            fig_rev = go.Figure(
                data=[
                    go.Bar(
                        x=[m["month"] for m in monthly],
                        y=[m["revenue"] for m in monthly],
                        name="Revenue (₦)",
                        marker_color="#0f766e",
                        hovertemplate="Month: %{x}<br>Revenue: ₦%{y:,.2f}<extra></extra>",
                    ),
                    go.Scatter(
                        x=[m["month"] for m in monthly],
                        y=[m["revenue"] for m in monthly],
                        mode="lines+markers",
                        name="Trend",
                        line=dict(color="#f59e0b", width=2.5),
                        marker=dict(size=7),
                        hoverinfo="skip",
                    ),
                ]
            )
            fig_rev.update_layout(
                title=dict(text="Monthly Revenue (NGN)", x=0.02, font=dict(size=15)),
                yaxis=dict(title="Revenue (₦)", gridcolor="#e2e8f0"),
                xaxis=dict(title="Month", type="category"),
                showlegend=False,
            )
        else:
            fig_rev = self._empty_figure(
                "Monthly Revenue (NGN)", "No completed order data recorded yet."
            )

        # 2. Sales by Category
        categories = data.get("revenue_by_category", [])
        if categories:
            fig_cat = go.Figure(
                data=[
                    go.Bar(
                        x=[c["category_name"] for c in categories],
                        y=[c["revenue"] for c in categories],
                        marker_color="#0284c7",
                        hovertemplate="%{x}<br>Revenue: ₦%{y:,.2f}<extra></extra>",
                    )
                ]
            )
            fig_cat.update_layout(
                title=dict(text="Sales by Product Category", x=0.02, font=dict(size=15)),
                yaxis=dict(title="Revenue (₦)", gridcolor="#e2e8f0"),
                xaxis=dict(title="Category", tickangle=-18),
            )
        else:
            fig_cat = self._empty_figure(
                "Sales by Product Category", "No category sales recorded yet."
            )

        # 3. Top-Selling Products (Horizontal Bar)
        top_prods = data.get("bestselling_products", [])[:6]
        if top_prods:
            reversed_prods = list(reversed(top_prods))
            fig_top = go.Figure(
                data=[
                    go.Bar(
                        x=[p["units_sold"] for p in reversed_prods],
                        y=[
                            (p["product_name"][:32] + "…")
                            if len(p["product_name"]) > 33
                            else p["product_name"]
                            for p in reversed_prods
                        ],
                        orientation="h",
                        marker_color="#14b8a6",
                        customdata=[p["formatted_revenue"] for p in reversed_prods],
                        hovertemplate="%{y}<br>Units Sold: %{x}<br>Revenue: %{customdata}<extra></extra>",
                    )
                ]
            )
            fig_top.update_layout(
                title=dict(text="Top-Selling Products (Units)", x=0.02, font=dict(size=15)),
                xaxis=dict(title="Units Sold", gridcolor="#e2e8f0", dtick=1),
                yaxis=dict(automargin=True),
            )
        else:
            fig_top = self._empty_figure(
                "Top-Selling Products (Units)", "No product sales recorded yet."
            )

        # 4. Order Distribution by Status
        statuses = data.get("status_distribution", [])
        status_palette = {
            "Order placed": "#0284c7",
            "Processing": "#f59e0b",
            "Shipped": "#6366f1",
            "Delivered": "#0f766e",
            "Cancelled": "#ef4444",
        }
        if statuses:
            fig_status = go.Figure(
                data=[
                    go.Pie(
                        labels=[s["status"] for s in statuses],
                        values=[s["count"] for s in statuses],
                        hole=0.48,
                        marker=dict(
                            colors=[
                                status_palette.get(s["status"], "#64748b")
                                for s in statuses
                            ]
                        ),
                        textinfo="label+value",
                        hovertemplate="%{label}: %{value} order(s) (%{percent})<extra></extra>",
                    )
                ]
            )
            fig_status.update_layout(
                title=dict(text="Orders by Fulfillment Status", x=0.02, font=dict(size=15)),
                showlegend=True,
            )
        else:
            fig_status = self._empty_figure(
                "Orders by Fulfillment Status", "No orders placed yet."
            )

        # 5. Inventory Stock Levels (Sorted lowest stock first to highlight restock needs)
        inv_items = sorted(
            data.get("inventory_items", []), key=lambda x: (x["stock"], x["sku"])
        )
        if inv_items:
            bar_colors = []
            for item in inv_items:
                if item["stock"] == 0:
                    bar_colors.append("#ef4444")  # Out of stock
                elif item["stock"] <= Config.LOW_STOCK_THRESHOLD:
                    bar_colors.append("#f59e0b")  # Low stock
                else:
                    bar_colors.append("#0f766e")  # Healthy stock

            fig_inv = go.Figure(
                data=[
                    go.Bar(
                        x=[item["sku"] for item in inv_items],
                        y=[item["stock"] for item in inv_items],
                        marker_color=bar_colors,
                        customdata=[
                            (item["name"], item["stock_status"]) for item in inv_items
                        ],
                        hovertemplate=(
                            "SKU: %{x}<br>%{customdata[0]}<br>"
                            "Stock: %{y} unit(s) (%{customdata[1]})<extra></extra>"
                        ),
                    )
                ]
            )
            fig_inv.update_layout(
                title=dict(
                    text="Current Inventory Levels by SKU (Red = Out, Amber = Low ≤ 5)",
                    x=0.02,
                    font=dict(size=15),
                ),
                yaxis=dict(title="Units in Stock", gridcolor="#e2e8f0"),
                xaxis=dict(title="Product SKU", tickangle=-35),
            )
        else:
            fig_inv = self._empty_figure(
                "Current Inventory Levels", "No active products in catalog."
            )

        return {
            "revenue_over_time": self._figure_to_html(fig_rev),
            "sales_by_category": self._figure_to_html(fig_cat),
            "top_products": self._figure_to_html(fig_top),
            "order_status": self._figure_to_html(fig_status),
            "inventory_levels": self._figure_to_html(fig_inv),
        }

    # ------------------------------------------------------------------
    # CSV Report Generation & File Export
    # ------------------------------------------------------------------
    def export_sales_report_csv(
        self, filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Exports itemized order sales records to CSV in Setuvo/exports/."""
        _, items_df, _ = self._load_dataframes()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        clean_name = (filename or f"setuvo_sales_report_{stamp}.csv").strip()
        if not clean_name.endswith(".csv"):
            clean_name = f"{clean_name}.csv"

        if items_df.empty:
            export_df = pd.DataFrame(
                columns=[
                    "order_number",
                    "order_status",
                    "order_created_at",
                    "product_sku",
                    "product_name",
                    "category_name",
                    "quantity",
                    "unit_price_ngn",
                    "line_total_ngn",
                ]
            )
        else:
            export_df = items_df[
                [
                    "order_number",
                    "order_status",
                    "order_created_at",
                    "product_sku",
                    "product_name",
                    "category_name",
                    "quantity",
                    "unit_price",
                    "line_total",
                ]
            ].rename(
                columns={
                    "unit_price": "unit_price_ngn",
                    "line_total": "line_total_ngn",
                }
            )

        target_path = self.exports_dir / clean_name
        csv_text = export_df.to_csv(index=False)
        target_path.write_text(csv_text, encoding="utf-8")

        return {
            "filepath": target_path,
            "filename": clean_name,
            "csv_content": csv_text,
            "row_count": int(len(export_df)),
        }

    def export_inventory_report_csv(
        self, filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Exports current product stock levels and retail valuations to CSV."""
        _, _, products_df = self._load_dataframes()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        clean_name = (filename or f"setuvo_inventory_report_{stamp}.csv").strip()
        if not clean_name.endswith(".csv"):
            clean_name = f"{clean_name}.csv"

        if products_df.empty:
            export_df = pd.DataFrame(
                columns=[
                    "sku",
                    "name",
                    "brand",
                    "category_name",
                    "price_ngn",
                    "stock",
                    "stock_status",
                    "retail_valuation_ngn",
                    "is_active",
                ]
            )
        else:
            export_df = products_df.copy()
            export_df["stock_status"] = export_df["stock"].apply(
                lambda s: "Out of stock"
                if int(s) == 0
                else ("Low stock" if int(s) <= Config.LOW_STOCK_THRESHOLD else "In stock")
            )
            export_df["retail_valuation_ngn"] = (
                export_df["price"] * export_df["stock"]
            ).round(2)
            export_df = export_df[
                [
                    "sku",
                    "name",
                    "brand",
                    "category_name",
                    "price",
                    "stock",
                    "stock_status",
                    "retail_valuation_ngn",
                    "is_active",
                ]
            ].rename(columns={"price": "price_ngn"})

        target_path = self.exports_dir / clean_name
        csv_text = export_df.to_csv(index=False)
        target_path.write_text(csv_text, encoding="utf-8")

        return {
            "filepath": target_path,
            "filename": clean_name,
            "csv_content": csv_text,
            "row_count": int(len(export_df)),
        }