"""database/seed_data.py

Idempotent seed data for Setuvo: curated Naira-priced student, developer,
and creator workstation products across 7 categories plus 4 preconfigured
workstation bundles.
"""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Dict, List

from database.db_manager import DatabaseManager

PRODUCTS_IMAGE_DIR = (
    Path(__file__).resolve().parent.parent / "static" / "images" / "products"
)
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".svg")


def resolve_product_image_url(sku: str) -> str:
    """Finds a matching local image file in static/images/products/ if no external URL is set."""
    stem = sku.strip().lower()
    for ext in IMAGE_EXTENSIONS:
        candidate = PRODUCTS_IMAGE_DIR / f"{stem}{ext}"
        if candidate.is_file():
            return f"/static/images/products/{stem}{ext}"
    return "/static/images/product_placeholder.svg"


CATEGORIES: List[Dict[str, Any]] = [
    {
        "slug": "laptop-stands-cooling",
        "name": "Laptop Stands & Cooling",
        "description": "Ergonomic aluminum risers, foldable travel stands, and quiet multi-fan cooling pads.",
        "display_order": 1,
    },
    {
        "slug": "keyboards-mice",
        "name": "Keyboards & Mice",
        "description": "Compact mechanical keyboards, silent wireless combos, and ergonomic precision mice.",
        "display_order": 2,
    },
    {
        "slug": "headphones-audio",
        "name": "Headphones & Audio",
        "description": "Active noise-cancelling headphones, studio monitor headsets, and USB condenser microphones.",
        "display_order": 3,
    },
    {
        "slug": "storage-connectivity",
        "name": "Storage & Connectivity",
        "description": "High-speed portable NVMe SSDs, multi-port USB-C hubs, and braided GaN charging cables.",
        "display_order": 4,
    },
    {
        "slug": "study-productivity",
        "name": "Study & Productivity",
        "description": "Digital desk timers, blue-light eyewear, hardcover dot-grid notebooks, and tablet styluses.",
        "display_order": 5,
    },
    {
        "slug": "desk-essentials",
        "name": "Desk & Workstation Essentials",
        "description": "Asymmetric monitor light bars, extended desk mats, and under-desk cable management trays.",
        "display_order": 6,
    },
    {
        "slug": "computer-accessories",
        "name": "Computer Accessories",
        "description": "1080p auto-focus webcams, surge-protected power strips, and laptop sleeves.",
        "display_order": 7,
    },
]

