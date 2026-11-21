"""scripts/sales_report.py

Command-line Pandas sales & inventory reporting utility for Setuvo.

Usage examples:
    python scripts/sales_report.py
    python scripts/sales_report.py --export-csv all
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from database.db_manager import DatabaseManager
from database.seed_data import seed_database
from services.analytics_service import AnalyticsService


def generate_cli_report(
    db_path: Optional[str] = None,
    exports_dir: Optional[str] = None,
    export_mode: str = "none",
) -> int:
    target_db = db_path or str(Config.DATABASE_PATH)
    target_exports = Path(exports_dir) if exports_dir else Config.EXPORTS_DIR
    target_exports.mkdir(parents=True, exist_ok=True)

    db_manager = DatabaseManager(db_path=target_db)
    db_manager.init_db()
    existing = db_manager.fetch_one("SELECT COUNT(*) AS cnt FROM categories;")
    if existing is None or int(existing["cnt"]) == 0:
        seed_database(db_manager, include_sample_orders=False)

    analytics = AnalyticsService(db_manager=db_manager, exports_dir=target_exports)
    summary = analytics.get_sales_summary()

    print("=" * 64)
    print("SETUVO — SALES & INVENTORY ANALYTICS REPORT (NGN)")
    print("=" * 64)
    print(f"Net Sales Revenue      : {summary['formatted_total_sales']}")
    print(f"  - Product Revenue    : {summary['formatted_product_revenue']}")
    print(f"  - Delivery Revenue   : {summary['formatted_delivery_revenue']}")
    print(f"Active Orders          : {summary['order_count']}")
    print(f"Total Units Sold       : {summary['total_units_sold']}")
    print(f"Average Order Value    : {summary['formatted_average_order_value']}")
    print(f"Inventory Valuation    : {summary['formatted_inventory_retail_value']}")
    print(f"Units in Stock         : {summary['total_stock_units']}")
    print(f"Low-Stock Alerts       : {len(summary['low_stock_products'])}")
    print("-" * 64)

    if summary["bestselling_products"]:
        print("Top Selling Products:")
        for idx, item in enumerate(summary["bestselling_products"][:5], start=1):
            print(
                f"  {idx}. {item['product_name']} "
                f"({item['units_sold']} units | {item['formatted_revenue']})"
            )
    else:
        print("Top Selling Products: No completed orders recorded yet.")

    if export_mode in ("sales", "all"):
        sales_csv = analytics.export_sales_report_csv()
        out_path = target_exports / sales_csv["filename"]
        out_path.write_text(sales_csv["csv_content"], encoding="utf-8")
        print(f"Exported Sales CSV     : {out_path}")

    if export_mode in ("inventory", "all"):
        inv_csv = analytics.export_inventory_report_csv()
        out_path = target_exports / inv_csv["filename"]
        out_path.write_text(inv_csv["csv_content"], encoding="utf-8")
        print(f"Exported Inventory CSV : {out_path}")

    print("=" * 64)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Setuvo Pandas Sales & Inventory Report CLI"
    )
    parser.add_argument("--db-path", default=None, help="Custom SQLite database path.")
    parser.add_argument(
        "--exports-dir", default=None, help="Directory for generated CSV files."
    )
    parser.add_argument(
        "--export-csv",
        choices=["none", "sales", "inventory", "all"],
        default="none",
        help="Optionally write CSV report file(s) to disk.",
    )
    args = parser.parse_args(argv)
    return generate_cli_report(
        db_path=args.db_path,
        exports_dir=args.exports_dir,
        export_mode=args.export_csv,
    )


if __name__ == "__main__":
    raise SystemExit(main())