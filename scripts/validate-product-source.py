#!/usr/bin/env python3
"""Validate the ARSAS product-site source before rendering."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "landing"
CANONICAL_ROOT = "https://masarray.github.io/arsas/"
TEMPLATES = (LANDING / "templates" / "index.html", LANDING / "templates" / "download.html")
PAGES = tuple(LANDING / name for name in (
    "about.html", "smart-reporting.html", "features.html", "control.html", "architecture.html", "roadmap.html"
))
TOKENS = {
    "ARSAS_VERSION", "PRODUCT_NAME", "CANONICAL_ROOT", "REPOSITORY_URL",
    "ENGINE_REPOSITORY_URL", "AUTHOR_NAME", "AUTHOR_LINKEDIN", "AUTHOR_GITHUB",
    "INSTALLER_URL", "PORTABLE_URL", "CHECKSUMS_URL",
}


class Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title = ""
        self.h1 = 0
        self.description: str | None = None
        self.canonical: str | None = None
        self.meta: dict[str, str] = {}
        self.refs: list[str] = []
        self.images: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "title":
            self.in_title = True
        elif tag == "h1":
            self.h1 += 1
        elif tag == "meta":
            key = values.get("name") or values.get("property")
            value = values.get("content")
            if key and value:
                self.meta[key.lower()] = value
            if values.get("name", "").lower() == "description":
                self.description = value
        elif tag == "link":
            href = values.get("href")
            if (values.get("rel") or "").lower() == "canonical":
                self.canonical = href
            if href:
                self.refs.append(href)
        elif tag == "a" and values.get("href"):
            self.refs.append(values["href"] or "")
        elif tag == "img" and values.get("src"):
            self.images.append(values)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title += data


def local_target(page: Path, value: str) -> Path | None:
    clean = value.split("#", 1)[0].split("?", 1)[0]
    parsed = urlparse(clean)
    if not clean or parsed.scheme or parsed.netloc or clean.startswith("#"):
        return None
    return (page.parent / clean).resolve()


def check_page(page: Path, errors: list[str], template: bool = False) -> None:
    if not page.exists():
        errors.append(f"missing page: {page.relative_to(ROOT)}")
        return
    text = page.read_text(encoding="utf-8")
    parser = Parser()
    parser.feed(text)
    label = page.relative_to(ROOT)

    if not parser.title.strip() or len(parser.title.strip()) > 75:
        errors.append(f"{label}: invalid title")
    if parser.h1 != 1:
        errors.append(f"{label}: expected one h1, found {parser.h1}")
    if not parser.description or not 70 <= len(parser.description) <= 220:
        errors.append(f"{label}: invalid meta description")
    if not parser.canonical:
        errors.append(f"{label}: missing canonical")
    for key in ("og:title", "og:description", "og:url", "og:image", "og:image:width", "og:image:height"):
        if not parser.meta.get(key):
            errors.append(f"{label}: missing {key}")

    for ref in parser.refs:
        target = local_target(page, ref)
        if target is not None and not target.exists():
            errors.append(f"{label}: missing local reference {ref}")
    for image in parser.images:
        src = image.get("src") or ""
        target = local_target(page, src)
        if target is not None and not target.exists():
            errors.append(f"{label}: missing local image {src}")
        if image.get("alt") is None or not image.get("width") or not image.get("height"):
            errors.append(f"{label}: incomplete image metadata {src}")

    if template:
        unknown = set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", text)) - TOKENS
        if unknown:
            errors.append(f"{label}: unknown tokens {sorted(unknown)}")


def check_config(errors: list[str]) -> None:
    try:
        config = json.loads((LANDING / "site.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"landing/site.json: {exc}")
        return
    checks = {
        ("product", "repository"): "https://github.com/masarray/arsas",
        ("author", "name"): "Ari Sulistiono",
        ("author", "linkedin"): "https://www.linkedin.com/in/ari-sulistiono",
        ("author", "github"): "https://github.com/masarray",
    }
    for path, expected in checks.items():
        value: object = config
        for key in path:
            value = value.get(key) if isinstance(value, dict) else None
        if value != expected:
            errors.append(f"landing/site.json: {'.'.join(path)} must be {expected}")


def check_contract(errors: list[str]) -> None:
    home = TEMPLATES[0].read_text(encoding="utf-8") if TEMPLATES[0].exists() else ""
    download = TEMPLATES[1].read_text(encoding="utf-8") if TEMPLATES[1].exists() else ""
    about = (LANDING / "about.html").read_text(encoding="utf-8") if (LANDING / "about.html").exists() else ""
    for value in ("{{INSTALLER_URL}}", 'href="download.html"', "arsas-rcb-scl-export.webp", "{{AUTHOR_LINKEDIN}}"):
        if value not in home:
            errors.append(f"homepage template missing {value}")
    for value in ("{{INSTALLER_URL}}", "{{PORTABLE_URL}}", "{{CHECKSUMS_URL}}", "{{ARSAS_VERSION}}"):
        if value not in download:
            errors.append(f"download template missing {value}")
    for value in ("https://www.linkedin.com/in/ari-sulistiono", "https://github.com/masarray"):
        if value not in about:
            errors.append(f"about page missing {value}")
    if "github.com/masarray/arsas#quick-start" in home + download:
        errors.append("product templates route users to README quick-start")


def check_sitemap(errors: list[str]) -> None:
    try:
        ET.parse(LANDING / "sitemap.xml")
    except (OSError, ET.ParseError) as exc:
        errors.append(f"landing/sitemap.xml: {exc}")
        return
    text = (LANDING / "sitemap.xml").read_text(encoding="utf-8")
    for name in ("download.html", "about.html", "smart-reporting.html", "features.html", "control.html", "architecture.html", "roadmap.html"):
        if f"{CANONICAL_ROOT}{name}" not in text:
            errors.append(f"landing/sitemap.xml missing {name}")


def main() -> int:
    errors: list[str] = []
    check_config(errors)
    for page in TEMPLATES:
        check_page(page, errors, template=True)
    for page in PAGES:
        check_page(page, errors)
    check_contract(errors)
    check_sitemap(errors)
    errors = list(dict.fromkeys(errors))
    if errors:
        print("ARSAS product-source validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("ARSAS product-source validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
