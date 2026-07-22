#!/usr/bin/env python3
"""Generate a deterministic SPDX 2.3 JSON SBOM for an extracted ARSAS Windows package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def spdx_id(relative: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9.-]+", "-", relative).strip("-")
    suffix = hashlib.sha256(relative.encode("utf-8")).hexdigest()[:12]
    return f"SPDXRef-File-{normalized[:80]}-{suffix}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    package_dir = Path(args.package_dir).resolve()
    output = Path(args.output).resolve()
    if not package_dir.is_dir():
        raise SystemExit(f"Package directory does not exist: {package_dir}")
    if not re.fullmatch(r"\d+\.\d+\.\d+([-.][0-9A-Za-z.-]+)?", args.version):
        raise SystemExit("Version is not semantic")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", args.source_commit):
        raise SystemExit("Source commit must be a full Git SHA")

    files = [path for path in sorted(package_dir.rglob("*")) if path.is_file()]
    if not files:
        raise SystemExit("Package directory contains no files")
    file_entries = []
    verification_input = hashlib.sha1()
    relationships = [{"spdxElementId": "SPDXRef-DOCUMENT", "relationshipType": "DESCRIBES", "relatedSpdxElement": "SPDXRef-Package-ARSAS"}]
    for path in files:
        relative = path.relative_to(package_dir).as_posix()
        digest = sha256(path)
        verification_input.update(bytes.fromhex(digest))
        identifier = spdx_id(relative)
        file_entries.append({
            "SPDXID": identifier,
            "fileName": "./" + relative,
            "checksums": [{"algorithm": "SHA256", "checksumValue": digest}],
            "licenseConcluded": "NOASSERTION",
            "licenseInfoInFiles": ["NOASSERTION"],
            "copyrightText": "NOASSERTION",
        })
        relationships.append({"spdxElementId": "SPDXRef-Package-ARSAS", "relationshipType": "CONTAINS", "relatedSpdxElement": identifier})

    namespace_seed = hashlib.sha256((args.version + args.source_commit + verification_input.hexdigest()).encode("utf-8")).hexdigest()
    document = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"ARSAS-{args.version}-windows-x64",
        "documentNamespace": f"https://github.com/masarray/arsas/sbom/{args.version}/{namespace_seed}",
        "creationInfo": {
            "created": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "creators": ["Tool: ARSAS generate-release-sbom.py", "Person: Ari Sulistiono"],
            "licenseListVersion": "3.25",
        },
        "documentDescribes": ["SPDXRef-Package-ARSAS"],
        "packages": [{
            "name": "ARSAS",
            "SPDXID": "SPDXRef-Package-ARSAS",
            "versionInfo": args.version,
            "downloadLocation": f"https://github.com/masarray/arsas/releases/tag/v{args.version}",
            "filesAnalyzed": True,
            "packageVerificationCode": {"packageVerificationCodeValue": verification_input.hexdigest()},
            "licenseConcluded": "GPL-3.0-or-later",
            "licenseDeclared": "GPL-3.0-or-later",
            "copyrightText": "Copyright (C) 2026 Ari Sulistiono",
            "externalRefs": [{
                "referenceCategory": "PERSISTENT-ID",
                "referenceType": "gitoid",
                "referenceLocator": f"git:{args.source_commit.lower()}",
            }],
        }],
        "files": file_entries,
        "relationships": relationships,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Generated SPDX 2.3 SBOM with {len(files)} files: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
