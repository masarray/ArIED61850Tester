#!/usr/bin/env python3
"""Validate ARSAS primary release and explicit backfill supply-chain contracts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def main() -> int:
    errors: list[str] = []
    primary = (WORKFLOWS / "release-windows.yml").read_text(encoding="utf-8")
    backfill = (WORKFLOWS / "release-supply-chain.yml").read_text(encoding="utf-8")

    primary_contract = (
        "id-token: write", "attestations: write", "Setup Python 3.12",
        "generate-release-sbom.py", "ARSAS-Windows-x64-SBOM.spdx.json",
        "actions/attest@v4", "subject-path: ArIED61850Tester/dist/ARSAS-Windows-x64-Setup.exe",
        "sbom-path: ArIED61850Tester/dist/ARSAS-Windows-x64-SBOM.spdx.json",
        "supplyChain = [ordered]@{", "attestationWorkflow = \"release-windows.yml\"",
    )
    for value in primary_contract:
        if value not in primary:
            errors.append(f"release-windows.yml missing primary supply-chain contract: {value}")

    backfill_contract = (
        "name: Backfill ARSAS release supply chain", "workflow_dispatch:",
        "sha256sum --check", "git rev-parse HEAD", "generate-release-sbom.py",
        "actions/attest@v4", "post-publication evidence does not retroactively describe another tag",
    )
    for value in backfill_contract:
        if value not in backfill:
            errors.append(f"release-supply-chain.yml missing backfill contract: {value}")
    if "\n  release:" in backfill:
        errors.append("release-supply-chain.yml must not auto-run after the primary release workflow")
    if "github.event.release" in backfill:
        errors.append("release-supply-chain.yml must use an explicit tag input only")

    if errors:
        print("ARSAS supply-chain workflow validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("ARSAS supply-chain workflow validation passed: primary build attestations and explicit checksum-verified backfill are separated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
