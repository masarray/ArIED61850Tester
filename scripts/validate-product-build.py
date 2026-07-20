#!/usr/bin/env python3
"""Validate the rendered ARSAS product website."""

from __future__ import annotations

import json
import re
import struct
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

EXPECTED_PAGES = (
    "index.html", "download.html", "about.html", "smart-reporting.html",
    "features.html", "control.html", "architecture.html", "roadmap.html", "404.html",
)
EXPECTED_MEDIA = (
    "assets/app-icon.png", "assets/social-card.png",
    "assets/screenshots/arsas-first-launch.webp",
    "assets/screenshots/arsas-multi-ied.webp",
    "assets/screenshots/arsas-live-values.webp",
    "assets/screenshots/arsas-event-log.webp",
    "assets/screenshots/arsas-goose.webp",
    "assets/screenshots/arsas-diagnostics.webp",
    "assets/screenshots/arsas-rcb-scl-export.webp",
)
INSTALLER = "https://github.com/masarray/arsas/releases/latest/download/ARSAS-Windows-x64-Setup.exe"
PORTABLE = "https://github.com/masarray/arsas/releases/latest/download/ARSAS-Windows-x64-Portable.zip"
CHECKSUMS = "https://github.com/masarray/arsas/releases/latest/download/ARSAS-Windows-x64-SHA256SUMS.txt"
REPOSITORY = "https://github.com/masarray/arsas"
LINKEDIN = "https://www.linkedin.com/in/ari-sulistiono"
AUTHOR_GITHUB = "https://github.com/masarray"
APP_ICON = "assets/app-icon.png"


class Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: list[str] = []
        self.icons: list[dict[str, str | None]] = []
        self.h1 = 0
        self.title = ""
        self.in_title = False
        self.description: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "title":
            self.in_title = True
        elif tag == "h1":
            self.h1 += 1
        elif tag == "meta" and values.get("name", "").lower() == "description":
            self.description = values.get("content")
        for key in ("href", "src", "content"):
            value = values.get(key)
            if value:
                self.refs.append(value)
        if tag == "link" and "icon" in (values.get("rel") or "").lower():
            self.icons.append(values)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title += data


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    return struct.unpack(">II", data[16:24])


def local_ref(site: Path, page: Path, reference: str) -> Path | None:
    clean = reference.split("#", 1)[0].split("?", 1)[0]
    parsed = urlparse(clean)
    if not clean or parsed.scheme or parsed.netloc or clean.startswith("#"):
        return None
    return (page.parent / clean).resolve()


def validate_latest(site: Path, errors: list[str]) -> None:
    path = site / "latest.json"
    if not path.exists():
        errors.append("missing latest.json")
        return
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"latest.json: {exc}")
        return
    if manifest.get("schemaVersion") != 1 or manifest.get("product") != "ARSAS":
        errors.append("latest.json has invalid identity")
    if manifest.get("channel") != "stable":
        errors.append("latest.json channel must be stable")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(manifest.get("version", ""))):
        errors.append("latest.json version is invalid")
    installer = manifest.get("installer")
    if not isinstance(installer, dict) or installer.get("url") != INSTALLER:
        errors.append("latest.json installer URL is invalid")
    elif not re.fullmatch(r"[0-9a-fA-F]{64}", str(installer.get("sha256", ""))):
        errors.append("latest.json installer SHA-256 is invalid")


def validate_build_info(site: Path, errors: list[str]) -> str | None:
    path = site / "build-info.json"
    try:
        info = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"build-info.json: {exc}")
        return None
    version = str(info.get("version", ""))
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors.append("build-info.json version is invalid")
    if info.get("repository") != REPOSITORY:
        errors.append("build-info.json repository is invalid")
    author = info.get("author")
    if not isinstance(author, dict) or author.get("name") != "Ari Sulistiono":
        errors.append("build-info.json author is invalid")
    return version or None


def main() -> int:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    errors: list[str] = []

    for relative in EXPECTED_PAGES + EXPECTED_MEDIA + ("site.json", "build-info.json"):
        if not (site / relative).exists():
            errors.append(f"missing deployable file: {relative}")

    combined = ""
    for name in EXPECTED_PAGES:
        page = site / name
        if not page.exists():
            continue
        text = page.read_text(encoding="utf-8")
        combined += text
        parser = Parser()
        parser.feed(text)
        if name != "404.html":
            if parser.h1 != 1:
                errors.append(f"{name}: expected one h1")
            if not parser.title.strip() or not parser.description:
                errors.append(f"{name}: title or description is missing")
        for reference in parser.refs:
            target = local_ref(site, page, reference)
            if target is not None:
                try:
                    target.relative_to(site)
                except ValueError:
                    errors.append(f"{name}: local reference escapes site {reference}")
                    continue
                if not target.exists():
                    errors.append(f"{name}: missing local asset {reference}")

        favicon = [icon for icon in parser.icons if (icon.get("rel") or "").lower() == "icon"]
        if len(favicon) != 1 or favicon[0].get("href") != APP_ICON:
            errors.append(f"{name}: favicon must use {APP_ICON}")
        touch = [icon for icon in parser.icons if (icon.get("rel") or "").lower() == "apple-touch-icon"]
        if len(touch) != 1 or touch[0].get("href") != APP_ICON:
            errors.append(f"{name}: apple-touch-icon must use {APP_ICON}")

    for forbidden in (
        "raw.githubusercontent.com/masarray/arsas/main/Assets/screenshot",
        "https://masarray.github.io/arsas/assets/social-card.svg",
        'href="assets/favicon.svg"',
        "{{ARSAS_", "{{AUTHOR_", "{{INSTALLER_",
    ):
        if forbidden in combined:
            errors.append(f"deployable HTML contains forbidden value: {forbidden}")

    home = (site / "index.html").read_text(encoding="utf-8") if (site / "index.html").exists() else ""
    download = (site / "download.html").read_text(encoding="utf-8") if (site / "download.html").exists() else ""
    about = (site / "about.html").read_text(encoding="utf-8") if (site / "about.html").exists() else ""
    for value in (INSTALLER, 'href="download.html"', "arsas-rcb-scl-export.webp", '"codeRepository"'):
        if value not in home:
            errors.append(f"homepage missing product contract: {value}")
    for value in (INSTALLER, PORTABLE, CHECKSUMS, "Latest stable channel"):
        if value not in download:
            errors.append(f"download page missing {value}")
    for value in (LINKEDIN, AUTHOR_GITHUB, REPOSITORY):
        if value not in about + home:
            errors.append(f"author or open-source identity missing {value}")
    if "github.com/masarray/arsas#quick-start" in home + download:
        errors.append("primary product pages route ordinary users to README quick-start")

    version = validate_build_info(site, errors)
    if version and f'"softwareVersion": "{version}"' not in home:
        errors.append("homepage softwareVersion does not match build-info.json")
    validate_latest(site, errors)

    icon = site / APP_ICON
    social = site / "assets/social-card.png"
    for path, expected in ((icon, (256, 256)), (social, (1200, 630))):
        if path.exists():
            try:
                actual = png_size(path)
                if actual != expected:
                    errors.append(f"{path.name}: expected {expected}, found {actual}")
            except ValueError as exc:
                errors.append(f"{path.name}: {exc}")

    errors = list(dict.fromkeys(errors))
    if errors:
        print("ARSAS product-build validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("ARSAS product-build validation passed: official downloads, author identity, screenshots, metadata and local assets are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
