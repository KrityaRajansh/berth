# /// script
# requires-python = ">=3.12"
# dependencies = ["markdown>=3.7", "pyyaml>=6.0"]
# ///
"""Render the project documents in docs/ to PDF.

Each document is a Markdown file with a YAML front matter block. The script
renders the PlantUML diagrams in docs/diagrams to SVG, converts each document
to HTML with a cover page and table of contents, then prints the HTML to PDF
with a locally installed Edge or Chrome in headless mode.

Requires Java (for PlantUML) and Edge or Chrome.

Usage:
    uv run docs/build.py            # build every document
    uv run docs/build.py srs sdd    # build only the named documents
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import markdown
import yaml
from markdown.extensions.toc import slugify as toc_slugify

DOCS_DIR = Path(__file__).resolve().parent
BUILD_DIR = DOCS_DIR / "build"
DIST_DIR = DOCS_DIR / "dist"
DIAGRAMS_DIR = DOCS_DIR / "diagrams"
TOOLS_DIR = DOCS_DIR / "tools"
DOCUMENTS = {
    "srs": DOCS_DIR / "srs" / "srs.md",
    "sdd": DOCS_DIR / "sdd" / "sdd.md",
    "test-plan": DOCS_DIR / "test" / "test-plan.md",
    "test-report": DOCS_DIR / "test" / "test-report.md",
    # The submission: overview plus all four documents in one PDF.
    "report": None,
}

# Test cases live in one data file so the plan and the report always agree.
CASES_FILE = DOCS_DIR / "test" / "results" / "cases.json"
CASE_MARKER = re.compile(r"<!-- cases:(UT|IT|ST|AT):(plan|report) -->")
CASE_TITLES = {
    "UT": "Unit test cases",
    "IT": "Integration test cases",
    "ST": "System test cases",
    "AT": "Acceptance test cases",
}

PLANTUML_VERSION = "1.2026.7"
PLANTUML_URL = (
    "https://repo1.maven.org/maven2/net/sourceforge/plantuml/plantuml-mit/"
    f"{PLANTUML_VERSION}/plantuml-mit-{PLANTUML_VERSION}.jar"
)

BROWSER_CANDIDATES = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
]
BROWSER_NAMES = ["msedge", "google-chrome", "chromium", "chrome"]


def find_browser() -> str:
    for candidate in BROWSER_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    for name in BROWSER_NAMES:
        found = shutil.which(name)
        if found:
            return found
    sys.exit("No Edge or Chrome installation found; one is needed to print PDFs.")


def plantuml_jar() -> Path:
    jar = TOOLS_DIR / f"plantuml-mit-{PLANTUML_VERSION}.jar"
    if jar.exists():
        return jar
    TOOLS_DIR.mkdir(exist_ok=True)
    print(f"Downloading PlantUML {PLANTUML_VERSION}")
    with urllib.request.urlopen(PLANTUML_URL) as resp:
        data = resp.read()
    with urllib.request.urlopen(PLANTUML_URL + ".sha1") as resp:
        expected = resp.read().decode().split()[0].strip()
    if hashlib.sha1(data).hexdigest() != expected:
        sys.exit("PlantUML download failed its checksum; not using it.")
    jar.write_bytes(data)
    return jar


def render_diagrams() -> None:
    out_dir = BUILD_DIR / "diagrams"
    out_dir.mkdir(parents=True, exist_ok=True)
    # Hand-drawn SVG figures and generated charts are used as they are.
    for svg in DIAGRAMS_DIR.glob("*.svg"):
        shutil.copy(svg, out_dir / svg.name)
    sources = sorted(p for p in DIAGRAMS_DIR.glob("*.puml") if not p.name.startswith("_"))
    if not sources:
        return
    java = shutil.which("java")
    if not java:
        sys.exit("Java is required to render diagrams.")
    out_dir = BUILD_DIR / "diagrams"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [java, "-jar", str(plantuml_jar()), "-tsvg", "-charset", "UTF-8",
         "-o", str(out_dir), *map(str, sources)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit(f"PlantUML failed:\n{result.stdout}\n{result.stderr}")
    print(f"diagrams: {len(sources)} rendered")


def case_table(level: str, kind: str) -> str:
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    rows = [(cid, c) for cid, c in cases.items() if cid.startswith(level)]
    if kind == "plan":
        header = "| ID | Req. | Test case and input | Expected result |\n|---|---|---|---|"
        lines = [f"| {cid} | {c['req']} | {c['case']} | {c['expected']} |" for cid, c in rows]
        css = "tc plan"
    else:
        header = (
            "| ID | Test case | Expected result | Actual result | Status |\n|---|---|---|---|---|"
        )
        lines = [
            f"| {cid} | {c['case']} | {c['expected']} | {c['actual']} | {c['status']} |"
            for cid, c in rows
        ]
        css = "tc result"
    title = f"**{CASE_TITLES[level]}** ({len(rows)})"
    table = "\n".join([header, *lines])
    return f'{title}\n\n<div class="{css}" markdown="1">\n\n{table}\n\n</div>'


def expand_cases(body: str) -> str:
    return CASE_MARKER.sub(lambda m: case_table(m.group(1), m.group(2)), body)


def split_front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    _, front, body = text.split("---", 2)
    return yaml.safe_load(front) or {}, expand_cases(body)


def render_cover(title: str, subtitle: str, version: str, date: str, meta: dict) -> str:
    rows = "\n".join(
        f"<tr><td>{html.escape(m['name'])}</td><td>{html.escape(m['reg'])}</td></tr>"
        for m in meta["members"]
    )
    links = "".join(
        f"<dt>{label}</dt><dd>{html.escape(meta[key])}</dd>"
        for label, key in (("Live system", "live_url"), ("Source code", "repo_url"))
        if meta.get(key)
    )
    return f"""
