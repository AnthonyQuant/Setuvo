# Setuvo — Curated Workstation & Study Gear Storefront

**Setuvo** is a full-stack Python e-commerce web application built with **Flask**, **SQLite**, **Pandas**, and **Plotly**, designed specifically for Nigerian students, software developers, and digital creators. All catalogue pricing, budget planning, shipping zones, and revenue analytics operate natively in **Nigerian Naira (`₦` / NGN)**.

---

## Core Capabilities

- **Structured Hardware Catalogue (`/catalogue`):** Multi-criteria filtering by keyword/SKU, category, brand, product type, Naira price range, stock availability, and 6 sorting modes.
- **Interactive Workstation Setup Builder (`/setup-builder`):** Purpose-driven hardware recommender (*Studying & Note-Taking*, *Software Engineering & Coding*, *Content Creation & Streaming*, *General Productivity & Home Office*) with real-time Naira budget utilization tracking and over-budget alerts.
- **Preconfigured Workstation Kits (`/bundles`):** Discounted multi-item bundles (*Student Essentials Kit*, *Programming Starter Kit*, *Home Office Kit*, *Content Creator Kit*) with component customization before adding to cart.
- **Side-by-Side Specification Comparison (`/compare`):** Compare 2 to 3 workstation products across pricing, stock, workflows, and technical specs with automatic difference highlighting.
- **Session Cart, Wishlist & Nigerian Delivery Zones (`/cart`, `/wishlist`):** Stock-clamped cart management and zone-based Nigerian shipping calculation (*Benin City Pickup*, *Edo State Local*, *Lagos Metro*, *Abuja FCT*, and *Nationwide Express*).
- **Atomic Guest Checkout & Self-Service Order Tracking (`/checkout`, `/track-order`):** Transactional SQLite stock deduction, historical `unit_price` snapshots, collision-free `STV-YYYYMMDD-XXXX` order references, automatic restocking on cancellation, and 4-stage visual order tracking.
- **Pandas & Plotly Operations Analytics (`/analytics`):** Live KPI cards, 5 interactive Plotly charts (monthly revenue, category sales, top products, order statuses, and stock levels), low-stock replenishment alerts, and one-click Sales & Inventory CSV report exports.

---

## Project Architecture

```text
Setuvo/
├── app.py                     # Flask app factory, CSRF, Jinja filters & route controllers
├── config.py                  # Naira currency, Nigerian delivery zones & runtime settings
├── requirements.txt           # Pinned Python dependencies
├── database/
│   ├── db_manager.py          # SQLite WAL connection manager, schema & atomic transactions
│   └── seed_data.py           # Idempotent seeder (7 categories, 20 products, 4 bundles, sample orders)
├── models/
│   └── entities.py            # Typed dataclasses (Product, Bundle, CartItem, Order, OrderItem)
├── services/
│   ├── product_service.py     # Catalogue search, filtering, sorting & comparison matrix
│   ├── setup_service.py       # Purpose-based Setup Builder & bundle discount engine
│   ├── cart_service.py        # Session cart, stock clamping, delivery zones & wishlist
│   ├── inventory_service.py   # Transactional stock deduction, restocking & stock alerts
│   ├── order_service.py       # Atomic guest checkout, lifecycle updates & order lookup
│   ├── email_service.py       # Safe optional SMTP order confirmation notifications
│   ├── analytics_service.py   # Pandas aggregations, 5 Plotly figures & CSV exports
│   └── exceptions.py          # Typed domain & HTTP exceptions
├── forms/
│   ├── search_form.py         # WTForms search, comparison & setup builder forms
│   └── checkout_form.py       # WTForms guest checkout & order tracking forms
├── templates/                 # 12 responsive Jinja2 templates extending base.html
├── static/
│   ├── css/style.css          # Responsive design system & print receipt rules
│   ├── js/setuvo.js           # Client-side budget tracker, quick-compare & shipping preview
│   └── images/products/       # Local SVG product illustrations
└── tests/
    └── test_setuvo.py         # End-to-end pytest integration & unit test suite

## Local Setup & Running the App

1. **Activate your virtual environment inside `Setuvo/`:**

```bash
source .venv/Scripts/activate
```

2. **Install dependencies (if not already installed):**

```bash
pip install -r requirements.txt
```

3. **Run the automated `pytest` test suite:**

```bash
pytest -v
```

4. **Launch the Setuvo web server:**

```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser to explore the storefront, build a workstation setup, place a guest order, track its status, and inspect the Pandas/Plotly analytics dashboard.

---

### 3. Run the Full `pytest` Suite & Launch Setuvo Live!
Run **`pytest -v`** in your PyCharm Git Bash terminal inside **`Setuvo/`**:

```bash
pytest -v
```

Expected output:

* `9 passed` across all end-to-end storefront, checkout, inventory, tracking, and analytics tests.

Once `pytest -v` passes, start your live server:

```bash
python app.py
```