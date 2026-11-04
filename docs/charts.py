# /// script
# requires-python = ">=3.12"
# ///
"""Draw the test report's figures as SVG from the recorded test results.

    uv run docs/charts.py

Reads docs/test/results/coverage.json (pytest-cov) and writes
docs/diagrams/coverage-by-module.svg and docs/diagrams/test-pyramid.svg.
"""

import json
from html import escape
from pathlib import Path

DOCS = Path(__file__).resolve().parent
RESULTS = DOCS / "test" / "results"
OUT = DOCS / "diagrams"

INK, MUTED, GRID, BAR, TARGET = "#1a1a1a", "#555555", "#e3e3e3", "#1f4e8c", "#8a8a8a"
FONT = "Segoe UI, Calibri, Arial, sans-serif"

# SDD modules and the backend files that implement them.
MODULES = {
    "Accounts and auth": ["services/auth", "core/security", "repositories/users", "routes/auth"],
    "Search and inventory": [
        "services/search", "services/inventory", "services/layout", "services/allocation",
        "repositories/inventory", "repositories/runs",
    ],
    "Fares and refunds": ["services/fares", "services/refunds", "services/money"],
    "Booking and payment": [
        "services/booking", "services/payments", "services/payment_gateway", "services/pnr",
        "repositories/bookings", "routes/bookings",
    ],
    "Cancellation and waitlist": ["services/cancellation", "services/waitlist"],
    "Tickets and PNR": ["services/tickets", "services/ticket_pdf", "services/views"],
    "Administration": [
        "services/admin", "services/network", "services/runs", "repositories/network",
        "routes/admin",
    ],
    "Scheduled jobs": ["jobs/runner", "jobs/tasks", "routes/jobs"],
}

# Automated tests per level, from the final run.
PYRAMID = [
    ("System and acceptance", "Playwright, real browser", 19),
    ("Integration", "API + PostgreSQL", 53),
    ("Unit", "pytest 39, Vitest 19", 58),
]


def module_coverage() -> list[tuple[str, float]]:
    files = json.loads((RESULTS / "coverage.json").read_text(encoding="utf-8"))["files"]
    rows = []
    for module, parts in MODULES.items():
        covered = statements = 0
        for path, data in files.items():
            normal = path.replace("\\", "/").removesuffix(".py")
            if any(normal.endswith(p) for p in parts):
                covered += data["summary"]["covered_lines"]
                statements += data["summary"]["num_statements"]
        rows.append((module, 100 * covered / statements))
    return rows


def coverage_chart(rows: list[tuple[str, float]]) -> str:
    width, label_w, right_pad, row_h, top = 640, 180, 48, 30, 34
    plot_w = width - label_w - right_pad
    height = top + row_h * len(rows) + 30
    x = lambda pct: label_w + plot_w * pct / 100  # noqa: E731
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" font-family="{FONT}">',
        f'<text x="{label_w}" y="16" font-size="12" fill="{MUTED}">'
        "Backend line coverage by module (%)</text>",
    ]
    for pct in (0, 25, 50, 75, 100):
        parts.append(
            f'<line x1="{x(pct)}" y1="{top - 6}" x2="{x(pct)}" y2="{height - 26}" '
            f'stroke="{GRID}" stroke-width="1"/>'
            f'<text x="{x(pct)}" y="{height - 10}" font-size="10" fill="{MUTED}" '
            f'text-anchor="middle">{pct}</text>'
        )
    for i, (name, pct) in enumerate(rows):
        y = top + i * row_h
        bar_w = plot_w * pct / 100
        parts.append(
            f'<text x="{label_w - 10}" y="{y + 15}" font-size="12" fill="{INK}" '
            f'text-anchor="end">{escape(name)}</text>'
            f'<path d="M{label_w} {y + 4} h{bar_w - 4} a4 4 0 0 1 4 4 v8 a4 4 0 0 1 -4 4 '
            f'h-{bar_w - 4} z" fill="{BAR}"/>'
            f'<text x="{label_w + bar_w + 6}" y="{y + 15}" font-size="11" fill="{INK}">'
            f"{pct:.0f}%</text>"
        )
    parts.append(
        f'<line x1="{x(80)}" y1="{top - 10}" x2="{x(80)}" y2="{height - 26}" '
        f'stroke="{TARGET}" stroke-width="1.5" stroke-dasharray="4 3"/>'
        f'<text x="{x(80) - 4}" y="{top - 14}" font-size="10" fill="{MUTED}" '
        'text-anchor="end">target 80% (NFR-15)</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def pyramid_chart() -> str:
    width, height, base_y, layer_h, gap = 640, 250, 236, 66, 6
    widest, narrowest = 560, 200
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" font-family="{FONT}">'
    ]
    fills = ["#0f2747", "#1f4e8c", "#5a83ba"]
    levels = list(reversed(PYRAMID))  # bottom layer first
    step = (widest - narrowest) / len(levels)
    for i, (name, detail, count) in enumerate(levels):
        y_bottom = base_y - i * (layer_h + gap)
        y_top = y_bottom - layer_h
        w_bottom = widest - i * step
        w_top = widest - (i + 1) * step
        cx = width / 2
        points = (
            f"{cx - w_bottom / 2},{y_bottom} {cx + w_bottom / 2},{y_bottom} "
            f"{cx + w_top / 2},{y_top} {cx - w_top / 2},{y_top}"
        )
        fill = fills[len(levels) - 1 - i]
        parts.append(
            f'<polygon points="{points}" fill="{fill}"/>'
            f'<text x="{cx}" y="{y_top + 26}" font-size="14" font-weight="600" fill="#ffffff" '
            f'text-anchor="middle">{escape(name)}: {count}</text>'
            f'<text x="{cx}" y="{y_top + 46}" font-size="11" fill="#eef4fb" '
            f'text-anchor="middle">{escape(detail)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


if __name__ == "__main__":
    rows = module_coverage()
    (OUT / "coverage-by-module.svg").write_text(coverage_chart(rows), encoding="utf-8")
    (OUT / "test-pyramid.svg").write_text(pyramid_chart(), encoding="utf-8")
    for name, pct in rows:
        print(f"{name:28} {pct:5.1f}%")