<section class="cover">
  <div class="cover-band">
    <p class="course">{html.escape(meta['course'])} &middot; Assignment {meta['assignment_number']}</p>
    <h1 class="doc-title">{html.escape(title)}</h1>
    <p class="doc-subtitle">{html.escape(subtitle)}</p>
    <p class="product">{html.escape(meta['project'])}</p>
  </div>
  <div class="cover-body">
    <dl class="facts">
      <dt>Group</dt><dd>{meta['group_number']}</dd>
      <dt>Assignment</dt><dd>{meta['assignment_number']}: {html.escape(meta['assignment_title'])}</dd>
      <dt>Version</dt><dd>{html.escape(str(version))}</dd>
      <dt>Date</dt><dd>{html.escape(str(date))}</dd>
      {links}
    </dl>
    <table class="members">
      <thead><tr><th>Group member</th><th>Registration no.</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</section>
"""


def render_toc(toc_tokens: list[dict], max_depth: int = 2) -> str:
    def items(tokens: list[dict], depth: int) -> str:
        if not tokens or depth > max_depth:
            return ""
        lis = []
        for t in tokens:
            children = items(t.get("children", []), depth + 1)
            lis.append(f'<li><a href="#{t["id"]}">{t["name"]}</a>{children}</li>')
        return f"<ol>{''.join(lis)}</ol>"

    return f'<nav class="toc"><h2>Contents</h2>{items(toc_tokens, 1)}</nav>'


def convert(id_prefix: str = "") -> markdown.Markdown:
    """A Markdown converter; the prefix keeps heading ids unique when documents are combined."""

    def slug(value: str, separator: str) -> str:
        return id_prefix + toc_slugify(value, separator)

    return markdown.Markdown(
        extensions=["tables", "fenced_code", "attr_list", "sane_lists", "toc", "md_in_html"],
        extension_configs={"toc": {"permalink": False, "slugify": slug}},
    )


def page(title: str, footer: str, body: str) -> str:
    css = (DOCS_DIR / "style.css").read_text(encoding="utf-8")
    css = css.replace("__FOOTER_LEFT__", footer.replace('"', '\\"'))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


def build_html(source: Path, meta: dict) -> str:
    doc_meta, body = split_front_matter(source.read_text(encoding="utf-8"))
    md = convert()
    content = md.convert(body)
    version = str(doc_meta.get("version", ""))
    cover = render_cover(
        doc_meta["title"], doc_meta.get("subtitle", ""), version, doc_meta.get("date", ""), meta
    )
    return page(
        doc_meta["title"],
        f"{meta['project']} | {doc_meta['title']} v{version}",
        f"{cover}\n{render_toc(md.toc_tokens)}\n<main>{content}</main>",
    )


REPORT_PARTS = [
    ("", "", DOCS_DIR / "report" / "overview.md"),
    ("Part I", "Software Requirements Specification", DOCS_DIR / "srs" / "srs.md"),
    ("Part II", "Software Design Document", DOCS_DIR / "sdd" / "sdd.md"),
    ("Part III", "Software Test Plan", DOCS_DIR / "test" / "test-plan.md"),
    ("Part IV", "Software Test Report", DOCS_DIR / "test" / "test-report.md"),
]


def build_report_html(meta: dict) -> str:
    """One document with the overview and the three parts, as the brief asks for one report."""
    sections, toc = [], []
    for index, (label, title, source) in enumerate(REPORT_PARTS):
        doc_meta, body = split_front_matter(source.read_text(encoding="utf-8"))
        md = convert(id_prefix=f"p{index}-")
        content = md.convert(body)
        if label:
            anchor = f"part-{index}"
            sections.append(
                f'<section class="part-divider" id="{anchor}">'
                f'<p class="part-no">{label}</p><h1>{html.escape(title)}</h1>'
                f'<p class="part-meta">Version {doc_meta.get("version", "")} &middot; '
                f'{doc_meta.get("date", "")}</p></section>'
            )
            toc.append({"id": anchor, "name": f"{label}: {title}", "children": md.toc_tokens})
        else:
            toc.extend(md.toc_tokens)
        sections.append(content)

    cover = render_cover(
        meta["assignment_title"],
        "Software Requirements Specification, Software Design Document, "
        "and Software Test Plan and Report",
        "1.1",
        "4 November 2026",
        meta,
    )
    return page(
        f"{meta['project']}: {meta['assignment_title']}",
        f"{meta['project']} | Group {meta['group_number']} | CSC702 Software Engineering Report",
        f'{cover}\n<div class="report-toc">{render_toc(toc)}</div>\n'
        f"<main>{''.join(sections)}</main>",
    )


def print_pdf(browser: str, html_file: Path, pdf_file: Path) -> None:
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                f"--user-data-dir={profile}",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_file}",
                html_file.as_uri(),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )


def main(selected: list[str]) -> None:
    names = selected or list(DOCUMENTS)
    unknown = [n for n in names if n not in DOCUMENTS]
    if unknown:
        sys.exit(f"Unknown document(s): {', '.join(unknown)}. Known: {', '.join(DOCUMENTS)}")

    meta = yaml.safe_load((DOCS_DIR / "meta.yaml").read_text(encoding="utf-8"))
    browser = find_browser()
    BUILD_DIR.mkdir(exist_ok=True)
    DIST_DIR.mkdir(exist_ok=True)
    render_diagrams()

    for name in names:
        source = DOCUMENTS[name]
        html_file = BUILD_DIR / f"{name}.html"
        pdf_file = DIST_DIR / f"{name}.pdf"
        document = build_report_html(meta) if source is None else build_html(source, meta)
        html_file.write_text(document, encoding="utf-8")
        print_pdf(browser, html_file, pdf_file)
        print(f"{name}: {pdf_file.relative_to(DOCS_DIR.parent)}")


if __name__ == "__main__":
    main(sys.argv[1:])
