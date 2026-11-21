"""scripts/generate_product_images.py

Generates 20 custom hardware-specific vector SVG illustrations inside
static/images/products/ plus static/images/product_placeholder.svg.
"""

from html import escape
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.seed_data import PRODUCTS

PALETTES = {
    "laptop-stands-cooling": ("#0f172a", "#134e4a", "#14b8a6", "#ccfbf1"),
    "keyboards-mice": ("#0f172a", "#1e293b", "#0ea5e9", "#e0f2fe"),
    "headphones-audio": ("#111827", "#1f2937", "#f59e0b", "#fef3c7"),
    "storage-connectivity": ("#0f172a", "#172554", "#38bdf8", "#e0f2fe"),
    "study-productivity": ("#0f172a", "#064e3b", "#10b981", "#d1fae5"),
    "desk-essentials": ("#18181b", "#27272a", "#2dd4bf", "#ccfbf1"),
    "computer-accessories": ("#0f172a", "#1e1b4b", "#818cf8", "#e0e7ff"),
}

ARTWORKS = {
    "STV-LS-001": """
      <g stroke="#5eead4" stroke-width="5" stroke-linecap="round" fill="none">
        <line x1="160" y1="245" x2="310" y2="115"/>
        <line x1="480" y1="245" x2="330" y2="115"/>
        <line x1="205" y1="245" x2="365" y2="128"/>
        <line x1="435" y1="245" x2="275" y2="128"/>
        <line x1="145" y1="245" x2="495" y2="245" stroke="#94a3b8" stroke-width="4"/>
      </g>
      <circle cx="320" cy="122" r="7" fill="#f8fafc"/>
      <circle cx="235" cy="182" r="5" fill="#14b8a6"/>
      <circle cx="405" cy="182" r="5" fill="#14b8a6"/>
    """,
    "STV-LS-002": """
      <path d="M180 245 L455 245 L430 228 L230 228 L390 120 L465 135 L472 120 L382 102 L180 232 Z"
            fill="#cbd5e1" stroke="#f8fafc" stroke-width="2"/>
      <rect x="260" y="160" width="90" height="8" rx="4" transform="rotate(-33 260 160)" fill="#0f172a"/>
      <line x1="150" y1="247" x2="490" y2="247" stroke="#5eead4" stroke-width="3"/>
    """,
    "STV-LS-003": """
      <rect x="170" y="105" width="300" height="145" rx="18" fill="#1e293b" stroke="#5eead4" stroke-width="3"/>
      <circle cx="255" cy="178" r="46" fill="#0f172a" stroke="#14b8a6" stroke-width="4"/>
      <circle cx="385" cy="178" r="46" fill="#0f172a" stroke="#14b8a6" stroke-width="4"/>
      <circle cx="255" cy="178" r="14" fill="#5eead4"/>
      <circle cx="385" cy="178" r="14" fill="#5eead4"/>
      <path d="M255 132 A46 46 0 0 1 301 178 M385 132 A46 46 0 0 1 431 178"
            stroke="#99f6e4" stroke-width="3" fill="none"/>
    """,
    "STV-KM-001": """
      <rect x="145" y="112" width="350" height="132" rx="12" fill="#1e293b" stroke="#38bdf8" stroke-width="3"/>
      <rect x="160" y="126" width="24" height="18" rx="3" fill="#f97316"/>
      <g fill="#334155" stroke="#64748b" stroke-width="1">
        <rect x="190" y="126" width="24" height="18" rx="3"/>
        <rect x="220" y="126" width="24" height="18" rx="3"/>
        <rect x="250" y="126" width="24" height="18" rx="3"/>
        <rect x="280" y="126" width="24" height="18" rx="3"/>
        <rect x="310" y="126" width="24" height="18" rx="3"/>
        <rect x="340" y="126" width="24" height="18" rx="3"/>
        <rect x="370" y="126" width="24" height="18" rx="3"/>
        <rect x="400" y="126" width="24" height="18" rx="3"/>
        <rect x="430" y="126" width="48" height="18" rx="3"/>
        <rect x="160" y="150" width="36" height="18" rx="3"/>
        <rect x="202" y="150" width="24" height="18" rx="3"/>
        <rect x="232" y="150" width="24" height="18" rx="3"/>
        <rect x="262" y="150" width="24" height="18" rx="3"/>
        <rect x="292" y="150" width="24" height="18" rx="3"/>
        <rect x="322" y="150" width="24" height="18" rx="3"/>
        <rect x="352" y="150" width="24" height="18" rx="3"/>
        <rect x="382" y="150" width="24" height="18" rx="3"/>
        <rect x="412" y="150" width="66" height="18" rx="3"/>
        <rect x="160" y="174" width="46" height="18" rx="3"/>
        <rect x="212" y="174" width="24" height="18" rx="3"/>
        <rect x="242" y="174" width="24" height="18" rx="3"/>
        <rect x="272" y="174" width="24" height="18" rx="3"/>
        <rect x="302" y="174" width="24" height="18" rx="3"/>
        <rect x="332" y="174" width="24" height="18" rx="3"/>
        <rect x="362" y="174" width="24" height="18" rx="3"/>
        <rect x="392" y="174" width="24" height="18" rx="3"/>
        <rect x="160" y="198" width="30" height="18" rx="3"/>
        <rect x="196" y="198" width="30" height="18" rx="3"/>
        <rect x="232" y="198" width="136" height="18" rx="3"/>
        <rect x="374" y="198" width="30" height="18" rx="3"/>
        <rect x="410" y="198" width="68" height="18" rx="3"/>
      </g>
      <rect x="422" y="174" width="56" height="18" rx="3" fill="#f97316"/>
    """,
    "STV-KM-002": """
      <rect x="160" y="122" width="320" height="114" rx="18" fill="#334155" stroke="#94a3b8" stroke-width="2.5"/>
      <g fill="#eab308">
        <circle cx="185" cy="144" r="8"/><circle cx="207" cy="144" r="8"/><circle cx="229" cy="144" r="8"/>
      </g>
      <g fill="#1e293b" stroke="#64748b" stroke-width="1">
        <circle cx="251" cy="144" r="8"/><circle cx="273" cy="144" r="8"/><circle cx="295" cy="144" r="8"/>
        <circle cx="317" cy="144" r="8"/><circle cx="339" cy="144" r="8"/><circle cx="361" cy="144" r="8"/>
        <circle cx="383" cy="144" r="8"/><circle cx="405" cy="144" r="8"/><circle cx="427" cy="144" r="8"/>
        <circle cx="449" cy="144" r="8"/>
        <circle cx="192" cy="167" r="8"/><circle cx="214" cy="167" r="8"/><circle cx="236" cy="167" r="8"/>
        <circle cx="258" cy="167" r="8"/><circle cx="280" cy="167" r="8"/><circle cx="302" cy="167" r="8"/>
        <circle cx="324" cy="167" r="8"/><circle cx="346" cy="167" r="8"/><circle cx="368" cy="167" r="8"/>
        <circle cx="390" cy="167" r="8"/><circle cx="412" cy="167" r="8"/><circle cx="440" cy="167" r="10"/>
        <circle cx="198" cy="190" r="8"/><circle cx="220" cy="190" r="8"/><circle cx="242" cy="190" r="8"/>
        <circle cx="264" cy="190" r="8"/><circle cx="286" cy="190" r="8"/><circle cx="308" cy="190" r="8"/>
        <circle cx="330" cy="190" r="8"/><circle cx="352" cy="190" r="8"/><circle cx="374" cy="190" r="8"/>
        <circle cx="396" cy="190" r="8"/><circle cx="426" cy="190" r="11"/>
        <rect x="242" y="206" width="136" height="14" rx="7"/>
      </g>
    """,
    "STV-KM-003": """
      <rect x="268" y="96" width="104" height="162" rx="50" fill="#1e293b" stroke="#38bdf8" stroke-width="3"/>
      <path d="M268 158 Q252 180 268 206" fill="#0f172a" stroke="#38bdf8" stroke-width="2.5"/>
      <line x1="320" y1="96" x2="320" y2="156" stroke="#475569" stroke-width="2"/>
      <rect x="313" y="114" width="14" height="28" rx="7" fill="#38bdf8"/>
      <circle cx="320" cy="150" r="3.5" fill="#94a3b8"/>
    """,
    "STV-KM-004": """
      <path d="M275 248 C262 200 282 112 332 104 C368 98 386 142 374 202 C368 232 355 248 335 248 Z"
            fill="#1e293b" stroke="#38bdf8" stroke-width="3"/>
      <path d="M322 108 C312 152 315 198 326 244" stroke="#38bdf8" stroke-width="2.5" fill="none"/>
      <rect x="336" y="132" width="10" height="24" rx="5" fill="#38bdf8"/>
      <line x1="230" y1="250" x2="410" y2="250" stroke="#64748b" stroke-width="3"/>
    """,
    "STV-HA-001": """
      <path d="M235 182 C235 122 405 122 405 182" fill="none" stroke="#f59e0b" stroke-width="10" stroke-linecap="round"/>
      <rect x="216" y="168" width="34" height="64" rx="16" fill="#1f2937" stroke="#fbbf24" stroke-width="3"/>
      <rect x="390" y="168" width="34" height="64" rx="16" fill="#1f2937" stroke="#fbbf24" stroke-width="3"/>
      <path d="M196 184 Q182 200 196 216 M444 184 Q458 200 444 216" stroke="#fcd34d" stroke-width="3" fill="none" stroke-linecap="round"/>
    """,
    "STV-HA-002": """
      <path d="M238 180 C238 118 402 118 402 180" fill="none" stroke="#9ca3af" stroke-width="9" stroke-linecap="round"/>
      <ellipse cx="234" cy="198" rx="22" ry="34" fill="#1f2937" stroke="#f59e0b" stroke-width="3"/>
      <ellipse cx="406" cy="198" rx="22" ry="34" fill="#1f2937" stroke="#f59e0b" stroke-width="3"/>
      <path d="M234 232 C234 256 268 258 295 252" fill="none" stroke="#9ca3af" stroke-width="3" stroke-linecap="round"/>
    """,
    "STV-HA-003": """
      <rect x="296" y="96" width="48" height="92" rx="24" fill="#1f2937" stroke="#f59e0b" stroke-width="3"/>
      <line x1="296" y1="138" x2="344" y2="138" stroke="#f59e0b" stroke-width="2.5"/>
      <path d="M280 154 C280 196 360 196 360 154" fill="none" stroke="#9ca3af" stroke-width="4" stroke-linecap="round"/>
      <line x1="320" y1="186" x2="320" y2="238" stroke="#9ca3af" stroke-width="5"/>
      <ellipse cx="320" cy="242" rx="48" ry="10" fill="#374151" stroke="#f59e0b" stroke-width="2"/>
    """,
    "STV-SC-001": """
      <rect x="248" y="98" width="144" height="154" rx="20" fill="#1e293b" stroke="#38bdf8" stroke-width="3"/>
      <g stroke="#334155" stroke-width="4">
        <line x1="268" y1="126" x2="372" y2="126"/><line x1="268" y1="142" x2="372" y2="142"/>
        <line x1="268" y1="158" x2="372" y2="158"/><line x1="268" y1="174" x2="372" y2="174"/>
        <line x1="268" y1="190" x2="372" y2="190"/><line x1="268" y1="206" x2="372" y2="206"/>
      </g>
      <rect x="292" y="224" width="56" height="10" rx="5" fill="#38bdf8"/>
    """,
    "STV-SC-002": """
      <rect x="180" y="150" width="265" height="54" rx="10" fill="#cbd5e1" stroke="#38bdf8" stroke-width="3"/>
      <path d="M445 177 C485 177 492 135 462 126" fill="none" stroke="#94a3b8" stroke-width="5" stroke-linecap="round"/>
      <rect x="442" y="118" width="24" height="14" rx="3" fill="#38bdf8"/>
      <g fill="#0f172a">
        <rect x="200" y="168" width="32" height="16" rx="2"/>
        <rect x="244" y="168" width="28" height="16" rx="2"/>
        <rect x="284" y="168" width="28" height="16" rx="2"/>
        <rect x="324" y="168" width="36" height="16" rx="2"/>
        <rect x="372" y="168" width="22" height="16" rx="4"/>
      </g>
    """,
    "STV-SC-003": """
      <ellipse cx="320" cy="176" rx="88" ry="52" fill="none" stroke="#38bdf8" stroke-width="8"/>
      <ellipse cx="320" cy="176" rx="74" ry="40" fill="none" stroke="#7dd3fc" stroke-width="4"/>
      <rect x="210" y="132" width="34" height="16" rx="4" fill="#1e293b" stroke="#38bdf8" stroke-width="2"/>
      <rect x="396" y="204" width="34" height="16" rx="4" fill="#1e293b" stroke="#38bdf8" stroke-width="2"/>
    """,
    "STV-SP-001": """
      <circle cx="320" cy="175" r="74" fill="#1e293b" stroke="#10b981" stroke-width="6"/>
      <circle cx="320" cy="175" r="58" fill="#0f172a"/>
      <text x="320" y="185" text-anchor="middle" fill="#6ee7b7" font-family="monospace" font-size="30" font-weight="bold">25:00</text>
    """,
    "STV-SP-002": """
      <rect x="218" y="114" width="184" height="134" rx="10" fill="#1e293b" stroke="#6ee7b7" stroke-width="2.5"/>
      <rect x="234" y="102" width="184" height="134" rx="10" fill="#065f46" stroke="#34d399" stroke-width="3"/>
      <line x1="256" y1="102" x2="256" y2="236" stroke="#10b981" stroke-width="4"/>
      <g fill="#a7f3d0">
        <circle cx="290" cy="135" r="2"/><circle cx="315" cy="135" r="2"/><circle cx="340" cy="135" r="2"/><circle cx="365" cy="135" r="2"/>
        <circle cx="290" cy="160" r="2"/><circle cx="315" cy="160" r="2"/><circle cx="340" cy="160" r="2"/><circle cx="365" cy="160" r="2"/>
        <circle cx="290" cy="185" r="2"/><circle cx="315" cy="185" r="2"/><circle cx="340" cy="185" r="2"/><circle cx="365" cy="185" r="2"/>
      </g>
    """,
    "STV-SP-003": """
      <rect x="188" y="146" width="108" height="58" rx="14" fill="rgba(251,191,36,0.28)" stroke="#f59e0b" stroke-width="4"/>
      <rect x="344" y="146" width="108" height="58" rx="14" fill="rgba(251,191,36,0.28)" stroke="#f59e0b" stroke-width="4"/>
      <path d="M296 168 Q320 156 344 168" fill="none" stroke="#f59e0b" stroke-width="4"/>
      <line x1="170" y1="164" x2="188" y2="164" stroke="#f59e0b" stroke-width="4"/>
      <line x1="452" y1="164" x2="470" y2="164" stroke="#f59e0b" stroke-width="4"/>
    """,
    "STV-DE-001": """
      <polygon points="185,146 455,146 505,246 135,246" fill="rgba(94,234,212,0.16)"/>
      <rect x="170" y="132" width="300" height="16" rx="8" fill="#e2e8f0" stroke="#2dd4bf" stroke-width="2.5"/>
      <rect x="294" y="114" width="52" height="20" rx="4" fill="#334155"/>
    """,
    "STV-DE-002": """
      <rect x="150" y="116" width="340" height="128" rx="14" fill="#1e293b" stroke="#2dd4bf" stroke-width="3"/>
      <rect x="160" y="126" width="320" height="108" rx="9" fill="none" stroke="#5eead4" stroke-width="1.5" stroke-dasharray="6 4"/>
      <rect x="424" y="206" width="42" height="16" rx="4" fill="#0f766e"/>
    """,
    "STV-CA-001": """
      <rect x="215" y="124" width="210" height="76" rx="22" fill="#1e293b" stroke="#818cf8" stroke-width="3"/>
      <circle cx="320" cy="162" r="26" fill="#0f172a" stroke="#a5b4fc" stroke-width="4"/>
      <circle cx="320" cy="162" r="11" fill="#4f46e5"/>
      <circle cx="315" cy="157" r="3.5" fill="#e0e7ff"/>
      <path d="M275 200 L260 236 L380 236 L365 200 Z" fill="#334155"/>
    """,
    "STV-CA-002": """
      <rect x="150" y="140" width="340" height="72" rx="12" fill="#f8fafc" stroke="#818cf8" stroke-width="3"/>
      <g fill="#1e293b">
        <rect x="172" y="158" width="36" height="36" rx="5"/>
        <rect x="220" y="158" width="36" height="36" rx="5"/>
        <rect x="268" y="158" width="36" height="36" rx="5"/>
        <rect x="316" y="158" width="36" height="36" rx="5"/>
        <rect x="364" y="158" width="36" height="36" rx="5"/>
      </g>
      <rect x="416" y="160" width="20" height="12" rx="3" fill="#4f46e5"/>
      <rect x="444" y="160" width="26" height="12" rx="5" fill="#0ea5e9"/>
      <rect x="444" y="180" width="26" height="12" rx="5" fill="#0ea5e9"/>
    """,
}


