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
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import markdown
import yaml

DOCS_DIR = Path(__file__).resolve().parent
BUILD_DIR = DOCS_DIR / "build"
DIST_DIR = DOCS_DIR / "dist"
DIAGRAMS_DIR = DOCS_DIR / "diagrams"
TOOLS_DIR = DOCS_DIR / "tools"
DOCUMENTS = {
    "srs": DOCS_DIR / "srs" / "srs.md",
    "sdd": DOCS_DIR / "sdd" / "sdd.md",
    "test": DOCS_DIR / "test" / "test-plan-report.md",
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


def split_front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    _, front, body = text.split("---", 2)
    return yaml.safe_load(front) or {}, body


def render_cover(doc_meta: dict, meta: dict) -> str:
    rows = "\n".join(
        f"<tr><td>{html.escape(m['name'])}</td><td>{html.escape(m['reg'])}</td></tr>"
        for m in meta["members"]
    )
    return f"""
<section class="cover">
  <p class="course">{html.escape(meta['course'])}</p>
  <h1 class="doc-title">{html.escape(doc_meta['title'])}</h1>
  <p class="doc-subtitle">{html.escape(doc_meta.get('subtitle', ''))}</p>
  <dl class="facts">
    <dt>Group</dt><dd>{meta['group_number']}</dd>
    <dt>Assignment</dt><dd>{meta['assignment_number']}: {html.escape(meta['assignment_title'])}</dd>
    <dt>Version</dt><dd>{html.escape(str(doc_meta.get('version', '')))}</dd>
    <dt>Date</dt><dd>{html.escape(str(doc_meta.get('date', '')))}</dd>
  </dl>
  <table class="members">
    <thead><tr><th>Name</th><th>Registration no.</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</section>
"""


def render_toc(toc_tokens: list[dict]) -> str:
    def items(tokens: list[dict], depth: int) -> str:
        if not tokens or depth > 2:
            return ""
        lis = []
        for t in tokens:
            children = items(t.get("children", []), depth + 1)
            lis.append(f'<li><a href="#{t["id"]}">{t["name"]}</a>{children}</li>')
        return f"<ol>{''.join(lis)}</ol>"

    return f'<nav class="toc"><h2>Contents</h2>{items(toc_tokens, 1)}</nav>'


def build_html(source: Path, meta: dict) -> str:
    doc_meta, body = split_front_matter(source.read_text(encoding="utf-8"))
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "attr_list", "sane_lists", "toc", "md_in_html"],
        extension_configs={"toc": {"permalink": False}},
    )
    content = md.convert(body)
    css = (DOCS_DIR / "style.css").read_text(encoding="utf-8")
    footer_left = f"{meta['project']} | {doc_meta['title']} v{doc_meta.get('version', '')}"
    css = css.replace("__FOOTER_LEFT__", footer_left.replace('"', '\\"'))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(doc_meta['title'])}</title>
<style>{css}</style>
</head>
<body>
{render_cover(doc_meta, meta)}
{render_toc(md.toc_tokens)}
<main>{content}</main>
</body>
</html>
"""


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
        html_file.write_text(build_html(source, meta), encoding="utf-8")
        print_pdf(browser, html_file, pdf_file)
        print(f"{name}: {pdf_file.relative_to(DOCS_DIR.parent)}")


if __name__ == "__main__":
    main(sys.argv[1:])
