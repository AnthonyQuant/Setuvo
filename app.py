"""app.py

Flask application factory, service dependency wiring, CSRF protection,
Jinja2 template filters, global navigation context, full storefront/checkout/
analytics routes, and centralized error handlers for Setuvo.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from flask import (
    Flask,
    Response,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.datastructures import MultiDict

from config import Config
from database.db_manager import DatabaseManager
from database.seed_data import (
    PRODUCTS as SEED_PRODUCTS,
    resolve_product_image_url,
    seed_database,
)
from forms.checkout_form import GuestCheckoutForm, OrderTrackingForm
from forms.search_form import (
    ProductComparisonForm,
    ProductSearchForm,
    SetupBuilderForm,
)
from models.entities import format_naira
from services.analytics_service import AnalyticsService
from services.cart_service import CartService
from services.email_service import EmailService
from services.exceptions import EmptyCartError, SetuvoError
from services.inventory_service import InventoryService
from services.order_service import OrderService
from services.product_service import ProductService
from services.receipt_service import ReceiptService
from services.setup_service import SetupService

csrf = CSRFProtect()


def get_services() -> Dict[str, Any]:
    """Returns the wired service container attached to the active Flask app."""
    return current_app.extensions["services"]


def get_safe_redirect_url(
    candidate: Optional[str], fallback_endpoint: str = "index"
) -> str:
    """Validates that a redirect target stays on the same host (prevents open redirects)."""
    fallback = url_for(fallback_endpoint)
    if not candidate:
        return fallback

    raw = str(candidate).strip()
    if not raw or raw.startswith("//") or "\\" in raw:
        return fallback

    host_url = urlparse(request.host_url)
    target_url = urlparse(urljoin(request.host_url, raw))
    if target_url.scheme in ("http", "https") and target_url.netloc == host_url.netloc:
        path = target_url.path or "/"
        if target_url.query:
            return f"{path}?{target_url.query}"
        return path
    return fallback


def _register_template_helpers(app: Flask) -> None:
    """Registers custom Jinja2 filters and global template context variables."""

    @app.template_filter("naira")
    def naira_filter(amount: Optional[float]) -> str:
        return format_naira(amount)

    @app.template_filter("short_date")
    def short_date_filter(iso_timestamp: Optional[str]) -> str:
        if not iso_timestamp:
            return "—"
        raw = str(iso_timestamp).strip()
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return parsed.strftime("%d %b %Y, %H:%M UTC")
        except ValueError:
            return raw[:16]

    @app.template_filter("status_badge_class")
    def status_badge_class_filter(status: Optional[str]) -> str:
        mapping = {
            "Order placed": "status-placed",
            "Processing": "status-processing",
            "Shipped": "status-shipped",
            "Delivered": "status-delivered",
            "Cancelled": "status-cancelled",
        }
        return mapping.get(str(status or "").strip(), "status-placed")

    @app.context_processor
    def inject_storefront_context() -> Dict[str, Any]:
        services = app.extensions["services"]
        product_service: ProductService = services["product_service"]
        cart_service: CartService = services["cart_service"]

        try:
            nav_categories = product_service.get_categories(include_empty=True)
        except Exception:
            nav_categories = []

        return {
            "app_name": Config.APP_NAME,
            "app_tagline": Config.APP_TAGLINE,
            "currency_symbol": Config.CURRENCY_SYMBOL,
            "nav_categories": nav_categories,
            "setup_purposes": Config.SETUP_PURPOSES,
            "delivery_zones": Config.DELIVERY_ZONES,
            "cart_count": cart_service.get_cart_count(session),
            "wishlist_count": cart_service.get_wishlist_count(session),
            "wishlist_ids": cart_service.get_wishlist_ids(session),
            "current_year": datetime.now(timezone.utc).year,
        }


def _register_error_handlers(app: Flask) -> None:
    """Registers centralized error pages and JSON API error responses."""

    def _render_error(
        status_code: int, title: str, message: str, details: Optional[str] = None
    ):
        if request.path.startswith("/api/"):
            payload: Dict[str, Any] = {
                "status": "error",
                "code": status_code,
                "title": title,
                "message": message,
            }
            if details:
                payload["details"] = details
            return jsonify(payload), status_code

        return (
            render_template(
                "error.html",
                status_code=status_code,
                error_title=title,
                error_message=message,
                error_details=details,
            ),
            status_code,
        )

    @app.errorhandler(SetuvoError)
    def handle_domain_error(exc: SetuvoError):
        return _render_error(
            status_code=exc.status_code,
            title="Request Could Not Be Completed",
            message=exc.message,
            details=exc.details,
        )

    @app.errorhandler(CSRFError)
    def handle_csrf_error(exc: CSRFError):
        return _render_error(
            status_code=400,
            title="Session Security Token Expired",
            message="Your form security token was missing or expired. Please refresh the page and try again.",
            details=exc.description,
        )

    @app.errorhandler(400)
    def handle_bad_request(exc):
        return _render_error(
            status_code=400,
            title="Bad Request",
            message="The submitted request could not be understood.",
        )

    @app.errorhandler(404)
    def handle_not_found(exc):
        return _render_error(
            status_code=404,
            title="Page Not Found",
            message="The page, product, or order you requested does not exist on Setuvo.",
        )

    @app.errorhandler(405)
    def handle_method_not_allowed(exc):
        return _render_error(
            status_code=405,
            title="Method Not Allowed",
            message="That action is not supported on this endpoint.",
        )

    @app.errorhandler(500)
    def handle_internal_error(exc):
        return _render_error(
            status_code=500,
            title="Internal Server Error",
            message="An unexpected error occurred while processing your request.",
        )


def _register_core_routes(app: Flask) -> None:
    """Registers core operational routes."""

    @app.get("/api/health")
    def api_health():
        services = get_services()
        db_manager: DatabaseManager = services["db_manager"]
        try:
            tables = db_manager.get_table_names()
            row = db_manager.fetch_one(
                "SELECT COUNT(*) AS cnt FROM products WHERE is_active = 1;"
            )
            active_products = int(row["cnt"]) if row else 0
            return jsonify(
                {
                    "status": "ok",
                    "app": Config.APP_NAME,
                    "currency": Config.CURRENCY_CODE,
                    "tables_ready": len(tables) >= 8,
                    "table_count": len(tables),
                    "active_products": active_products,
                }
            ), 200
        except Exception as exc:
            return jsonify(
                {
                    "status": "degraded",
                    "app": Config.APP_NAME,
                    "error": str(exc),
                }
            ), 503


def _register_catalog_routes(app: Flask) -> None:
    """Registers storefront discovery, catalogue search, comparison, and wishlist routes."""

    @app.get("/")
    def index():
        services = get_services()
        product_service: ProductService = services["product_service"]
        setup_service: SetupService = services["setup_service"]

        categories = product_service.get_categories(include_empty=True)
        featured_products = product_service.get_featured_products(limit=6)
        bestsellers = product_service.get_bestsellers(limit=4)
        bundles = setup_service.get_all_bundles(include_inactive=False)
        purpose_options = setup_service.get_purpose_options()

        return render_template(
            "index.html",
            categories=categories,
            featured_products=featured_products,
            bestsellers=bestsellers,
            bundles=bundles,
            purpose_options=purpose_options,
        )

    @app.get("/catalogue")
    def catalogue():
        services = get_services()
        product_service: ProductService = services["product_service"]

        filter_options = product_service.get_filter_options()
        form = ProductSearchForm(formdata=request.args)
        form.populate_filter_choices(filter_options)

        if request.args:
            form.validate()

        min_price = float(form.min_price.data) if form.min_price.data is not None else None
        max_price = float(form.max_price.data) if form.max_price.data is not None else None

        products = product_service.search_and_filter_products(
            query=form.q.data,
            category_slug=form.category.data or "all",
            brand=form.brand.data or "all",
            product_type=form.product_type.data or "all",
            min_price=min_price,
            max_price=max_price,
            availability=form.availability.data or "all",
            sort_by=form.sort_by.data or "featured",
            include_inactive=False,
        )

        active_category = None
        selected_cat_slug = (form.category.data or "all").strip().lower()
        if selected_cat_slug != "all":
            for cat in filter_options["categories"]:
                if cat["slug"] == selected_cat_slug:
                    active_category = cat
                    break

        return render_template(
            "catalogue.html",
            form=form,
            products=products,
            filter_options=filter_options,
            active_category=active_category,
            result_count=len(products),
        )

    @app.get("/product/<int:product_id>")
    def product_detail(product_id: int):
        services = get_services()
        product_service: ProductService = services["product_service"]

        product = product_service.get_product_by_id(product_id, include_inactive=False)
        related_products = product_service.get_related_products(product, limit=4)

        return render_template(
            "product.html",
            product=product,
            related_products=related_products,
        )

    @app.get("/compare")
    def compare_products():
        services = get_services()
        product_service: ProductService = services["product_service"]

        all_products = product_service.search_and_filter_products(
            sort_by="featured", include_inactive=False
        )

        if "ids" in request.args and "product_1" not in request.args:
            raw_ids: List[int] = []
            for part in str(request.args.get("ids", "")).split(","):
                try:
                    pid = int(part.strip())
                    if pid > 0 and pid not in raw_ids:
                        raw_ids.append(pid)
                except ValueError:
                    continue
            mapped = MultiDict(
                {
                    "product_1": str(raw_ids[0]) if len(raw_ids) >= 1 else "0",
                    "product_2": str(raw_ids[1]) if len(raw_ids) >= 2 else "0",
                    "product_3": str(raw_ids[2]) if len(raw_ids) >= 3 else "0",
                }
            )
            form = ProductComparisonForm(formdata=mapped)
        elif request.args:
            form = ProductComparisonForm(formdata=request.args)
        else:
            default_1 = all_products[0].id if len(all_products) >= 1 else 0
            default_2 = all_products[1].id if len(all_products) >= 2 else 0
            form = ProductComparisonForm(
                data={"product_1": default_1, "product_2": default_2, "product_3": 0}
            )

        form.populate_product_choices(all_products)

        comparison_matrix: Optional[Dict[str, Any]] = None
        if request.args:
            if form.validate():
                comparison_matrix = product_service.build_comparison_matrix(
                    form.get_selected_ids()
                )
        elif len(all_products) >= 2:
            comparison_matrix = product_service.build_comparison_matrix(
                [all_products[0].id, all_products[1].id]
            )

        return render_template(
            "comparison.html",
            form=form,
            all_products=all_products,
            comparison=comparison_matrix,
        )

    @app.get("/wishlist")
    def wishlist_view():
        services = get_services()
        cart_service: CartService = services["cart_service"]

        saved_products = cart_service.get_wishlist_products(session)
        return render_template(
            "wishlist.html",
            saved_products=saved_products,
        )

    @app.post("/wishlist/toggle/<int:product_id>")
    def wishlist_toggle(product_id: int):
        services = get_services()
        cart_service: CartService = services["cart_service"]
        product_service: ProductService = services["product_service"]

        product = product_service.get_product_by_id(product_id, include_inactive=False)
        saved = cart_service.toggle_wishlist(session, product.id)
        if saved:
            flash(f"Saved '{product.name}' to your wishlist.", "success")
        else:
            flash(f"Removed '{product.name}' from your wishlist.", "info")

        next_url = get_safe_redirect_url(
            request.form.get("next") or request.referrer,
            fallback_endpoint="wishlist_view",
        )
        return redirect(next_url)

    @app.post("/wishlist/remove/<int:product_id>")
    def wishlist_remove(product_id: int):
        services = get_services()
        cart_service: CartService = services["cart_service"]

        removed = cart_service.remove_from_wishlist(session, product_id)
        if removed:
            flash("Item removed from your wishlist.", "info")

        next_url = get_safe_redirect_url(
            request.form.get("next") or request.referrer,
            fallback_endpoint="wishlist_view",
        )
        return redirect(next_url)

    @app.post("/wishlist/move-to-cart/<int:product_id>")
    def wishlist_move_to_cart(product_id: int):
        services = get_services()
        cart_service: CartService = services["cart_service"]
        product_service: ProductService = services["product_service"]

        product = product_service.get_product_by_id(product_id, include_inactive=False)
        try:
            cart_service.move_wishlist_to_cart(session, product.id)
            flash(f"Moved '{product.name}' from your wishlist to your cart.", "success")
        except SetuvoError as exc:
            flash(exc.message, "error")

        return redirect(url_for("wishlist_view"))


def _register_setup_and_bundle_routes(app: Flask) -> None:
    """Registers the Curated Workstation Setup Builder and Preconfigured Bundles routes."""

    @app.route("/setup-builder", methods=["GET", "POST"])
    def setup_builder():
        services = get_services()
        product_service: ProductService = services["product_service"]
        setup_service: SetupService = services["setup_service"]

        all_products = product_service.search_and_filter_products(
            include_inactive=False
        )
        purpose_options = setup_service.get_purpose_options()

        if request.method == "POST":
            purpose = setup_service.normalize_purpose(request.form.get("purpose"))
            default_budget = float(Config.SETUP_PURPOSES[purpose]["default_budget"])
            raw_budget = request.form.get("budget")
            try:
                budget_val = float(raw_budget) if raw_budget else default_budget
            except ValueError:
                budget_val = default_budget

            selected_ids: List[int] = []
            for raw_id in request.form.getlist("product_ids"):
                try:
                    pid = int(raw_id)
                    if pid > 0 and pid not in selected_ids:
                        selected_ids.append(pid)
                except ValueError:
                    continue

            form = SetupBuilderForm(
                formdata=MultiDict(
                    {
                        "purpose": purpose,
                        "budget": str(budget_val),
                    }
                )
            )
            form.populate_product_choices(all_products)
            form.product_ids.data = selected_ids
        else:
            purpose = setup_service.normalize_purpose(request.args.get("purpose"))
            default_budget = float(Config.SETUP_PURPOSES[purpose]["default_budget"])
            raw_budget = request.args.get("budget")
            try:
                budget_val = float(raw_budget) if raw_budget else default_budget
            except ValueError:
                budget_val = default_budget

            selected_ids = []
            for part in str(request.args.get("selected", "")).split(","):
                try:
                    pid = int(part.strip())
                    if pid > 0 and pid not in selected_ids:
                        selected_ids.append(pid)
                except ValueError:
                    continue

            form = SetupBuilderForm(
                data={
                    "purpose": purpose,
                    "budget": budget_val,
                    "product_ids": selected_ids,
                }
            )
            form.populate_product_choices(all_products)

        recommendations = setup_service.get_recommended_products(purpose)
        try:
            evaluation = setup_service.evaluate_setup(
                purpose=purpose,
                budget=budget_val,
                selected_ids=selected_ids,
            )
        except SetuvoError as exc:
            flash(exc.message, "error")
            evaluation = setup_service.evaluate_setup(
                purpose=purpose,
                budget=float(Config.SETUP_PURPOSES[purpose]["default_budget"]),
                selected_ids=selected_ids,
            )

        return render_template(
            "setup_builder.html",
            form=form,
            purpose_options=purpose_options,
            recommendations=recommendations,
            evaluation=evaluation,
        )

    @app.post("/setup-builder/add-to-cart")
    def setup_builder_add_to_cart():
        services = get_services()
        cart_service: CartService = services["cart_service"]
        setup_service: SetupService = services["setup_service"]

        purpose = setup_service.normalize_purpose(request.form.get("purpose"))
        raw_budget = request.form.get("budget")
        try:
            budget_val = float(raw_budget) if raw_budget else None
        except ValueError:
            budget_val = None

        selected_ids: List[int] = []
        for raw_id in request.form.getlist("product_ids"):
            try:
                pid = int(raw_id)
                if pid > 0 and pid not in selected_ids:
                    selected_ids.append(pid)
            except ValueError:
                continue

        if not selected_ids:
            flash("Select at least one product in the Setup Builder first.", "error")
            return redirect(url_for("setup_builder", purpose=purpose))

        evaluation = setup_service.evaluate_setup(
            purpose=purpose,
            budget=budget_val,
            selected_ids=selected_ids,
        )
        purchasable_ids: List[int] = evaluation["purchasable_ids"]
        if not purchasable_ids:
            flash(
                "None of the selected setup items are currently in stock.",
                "error",
            )
            return redirect(url_for("setup_builder", purpose=purpose))

        try:
            cart_service.add_multiple_items(session, purchasable_ids, quantity_each=1)
            if evaluation["unavailable_items"]:
                skipped_names = ", ".join(
                    item["name"] for item in evaluation["unavailable_items"]
                )
                flash(
                    f"Added {len(purchasable_ids)} in-stock setup item(s) to your cart. "
                    f"Skipped out-of-stock item(s): {skipped_names}.",
                    "info",
                )
            else:
                flash(
                    f"Added your custom {evaluation['purpose_label']} setup "
                    f"({len(purchasable_ids)} items) to your cart!",
                    "success",
                )
        except SetuvoError as exc:
            flash(exc.message, "error")
            return redirect(url_for("setup_builder", purpose=purpose))

        return redirect(url_for("cart_view"))

    @app.get("/bundles")
    def bundles_page():
        services = get_services()
        setup_service: SetupService = services["setup_service"]

        bundles = setup_service.get_all_bundles(include_inactive=False)
        return render_template(
            "bundles.html",
            bundles=bundles,
        )

    @app.post("/bundles/<slug>/add-to-cart")
    def bundle_add_to_cart(slug: str):
        services = get_services()
        setup_service: SetupService = services["setup_service"]
        cart_service: CartService = services["cart_service"]

        raw_kept = request.form.getlist("product_ids")
        kept_ids: Optional[List[int]] = None
        if raw_kept:
            kept_ids = []
            for raw_id in raw_kept:
                try:
                    pid = int(raw_id)
                    if pid > 0 and pid not in kept_ids:
                        kept_ids.append(pid)
                except ValueError:
                    continue

        try:
            preview = setup_service.preview_customized_bundle(
                bundle_slug=slug,
                kept_product_ids=kept_ids,
            )
            if not preview["is_available"]:
                unavailable = ", ".join(preview["unavailable_names"])
                flash(
                    f"Cannot add bundle because the following item(s) lack stock: {unavailable}. "
                    "Uncheck out-of-stock items to customize your kit.",
                    "error",
                )
                return redirect(url_for("bundles_page"))

            cart_service.add_multiple_items(
                session,
                preview["selected_product_ids"],
                quantity_each=1,
            )
            flash(
                f"Added '{preview['bundle']['name']}' ({len(preview['selected_product_ids'])} items) to your cart!",
                "success",
            )
        except SetuvoError as exc:
            flash(exc.message, "error")
            return redirect(url_for("bundles_page"))

        return redirect(url_for("cart_view"))


def _register_checkout_and_order_routes(app: Flask) -> None:
    """Registers Shopping Cart, Guest Checkout, Order Confirmation, and Order Tracking routes."""

    @app.get("/cart")
    def cart_view():
        services = get_services()
        cart_service: CartService = services["cart_service"]

        cart_summary = cart_service.get_cart_summary(session)
        for notice in cart_summary["adjustment_notices"]:
            flash(notice, "info")

        zone_options = cart_service.get_delivery_zone_options()
        return render_template(
            "cart.html",
            cart=cart_summary,
            zone_options=zone_options,
        )

    @app.post("/cart/add")
    def cart_add():
        services = get_services()
        cart_service: CartService = services["cart_service"]
        product_service: ProductService = services["product_service"]

        try:
            product_id = int(request.form.get("product_id", 0))
            quantity = int(request.form.get("quantity", 1))
        except ValueError:
            flash("Invalid product or quantity submitted.", "error")
            return redirect(url_for("catalogue"))

        product = product_service.get_product_by_id(product_id, include_inactive=False)
        try:
            cart_service.add_item(session, product.id, quantity=quantity)
            flash(f"Added {quantity} × '{product.name}' to your cart.", "success")
        except SetuvoError as exc:
            flash(exc.message, "error")

        next_url = get_safe_redirect_url(
            request.form.get("next") or request.referrer,
            fallback_endpoint="cart_view",
        )
        return redirect(next_url)

    @app.post("/cart/update/<int:product_id>")
    def cart_update(product_id: int):
        services = get_services()
        cart_service: CartService = services["cart_service"]

        try:
            quantity = int(request.form.get("quantity", 1))
            cart_service.update_item_quantity(session, product_id, quantity)
            if quantity <= 0:
                flash("Item removed from your cart.", "info")
            else:
                flash("Shopping cart quantity updated.", "success")
        except ValueError:
            flash("Please enter a valid whole number for quantity.", "error")
        except SetuvoError as exc:
            flash(exc.message, "error")

        return redirect(url_for("cart_view"))

    @app.post("/cart/remove/<int:product_id>")
    def cart_remove(product_id: int):
        services = get_services()
        cart_service: CartService = services["cart_service"]

        if cart_service.remove_item(session, product_id):
            flash("Item removed from your shopping cart.", "info")
        return redirect(url_for("cart_view"))

    @app.post("/cart/zone")
    def cart_set_zone():
        services = get_services()
        cart_service: CartService = services["cart_service"]

        zone = request.form.get("delivery_zone", "")
        try:
            cart_service.set_delivery_zone(session, zone)
            flash("Updated delivery zone and shipping fee.", "success")
        except SetuvoError as exc:
            flash(exc.message, "error")

        next_url = get_safe_redirect_url(
            request.form.get("next") or request.referrer,
            fallback_endpoint="cart_view",
        )
        return redirect(next_url)

    @app.route("/checkout", methods=["GET", "POST"])
    def checkout():
        services = get_services()
        cart_service: CartService = services["cart_service"]
        order_service: OrderService = services["order_service"]

        cart_summary = cart_service.get_cart_summary(session)
        if cart_summary["is_empty"]:
            flash("Your cart is empty. Add items before checking out.", "info")
            return redirect(url_for("catalogue"))

        if request.method == "POST":
            form = GuestCheckoutForm(formdata=request.form)
            selected_zone = cart_service.normalize_delivery_zone(
                form.delivery_zone.data
            )
            cart_summary = cart_service.get_cart_summary(
                session, delivery_zone=selected_zone
            )

            if form.validate():
                try:
                    result = order_service.place_guest_order(
                        session_store=session,
                        full_name=form.full_name.data or "",
                        email=form.email.data or "",
                        phone=form.phone.data or "",
                        address=form.address.data or "",
                        delivery_zone=form.delivery_zone.data or selected_zone,
                        notes=form.notes.data or "",
                        payment_method=form.payment_method.data
                        or "Pay on Delivery (Demo)",
                    )
                    order = result["order"]
                    email_res = result["email_result"]

                    if email_res.get("error"):
                        flash(
                            f"Order {order.order_number} placed! Confirmation email could not be sent right now, "
                            "but your order is saved and trackable.",
                            "info",
                        )
                    else:
                        flash(
                            f"Order {order.order_number} confirmed! Save your order number for tracking.",
                            "success",
                        )

                    return redirect(
                        url_for(
                            "order_confirmation", order_number=order.order_number
                        )
                    )
                except EmptyCartError as exc:
                    flash(exc.message, "info")
                    return redirect(url_for("catalogue"))
                except SetuvoError as exc:
                    flash(exc.message, "error")
        else:
            active_zone = cart_service.get_delivery_zone(session)
            form = GuestCheckoutForm(data={"delivery_zone": active_zone})

        zone_options = cart_service.get_delivery_zone_options()
        return render_template(
            "checkout.html",
            form=form,
            cart=cart_summary,
            zone_options=zone_options,
        )

    @app.get("/order-confirmation/<order_number>")
    def order_confirmation(order_number: str):
        services = get_services()
        order_service: OrderService = services["order_service"]

        order = order_service.get_order_by_number(order_number)
        return render_template(
            "order_confirmation.html",
            order=order,
        )

    @app.get("/order-confirmation/<order_number>/download")
    def download_order_receipt(order_number: str):
        services = get_services()
        order_service: OrderService = services["order_service"]
        receipt_service: ReceiptService = services["receipt_service"]

        order = order_service.get_order_by_number(order_number)
        png_buffer = receipt_service.generate_receipt_png(order)
        return send_file(
            png_buffer,
            mimetype="image/png",
            as_attachment=True,
            download_name=f"{order.order_number}_receipt.png",
        )

    @app.route("/track-order", methods=["GET", "POST"])
    def track_order():
        services = get_services()
        order_service: OrderService = services["order_service"]

        tracked_order = None
        if request.method == "POST":
            form = OrderTrackingForm(formdata=request.form)
            if form.validate():
                try:
                    tracked_order = order_service.track_order(
                        order_number=form.normalized_order_number,
                        email=form.normalized_email,
                    )
                except SetuvoError as exc:
                    flash(exc.message, "error")
        else:
            prefill_number = str(request.args.get("order_number", "")).strip()
            prefill_email = str(request.args.get("email", "")).strip()
            if prefill_number or prefill_email:
                form = OrderTrackingForm(
                    formdata=MultiDict(
                        {
                            "order_number": prefill_number,
                            "email": prefill_email,
                        }
                    )
                )
                if form.validate():
                    try:
                        tracked_order = order_service.track_order(
                            order_number=form.normalized_order_number,
                            email=form.normalized_email,
                        )
                    except SetuvoError as exc:
                        flash(exc.message, "error")
            else:
                form = OrderTrackingForm()

        return render_template(
            "order_tracking.html",
            form=form,
            order=tracked_order,
        )


def _register_analytics_routes(app: Flask) -> None:
    """Registers local Pandas business analytics dashboard and CSV export downloads."""

    @app.get("/analytics")
    def analytics_dashboard():
        services = get_services()
        analytics_service: AnalyticsService = services["analytics_service"]

        summary = analytics_service.get_sales_summary()
        charts = analytics_service.build_plotly_charts(summary)
        return render_template(
            "analytics.html",
            summary=summary,
            charts=charts,
        )

    @app.get("/analytics/export/<report_type>")
    def analytics_export_csv(report_type: str):
        services = get_services()
        analytics_service: AnalyticsService = services["analytics_service"]

        clean_type = str(report_type or "").strip().lower()
        if clean_type == "sales":
            export_data = analytics_service.export_sales_report_csv()
        elif clean_type == "inventory":
            export_data = analytics_service.export_inventory_report_csv()
        else:
            flash("Unknown report type requested. Choose sales or inventory.", "error")
            return redirect(url_for("analytics_dashboard"))

        return Response(
            export_data["csv_content"],
            mimetype="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{export_data["filename"]}"'
            },
        )


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """Application factory creating and wiring a configured Setuvo Flask instance."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    Config.ensure_directories()
    csrf.init_app(app)

    db_path = app.config.get("DATABASE_PATH", Config.DATABASE_PATH)
    exports_dir = app.config.get("EXPORTS_DIR", Config.EXPORTS_DIR)

    db_manager = DatabaseManager(db_path=db_path)
    if app.config.get("AUTO_INIT_DB", True):
        db_manager.init_db()
        existing = db_manager.fetch_one("SELECT COUNT(*) AS cnt FROM categories;")
        if existing is None or int(existing["cnt"]) == 0:
            seed_database(
                db_manager,
                include_sample_orders=bool(app.config.get("SEED_SAMPLE_ORDERS", False)),
            )
        else:
            with db_manager.transaction() as conn:
                for prod in SEED_PRODUCTS:
                    target_url = prod.get("image_url") or resolve_product_image_url(
                        prod["sku"]
                    )
                    conn.execute(
                        "UPDATE products SET image_url = ? WHERE sku = ?;",
                        (target_url, prod["sku"]),
                    )

    product_service = ProductService(db_manager)
    setup_service = SetupService(db_manager, product_service)
    cart_service = CartService(db_manager, product_service)
    inventory_service = InventoryService(db_manager)
    email_service = EmailService(
        mail_enabled=app.config.get("MAIL_ENABLED", Config.MAIL_ENABLED),
        mail_server=app.config.get("MAIL_SERVER", Config.MAIL_SERVER),
        mail_port=app.config.get("MAIL_PORT", Config.MAIL_PORT),
        mail_use_tls=app.config.get("MAIL_USE_TLS", Config.MAIL_USE_TLS),
        mail_username=app.config.get("MAIL_USERNAME", Config.MAIL_USERNAME),
        mail_password=app.config.get("MAIL_PASSWORD", Config.MAIL_PASSWORD),
        default_sender=app.config.get("MAIL_DEFAULT_SENDER", Config.MAIL_DEFAULT_SENDER),
        admin_email=app.config.get(
            "ADMIN_NOTIFICATION_EMAIL", Config.ADMIN_NOTIFICATION_EMAIL
        ),
    )
    order_service = OrderService(
        db_manager=db_manager,
        cart_service=cart_service,
        inventory_service=inventory_service,
        email_service=email_service,
    )
    receipt_service = ReceiptService()
    analytics_service = AnalyticsService(
        db_manager=db_manager,
        exports_dir=exports_dir,
    )

    app.extensions["services"] = {
        "db_manager": db_manager,
        "product_service": product_service,
        "setup_service": setup_service,
        "cart_service": cart_service,
        "inventory_service": inventory_service,
        "email_service": email_service,
        "order_service": order_service,
        "receipt_service": receipt_service,
        "analytics_service": analytics_service,
    }

    _register_template_helpers(app)
    _register_error_handlers(app)
    _register_core_routes(app)
    _register_catalog_routes(app)
    _register_setup_and_bundle_routes(app)
    _register_checkout_and_order_routes(app)
    _register_analytics_routes(app)

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="127.0.0.1", port=5000, debug=Config.DEBUG)