PRODUCTS: List[Dict[str, Any]] = [
    # --- 1. Laptop Stands & Cooling ---
    {
        "category_slug": "laptop-stands-cooling",
        "sku": "STV-LS-001",
        "name": "Nexstand K2 Foldable Ergonomic Laptop Riser",
        "brand": "Nexstand",
        "subcategory": "Portable Stands",
        "description": "Lightweight nylon-composite folding stand with 8 height levels for lecture halls, libraries, and remote desks.",
        "specifications": {
            "Material": "Reinforced Nylon & Fiberglass",
            "Height Levels": "8 Adjustable Angles (14cm–32cm)",
            "Compatibility": "11-inch to 17.3-inch Laptops",
            "Weight": "234 g",
            "Portability": "Folds flat with nylon sleeve",
        },
        "use_cases": "studying,programming,general_productivity",
        "price": 24500.0,
        "stock": 18,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQdSIxm1jKH6qE1rW0JdvDZD5shC4aLaq1Frzs2hp4z8-iQlrdburQx3ns&s=10",
        "is_featured": 1,
        "is_bestseller": 1,
    },
    {
        "category_slug": "laptop-stands-cooling",
        "sku": "STV-LS-002",
        "name": "UGREEN Unibody Aluminum Ventilated Laptop Stand",
        "brand": "UGREEN",
        "subcategory": "Desktop Stands",
        "description": "CNC-machined anodized aluminum riser with open thermal airflow channels and non-slip silicone pads.",
        "specifications": {
            "Material": "Anodized Aluminum Alloy",
            "Height Levels": "Fixed 15° Ergonomic Tilt",
            "Compatibility": "Up to 16-inch Laptops (Max 5 kg)",
            "Weight": "680 g",
            "Portability": "Desktop stationary",
        },
        "use_cases": "programming,content_creation,general_productivity",
        "price": 38000.0,
        "stock": 12,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRNbCaE5yt5q81mneTrSN-PdLDIAbBJ_BAKN8r0KMVe2g&s=10",
        "is_featured": 1,
        "is_bestseller": 0,
    },
    {
        "category_slug": "laptop-stands-cooling",
        "sku": "STV-LS-003",
        "name": "IETS GT300 Dual-Blower Filtered Cooling Pad",
        "brand": "IETS",
        "subcategory": "Cooling Pads",
        "description": "High-static-pressure sealed foam cooling pad with washable dust filters for sustained compiles and rendering.",
        "specifications": {
            "Cooling System": "Dual 4500 RPM Centrifugal Blowers",
            "Noise Level": "28–42 dBA (3 Speed Modes)",
            "Compatibility": "14-inch to 17.3-inch Laptops",
            "Power Input": "USB-A Pass-Through (5V)",
            "Dust Protection": "Removable Dual Mesh Filters",
        },
        "use_cases": "programming,content_creation",
        "price": 54000.0,
        "stock": 4,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQvVBY0Yne_AP8yNbRr8xMLKFjjUD-PjQlSTsQptjkkSg&s=10",
        "is_featured": 0,
        "is_bestseller": 1,
    },
    # --- 2. Keyboards & Mice ---
    {
        "category_slug": "keyboards-mice",
        "sku": "STV-KM-001",
        "name": "Keychron K2 V2 75% Wireless Mechanical Keyboard",
        "brand": "Keychron",
        "subcategory": "Mechanical Keyboards",
        "description": "Compact 84-key tactile brown switch mechanical keyboard with multi-device Bluetooth 5.1 and USB-C wired mode.",
        "specifications": {
            "Connection": "Bluetooth 5.1 & USB-C Wired",
            "Layout": "75% Compact (84 Keys)",
            "Switch Type": "Gateron G Pro Brown (Tactile)",
            "Battery Life": "Up to 72 hours (4000 mAh)",
            "Compatibility": "Windows, macOS & Linux",
        },
        "use_cases": "programming,content_creation,general_productivity",
        "price": 89000.0,
        "stock": 9,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRto815kph1sBggd7AN5TKuQKyhzDvhtWRNv2qPORLYxg&s=10",
        "is_featured": 1,
        "is_bestseller": 1,
    },
    {
        "category_slug": "keyboards-mice",
        "sku": "STV-KM-002",
        "name": "Logitech K380 Multi-Device Slim Bluetooth Keyboard",
        "brand": "Logitech",
        "subcategory": "Portable Keyboards",
        "description": "Ultra-quiet scooped scissor-switch keyboard that switches seamlessly between laptop, tablet, and phone.",
        "specifications": {
            "Connection": "Bluetooth 3.0 (3-Device Easy-Switch)",
            "Layout": "Compact Tenkeyless (79 Keys)",
            "Switch Type": "Low-Profile Scissor",
            "Battery Life": "24 Months (2x AAA Included)",
            "Compatibility": "Windows, macOS, iPadOS & Android",
        },
        "use_cases": "studying,general_productivity",
        "price": 42000.0,
        "stock": 15,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQwvi38t8ULzy08DvyY6_QpX3Bku69BH4Vou_8s6-55sA&s=10",
        "is_featured": 0,
        "is_bestseller": 1,
    },
    {
        "category_slug": "keyboards-mice",
        "sku": "STV-KM-003",
        "name": "Logitech MX Master 3S Performance Wireless Mouse",
        "brand": "Logitech",
        "subcategory": "Ergonomic Mice",
        "description": "8000 DPI track-on-glass sensor with MagSpeed electromagnetic scroll wheel and quiet-click switches.",
        "specifications": {
            "Connection": "Logi Bolt USB & Bluetooth Low Energy",
            "Sensor": "8000 DPI Darkfield Track-on-Glass",
            "Buttons": "7 Programmable Buttons + Thumb Wheel",
            "Battery Life": "Up to 70 Days (USB-C Quick Charge)",
            "Compatibility": "Windows, macOS & Linux",
        },
        "use_cases": "programming,content_creation,general_productivity",
        "price": 96000.0,
        "stock": 7,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS84EkNTNN6ywK2DgNDx5nvw6dE6W3mzTZAcNd6laf6yQ&s=10",
        "is_featured": 1,
        "is_bestseller": 1,
    },
    {
        "category_slug": "keyboards-mice",
        "sku": "STV-KM-004",
        "name": "UGREEN M571 Ergonomic Vertical Wireless Mouse",
        "brand": "UGREEN",
        "subcategory": "Ergonomic Mice",
        "description": "57-degree natural handshake vertical mouse designed to reduce wrist pronation during long study sessions.",
        "specifications": {
            "Connection": "2.4 GHz USB Receiver & Bluetooth 5.0",
            "Sensor": "4000 DPI Adjustable (4 Levels)",
            "Buttons": "6 Silent-Click Buttons",
            "Battery Life": "12 Months (1x AA Battery)",
            "Compatibility": "Windows, macOS & Linux",
        },
        "use_cases": "studying,programming,general_productivity",
        "price": 23000.0,
        "stock": 20,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQkT2SfvSa0Lt_HbP5h1r6McVc--lNS3IJ8gXBTgpyCGQ&s=10",
        "is_featured": 0,
        "is_bestseller": 0,
    },
    # --- 3. Headphones & Audio ---
    {
        "category_slug": "headphones-audio",
        "sku": "STV-HA-001",
        "name": "Soundcore Space One Active Noise Cancelling Headphones",
        "brand": "Anker Soundcore",
        "subcategory": "ANC Headphones",
        "description": "Adaptive noise-cancelling over-ear headphones blocking campus and generator background hum with 40-hour battery life.",
        "specifications": {
            "Connection": "Bluetooth 5.3 & 3.5mm AUX Wired",
            "Driver Size": "40mm Custom Dynamic Drivers (LDAC)",
            "Noise Cancellation": "Adaptive ANC (Up to 98% Voice Reduction)",
            "Battery Life": "40 Hours (ANC On) / 55 Hours (ANC Off)",
            "Microphone": "3-Mic AI Call Clarity",
        },
        "use_cases": "studying,programming,content_creation,general_productivity",
        "price": 78000.0,
        "stock": 11,
        "image_url": "https://www.cdcare.ng/_next/image?url=https%3A%2F%2Fcdn.cdcare.app%2Fproduct_images%2FcpmveT3MBDFiZjkjqmOp%2Fimage1&w=1600&q=75",
        "is_featured": 1,
        "is_bestseller": 1,
    },
    {
        "category_slug": "headphones-audio",
        "sku": "STV-HA-002",
        "name": "Audio-Technica ATH-M20x Closed-Back Monitor Headphones",
        "brand": "Audio-Technica",
        "subcategory": "Studio Monitors",
        "description": "Flat-response closed-back studio headphones engineered for accurate audio mixing, video editing, and focused listening.",
        "specifications": {
            "Connection": "Wired 3.0m Straight Cable (3.5mm + 6.3mm)",
            "Driver Size": "40mm Rare-Earth Magnet Drivers",
            "Noise Cancellation": "Passive Circumaural Isolation",
            "Battery Life": "Passive Wired (No Charging Needed)",
            "Microphone": "None (Pure Studio Monitoring)",
        },
        "use_cases": "content_creation,programming",
        "price": 68000.0,
        "stock": 6,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSk948qhBGXHZi6vOh-NtVgwI0gZMU3yLcscwinpbjjxg&s",
        "is_featured": 0,
        "is_bestseller": 0,
    },
    {
        "category_slug": "headphones-audio",
        "sku": "STV-HA-003",
        "name": "Maono PD100U Dynamic USB-C Podcast & Voiceover Mic",
        "brand": "Maono",
        "subcategory": "USB Microphones",
        "description": "Cardioid dynamic broadcast microphone with built-in gain knob and desktop stand for tutorials, calls, and voiceovers.",
        "specifications": {
            "Connection": "USB-C & USB-A Plug-and-Play",
            "Polar Pattern": "Cardioid Dynamic Capsule",
            "Sample Rate": "24-bit / 48 kHz",
            "Controls": "Hardware Mic Gain Dial",
            "Included Mount": "Weighted Metal Desktop Base",
        },
        "use_cases": "content_creation,general_productivity",
        "price": 56000.0,
        "stock": 3,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQWhcqDUVSuQAFWMSh26K-TA1ain82yrRXiCLDyb4Ss4A&s=10",
        "is_featured": 0,
        "is_bestseller": 0,
    },
    # --- 4. Storage & Connectivity ---
    {
        "category_slug": "storage-connectivity",
        "sku": "STV-SC-001",
        "name": "Samsung T7 Shield 1TB Rugged Portable NVMe SSD",
        "brand": "Samsung",
        "subcategory": "External SSDs",
        "description": "1,050 MB/s USB 3.2 Gen 2 solid-state drive with IP65 dust/water resistance for datasets, VMs, and 4K footage.",
        "specifications": {
            "Capacity": "1 TB NVMe Flash",
            "Interface": "USB 3.2 Gen 2 (10 Gbps Type-C)",
            "Read/Write Speed": "Up to 1,050 / 1,000 MB/s",
            "Durability": "IP65 Rated + 3m Drop Resistant",
            "Security": "AES 256-bit Hardware Encryption",
        },
        "use_cases": "programming,content_creation,studying",
        "price": 118000.0,
        "stock": 8,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR8ExUw3xvn1BIZM1Q9LEap8tR-Ipj_znK--tHT1Gveaw&s=10",
        "is_featured": 1,
        "is_bestseller": 1,
    },
    {
        "category_slug": "storage-connectivity",
        "sku": "STV-SC-002",
        "name": "UGREEN Revodok 7-in-1 USB-C Hub (4K HDMI + 100W PD)",
        "brand": "UGREEN",
        "subcategory": "USB-C Hubs",
        "description": "Aluminum multi-port docking adapter adding 4K@60Hz HDMI, Gigabit Ethernet, SD/TF readers, and 100W pass-through charging.",
        "specifications": {
            "Video Output": "1x HDMI (4K @ 60Hz)",
            "Data Ports": "2x USB-A 3.0 (5 Gbps) + SD/microSD",
            "Networking": "1x RJ45 Gigabit Ethernet",
            "Power Delivery": "100W USB-C PD Pass-Through",
            "Chassis": "Braided Cable + Aluminum Shell",
        },
        "use_cases": "programming,content_creation,studying,general_productivity",
        "price": 36500.0,
        "stock": 14,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQVUfree8eh8gHo9zWYMZ6zj0ZyDfNUXO1Vx_GrInmeKw&s=10",
        "is_featured": 1,
        "is_bestseller": 1,
    },
    {
        "category_slug": "storage-connectivity",
        "sku": "STV-SC-003",
        "name": "Anker 333 100W Braided USB-C to USB-C Cable (2-Pack, 6ft)",
        "brand": "Anker",
        "subcategory": "Cables & Adapters",
        "description": "E-Marker certified 100W fast-charging nylon braided cables built to withstand 12,000+ bends.",
        "specifications": {
            "Max Power": "100W (20V / 5A USB Power Delivery)",
            "Length": "1.8 m (6 ft) x 2 Cables",
            "Data Transfer": "480 Mbps USB 2.0",
            "Jacket": "Double-Braided Nylon",
            "Certification": "USB-IF & E-Marker Chip",
        },
        "use_cases": "studying,programming,content_creation,general_productivity",
        "price": 16500.0,
        "stock": 25,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSwW1V1SNvXRr5xLKs2TI4eU3jTB4tsZYsYXrA0EXFZUA&s",
        "is_featured": 0,
        "is_bestseller": 0,
    },
    # --- 5. Study & Productivity ---
    {
        "category_slug": "study-productivity",
        "sku": "STV-SP-001",
        "name": "Baseus Heyo Rotation Countdown Pomodoro Desk Timer",
        "brand": "Baseus",
        "subcategory": "Focus Timers",
        "description": "Magnetic rotary LED digital timer with silent flash mode for library Pomodoro study sprints and deep-work blocks.",
        "specifications": {
            "Display": "Large High-Contrast LED Digital",
            "Controls": "Stepless Rotary Bezel + Start/Stop",
            "Alert Modes": "Silent Blink / Low / High Chime",
            "Mounting": "Magnetic Back + Fold-Out Stand",
            "Power": "3x AAA Batteries",
        },
        "use_cases": "studying,programming,general_productivity",
        "price": 15000.0,
        "stock": 22,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS8mgKdTyEdwdJk9-LP2MiHEM-y3gJ9bLYkcGindG29AQ&s=10",
        "is_featured": 0,
        "is_bestseller": 1,
    },
    {
        "category_slug": "study-productivity",
        "sku": "STV-SP-002",
        "name": "Setuvo A5 Hardcover Dot-Grid Engineering Notebook (2-Pack)",
        "brand": "Setuvo Studio",
        "subcategory": "Notebooks",
        "description": "120gsm fountain-pen-friendly lay-flat thread-bound notebooks with numbered index pages for algorithms and system sketches.",
        "specifications": {
            "Paper Weight": "120 gsm Acid-Free Ivory Paper",
            "Page Count": "192 Numbered Pages per Book",
            "Ruling": "5mm Subtle Dot-Grid",
            "Binding": "180° Lay-Flat Smyth-Sewn Hardcover",
            "Extras": "Dual Ribbon Bookmarks + Back Pocket",
        },
        "use_cases": "studying,programming,content_creation",
        "price": 14000.0,
        "stock": 30,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSth9pVBqwokCUz_PwIm6AUynlMp74639TQQrOiHa_U4A&s=10",
        "is_featured": 0,
        "is_bestseller": 0,
    },
    {
        "category_slug": "study-productivity",
        "sku": "STV-SP-003",
        "name": "Gunnar Intercept Anti-Blue-Light Computer Eyewear",
        "brand": "Gunnar",
        "subcategory": "Eye Protection",
        "description": "Patented amber-tint focus lenses filtering 65% of high-energy blue light to reduce eye strain during night coding.",
        "specifications": {
            "Blue Light Filter": "65% @ 450nm Peak Spectrum",
            "Lens Coating": "Anti-Reflective & Oleophobic",
            "Frame Material": "Lightweight Polymer (28 g)",
            "Focus Magnification": "+0.20 Diopter Relief",
            "Includes": "Microfiber Pouch & Cleaning Cloth",
        },
        "use_cases": "studying,programming,content_creation,general_productivity",
        "price": 32000.0,
        "stock": 0,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRR2bg87OLS-QTx50lUaGP-LEy0sJuoSWsUAXsQFqopGw&s",
        "is_featured": 0,
        "is_bestseller": 0,
    },
    # --- 6. Desk & Workstation Essentials ---
    {
        "category_slug": "desk-essentials",
        "sku": "STV-DE-001",
        "name": "Baseus i-wok Asymmetric ScreenBar Monitor Light",
        "brand": "Baseus",
        "subcategory": "Desk Lighting",
        "description": "Zero-glare asymmetric optical monitor lamp illuminating your desk surface without screen reflections (2900K–6500K).",
        "specifications": {
            "Optical Design": "45° Asymmetric Anti-Glare Cut-Off",
            "Color Temperature": "2900K Warm to 6500K Daylight",
            "Color Rendering": "CRI Ra > 95",
            "Power Supply": "USB-C Powered (5W)",
            "Compatibility": "Monitors & Laptops (5mm–40mm Bezel)",
        },
        "use_cases": "studying,programming,content_creation,general_productivity",
        "price": 34000.0,
        "stock": 10,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRHRoK7PM55OQNyk-R5WN2PE7MqT9vLfxkgta1mdMlBqQ&s",
        "is_featured": 1,
        "is_bestseller": 1,
    },
    {
        "category_slug": "desk-essentials",
        "sku": "STV-DE-002",
        "name": "Setuvo Studio Extended Vegan-Leather Desk Mat (90x40 cm)",
        "brand": "Setuvo Studio",
        "subcategory": "Desk Mats",
        "description": "Water-resistant micro-textured desk pad cushioning wrists and stabilizing full-size keyboards and mice.",
        "specifications": {
            "Dimensions": "900 mm x 400 mm x 3 mm",
            "Top Surface": "Smooth Micro-Pebble PU Leather",
            "Base Layer": "High-Grip Natural Suede Backing",
            "Edge Finish": "Reinforced Double-Stitched Seam",
            "Water Resistance": "Spill-Proof Wipe-Clean Coating",
        },
        "use_cases": "programming,content_creation,general_productivity",
        "price": 19500.0,
        "stock": 19,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ4BMbBFkY0__q6QKvx3nfo2DYaPwNGiKTOdwdJWj13BA&s=10",
        "is_featured": 0,
        "is_bestseller": 1,
    },
    # --- 7. Computer Accessories ---
    {
        "category_slug": "computer-accessories",
        "sku": "STV-CA-001",
        "name": "Logitech C920e Full HD 1080p Auto-Focus Webcam",
        "brand": "Logitech",
        "subcategory": "Webcams",
        "description": "Crisp 1080p/30fps glass lens webcam with automatic low-light correction, dual omni mics, and attachable privacy shutter.",
        "specifications": {
            "Resolution": "1080p @ 30fps / 720p @ 60fps",
            "Field of View": "78° Diagonal Fixed Frame",
            "Focus & Light": "Auto-Focus + RightLight 2 Correction",
            "Privacy": "Flip-Down Lens Privacy Cover",
            "Mount": "Universal Monitor Clip + 1/4\" Tripod Thread",
        },
        "use_cases": "content_creation,general_productivity,studying",
        "price": 64000.0,
        "stock": 5,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRj6Ebx-9VhJ7RhJjQzvwEokim29m4SQEOnbwIDwaq8tw&s=10",
        "is_featured": 1,
        "is_bestseller": 0,
    },
    {
        "category_slug": "computer-accessories",
        "sku": "STV-CA-002",
        "name": "Anker PowerExtend 6-Outlet 20W USB-C Surge Protector Strip",
        "brand": "Anker",
        "subcategory": "Power & Surge Protection",
        "description": "2000-Joule surge-protected extension strip with 6 AC outlets, 20W USB-C PD port, and overload circuit breaker.",
        "specifications": {
            "Surge Rating": "2,000 Joules + Overload Breaker",
            "AC Outlets": "6 Wide-Spaced Universal/UK Outlets",
            "USB Ports": "1x USB-C (20W PD) + 2x USB-A (12W)",
            "Cable Length": "2.0 m Heavy-Duty Cord",
            "Safety": "750°C Fire-Retardant Housing",
        },
        "use_cases": "studying,programming,content_creation,general_productivity",
        "price": 29000.0,
        "stock": 16,
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQP0_QnO-bnCYojRIjHOte_TA1b4eD1jJr7Hv7Brci3VA&s",
        "is_featured": 0,
        "is_bestseller": 1,
    },
]