def build_svg(sku: str, name: str, brand: str, category_slug: str) -> str:
    bg_start, bg_end, accent, badge_bg = PALETTES.get(
        category_slug, ("#0f172a", "#134e4a", "#14b8a6", "#ccfbf1")
    )
    artwork = ARTWORKS.get(sku, "")
    short_title = name if len(name) <= 44 else name[:41].rstrip() + "..."

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 400" width="640" height="400" role="img" aria-label="{escape(name)}">
  <defs>
    <linearGradient id="bg-{sku}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg_start}"/>
      <stop offset="100%" stop-color="{bg_end}"/>
    </linearGradient>
    <pattern id="grid-{sku}" width="32" height="32" patternUnits="userSpaceOnUse">
      <path d="M 32 0 L 0 0 0 32" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
    </pattern>
  </defs>

  <rect width="640" height="400" fill="url(#bg-{sku})"/>
  <rect width="640" height="400" fill="url(#grid-{sku})"/>

  <!-- Top Brand & SKU Header -->
  <rect x="28" y="24" width="136" height="28" rx="14" fill="{badge_bg}"/>
  <text x="96" y="42" text-anchor="middle" fill="#0f172a" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="12" font-weight="700">{escape(brand.upper())}</text>

  <text x="612" y="42" text-anchor="end" fill="#94a3b8" font-family="monospace" font-size="13" font-weight="700">{escape(sku)}</text>

  <!-- Vector Hardware Illustration -->
  {artwork}

  <!-- Bottom Product Label Strip -->
  <rect x="0" y="318" width="640" height="82" fill="rgba(15,23,42,0.78)"/>
  <line x1="0" y1="318" x2="640" y2="318" stroke="{accent}" stroke-width="2"/>
  <text x="32" y="352" fill="#ffffff" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="17" font-weight="700">{escape(short_title)}</text>
  <text x="32" y="376" fill="{accent}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="12" font-weight="600">SETUVO CURATED WORKSTATION HARDWARE</text>
</svg>
"""


def generate_all_product_svgs() -> int:
    images_dir = PROJECT_ROOT / "static" / "images"
    products_dir = images_dir / "products"
    products_dir.mkdir(parents=True, exist_ok=True)

    placeholder_svg = build_svg(
        sku="SETUVO",
        name="Curated Workstation Gear",
        brand="Setuvo",
        category_slug="laptop-stands-cooling",
    )
    (images_dir / "product_placeholder.svg").write_text(
        placeholder_svg, encoding="utf-8"
    )

    count = 0
    for prod in PRODUCTS:
        sku = prod["sku"]
        svg_text = build_svg(
            sku=sku,
            name=prod["name"],
            brand=prod["brand"],
            category_slug=prod["category_slug"],
        )
        out_file = products_dir / f"{sku.lower()}.svg"
        out_file.write_text(svg_text, encoding="utf-8")
        count += 1

    return count


if __name__ == "__main__":
    generated = generate_all_product_svgs()
    print(f"Generated {generated} product SVG illustrations + product_placeholder.svg")