BUNDLES: List[Dict[str, Any]] = [
    {
        "slug": "student-essentials-kit",
        "name": "Student Essentials Kit",
        "purpose": "studying",
        "description": "Everything needed for ergonomic library study sessions, distraction-free focus, and organized lecture notes.",
        "discount_pct": 12.0,
        "items": [
            ("STV-LS-001", 1),
            ("STV-KM-002", 1),
            ("STV-KM-004", 1),
            ("STV-SP-001", 1),
            ("STV-SP-002", 1),
        ],
    },
    {
        "slug": "programming-starter-kit",
        "name": "Programming Starter Kit",
        "purpose": "programming",
        "description": "Tactile mechanical typing, elevated screen ergonomics, multi-port connectivity, and clean desk lighting for long coding sprints.",
        "discount_pct": 15.0,
        "items": [
            ("STV-LS-002", 1),
            ("STV-KM-001", 1),
            ("STV-KM-003", 1),
            ("STV-SC-002", 1),
            ("STV-DE-001", 1),
        ],
    },
    {
        "slug": "home-office-kit",
        "name": "Home Office Kit",
        "purpose": "general_productivity",
        "description": "A balanced daily workstation setup combining quiet peripherals, surge-safe power, and a clean extended desk surface.",
        "discount_pct": 10.0,
        "items": [
            ("STV-LS-001", 1),
            ("STV-KM-002", 1),
            ("STV-KM-004", 1),
            ("STV-DE-002", 1),
            ("STV-CA-002", 1),
        ],
    },
    {
        "slug": "content-creator-kit",
        "name": "Content Creator Kit",
        "purpose": "content_creation",
        "description": "Studio-grade monitoring headphones, dynamic USB-C voiceover microphone, high-speed 1TB NVMe storage, and 1080p webcam.",
        "discount_pct": 14.0,
        "items": [
            ("STV-HA-002", 1),
            ("STV-HA-003", 1),
            ("STV-SC-001", 1),
            ("STV-CA-001", 1),
            ("STV-DE-001", 1),
        ],
    },
]


def seed_database(
    db_manager: DatabaseManager,
    include_sample_orders: bool = False,
) -> Dict[str, int]:
    """Initializes schema and idempotently populates categories, products, and bundles."""
    db_manager.init_db()

    with db_manager.transaction() as conn:
        for cat in CATEGORIES:
            conn.execute(
                """
                INSERT OR IGNORE INTO categories (slug, name, description, display_order)
                VALUES (?, ?, ?, ?);
                """,
                (cat["slug"], cat["name"], cat["description"], cat["display_order"]),
            )

        category_rows = conn.execute("SELECT id, slug FROM categories;").fetchall()
        category_map = {row["slug"]: int(row["id"]) for row in category_rows}

        for prod in PRODUCTS:
            cat_id = category_map[prod["category_slug"]]
            specs_json = json.dumps(prod["specifications"], ensure_ascii=False)
            image_url = prod.get("image_url") or resolve_product_image_url(prod["sku"])
            conn.execute(
                """
                INSERT OR IGNORE INTO products (
                    category_id, sku, name, brand, subcategory, description,
                    specifications_json, use_cases, price, stock, image_url,
                    is_featured, is_bestseller, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
                """,
                (
                    cat_id,
                    prod["sku"],
                    prod["name"],
                    prod["brand"],
                    prod["subcategory"],
                    prod["description"],
                    specs_json,
                    prod["use_cases"],
                    float(prod["price"]),
                    int(prod["stock"]),
                    image_url,
                    int(prod["is_featured"]),
                    int(prod["is_bestseller"]),
                ),
            )
            conn.execute(
                """
                UPDATE products
                SET image_url = ?
                WHERE sku = ?;
                """,
                (image_url, prod["sku"]),
            )

        product_rows = conn.execute(
            "SELECT id, sku, name, price FROM products;"
        ).fetchall()
        product_map = {row["sku"]: dict(row) for row in product_rows}

        for bundle in BUNDLES:
            conn.execute(
                """
                INSERT OR IGNORE INTO bundles (slug, name, purpose, description, discount_pct, is_active)
                VALUES (?, ?, ?, ?, ?, 1);
                """,
                (
                    bundle["slug"],
                    bundle["name"],
                    bundle["purpose"],
                    bundle["description"],
                    float(bundle["discount_pct"]),
                ),
            )
            b_row = conn.execute(
                "SELECT id FROM bundles WHERE slug = ?;", (bundle["slug"],)
            ).fetchone()
            if b_row is None:
                continue
            bundle_id = int(b_row["id"])

            for sku, qty in bundle["items"]:
                if sku in product_map:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO bundle_items (bundle_id, product_id, quantity)
                        VALUES (?, ?, ?);
                        """,
                        (bundle_id, int(product_map[sku]["id"]), int(qty)),
                    )

        if include_sample_orders:
            existing_orders = conn.execute("SELECT COUNT(*) AS cnt FROM orders;").fetchone()
            if existing_orders and int(existing_orders["cnt"]) == 0:
                _seed_demo_orders(conn, product_map)

        cat_count = int(conn.execute("SELECT COUNT(*) FROM categories;").fetchone()[0])
        prod_count = int(conn.execute("SELECT COUNT(*) FROM products;").fetchone()[0])
        bundle_count = int(conn.execute("SELECT COUNT(*) FROM bundles;").fetchone()[0])
        order_count = int(conn.execute("SELECT COUNT(*) FROM orders;").fetchone()[0])
        photo_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM products WHERE image_url LIKE 'http%';"
            ).fetchone()[0]
        )

    return {
        "categories": cat_count,
        "products": prod_count,
        "custom_photos": photo_count,
        "bundles": bundle_count,
        "orders": order_count,
    }


def _seed_demo_orders(conn: Any, product_map: Dict[str, Dict[str, Any]]) -> None:
    """Inserts realistic sample historical orders for immediate analytics visualization."""
    now = datetime.now(timezone.utc)
    demo_orders = [
        {
            "order_number": "STV-20261101-1001",
            "full_name": "Chinedu Okafor",
            "email": "chinedu.okafor@example.ng",
            "phone": "08031234567",
            "address": "14 Ekehuan Road, Benin City",
            "delivery_zone": "edo_local",
            "delivery_fee": 2500.0,
            "status": "Delivered",
            "days_ago": 14,
            "items": [("STV-KM-001", 1), ("STV-LS-002", 1)],
        },
        {
            "order_number": "STV-20261108-1002",
            "full_name": "Amina Suleiman",
            "email": "amina.suleiman@example.ng",
            "phone": "08098765432",
            "address": "22 Admiralty Way, Lekki Phase 1, Lagos",
            "delivery_zone": "lagos_metro",
            "delivery_fee": 3500.0,
            "status": "Shipped",
            "days_ago": 7,
            "items": [("STV-HA-001", 1), ("STV-SC-002", 1), ("STV-SP-001", 1)],
        },
        {
            "order_number": "STV-20261115-1003",
            "full_name": "Tunde Adeyemi",
            "email": "tunde.adeyemi@example.ng",
            "phone": "08123456789",
            "address": "8 Aminu Kano Crescent, Wuse II, Abuja",
            "delivery_zone": "abuja_fct",
            "delivery_fee": 4000.0,
            "status": "Processing",
            "days_ago": 3,
            "items": [("STV-SC-001", 1), ("STV-KM-003", 1)],
        },
        {
            "order_number": "STV-20261119-1004",
            "full_name": "Ngozi Eze",
            "email": "ngozi.eze@example.ng",
            "phone": "07055512345",
            "address": "Hall 3, University of Benin, Ugbowo Campus",
            "delivery_zone": "pickup_benin",
            "delivery_fee": 0.0,
            "status": "Order placed",
            "days_ago": 1,
            "items": [("STV-LS-001", 1), ("STV-KM-002", 1), ("STV-SP-002", 2)],
        },
    ]

    for entry in demo_orders:
        created_ts = (now - timedelta(days=entry["days_ago"])).strftime("%Y-%m-%dT%H:%M:%SZ")
        cur = conn.execute(
            """
            INSERT INTO customers (full_name, email, phone, address, delivery_zone, created_at)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                entry["full_name"],
                entry["email"],
                entry["phone"],
                entry["address"],
                entry["delivery_zone"],
                created_ts,
            ),
        )
        customer_id = int(cur.lastrowid)

        subtotal = 0.0
        line_rows = []
        for sku, qty in entry["items"]:
            prod = product_map[sku]
            unit_price = float(prod["price"])
            line_total = round(unit_price * qty, 2)
            subtotal += line_total
            line_rows.append((int(prod["id"]), prod["name"], sku, qty, unit_price, line_total))

        total_amount = round(subtotal + float(entry["delivery_fee"]), 2)
        order_cur = conn.execute(
            """
            INSERT INTO orders (
                order_number, customer_id, delivery_zone, delivery_address,
                subtotal, delivery_fee, total_amount, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                entry["order_number"],
                customer_id,
                entry["delivery_zone"],
                entry["address"],
                round(subtotal, 2),
                float(entry["delivery_fee"]),
                total_amount,
                entry["status"],
                created_ts,
                created_ts,
            ),
        )
        order_id = int(order_cur.lastrowid)

        for prod_id, prod_name, sku, qty, unit_price, line_total in line_rows:
            conn.execute(
                """
                INSERT INTO order_items (
                    order_id, product_id, product_name, product_sku,
                    quantity, unit_price, line_total
                )
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (order_id, prod_id, prod_name, sku, qty, unit_price, line_total),
            )


if __name__ == "__main__":
    manager = DatabaseManager()
    counts = seed_database(manager, include_sample_orders=True)
    print(f"Seeded Setuvo database ({manager.db_path}): {counts}")