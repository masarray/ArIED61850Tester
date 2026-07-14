from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = os.environ.get("GITHUB_REPOSITORY", "masarray/ArIED61850Tester")
OWNER = "Mas Ari / masarray"
OWNER_LOGIN = "masarray"
EFFECTIVE_DATE = "2026-07-14"
APACHE_SHA = os.environ.get("APACHE_BASE_SHA", "0df1007d9538b978edba67218136bc5c4f8019ad")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig") if path.exists() else ""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True, encoding="utf-8", errors="replace").strip()


def replace_section(text: str, heading: str, body: str) -> str:
    pattern = re.compile(rf"(?ms)^## {re.escape(heading)}\s*\n.*?(?=^## |\Z)")
    replacement = f"## {heading}\n\n{body.strip()}\n\n"
    return pattern.sub(replacement, text, count=1) if pattern.search(text) else text.rstrip() + "\n\n" + replacement


def audit_repository() -> dict:
    authors = sorted(set(run("git", "log", "--format=%aN <%aE>").splitlines()), key=str.lower)
    trailers = run("git", "log", "--format=%B").splitlines()
    coauthors = sorted({line.strip() for line in trailers if line.lower().startswith("co-authored-by:")}, key=str.lower)
    pr_authors: list[str] = []
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        for page in range(1, 11):
            request = urllib.request.Request(
                f"https://api.github.com/repos/{REPO}/pulls?state=all&per_page=100&page={page}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "ArIED-license-audit/1.0",
                },
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                items = json.loads(response.read().decode("utf-8"))
            if not items:
                break
            pr_authors.extend(item.get("user", {}).get("login", "") for item in items)
            if len(items) < 100:
                break
    pr_authors = sorted(set(value for value in pr_authors if value), key=str.lower)
    external = [value for value in pr_authors if value.lower() != OWNER_LOGIN and "bot" not in value.lower() and "dependabot" not in value.lower()]

    package_refs: list[str] = []
    pattern = re.compile(r'<PackageReference\s+Include="([^"]+)"(?:\s+Version="([^"]+)")?', re.I)
    for project in ROOT.rglob("*.csproj"):
        for name, version in pattern.findall(read(project)):
            package_refs.append(f"{name} {version or '(version inherited)'} — `{project.relative_to(ROOT).as_posix()}`")

    binary_exts = {".dll", ".exe", ".pdb", ".so", ".dylib", ".jar", ".zip", ".7z", ".pcap", ".pcapng"}
    binaries = sorted(path for path in run("git", "ls-files").splitlines() if Path(path).suffix.lower() in binary_exts)
    return {
        "commits": run("git", "rev-list", "--count", "HEAD"),
        "authors": authors,
        "coauthors": coauthors,
        "pr_authors": pr_authors,
        "external": external,
        "packages": sorted(set(package_refs), key=str.lower),
        "binaries": binaries,
    }


def update_readme() -> None:
    path = ROOT / "README.md"
    text = read(path)
    banner = (
        "> **Licensing:** the public community edition is `GPL-3.0-or-later`. "
        "A separate commercial license is available for proprietary integration, OEM/white-label distribution, "
        "and contractual engineering support. See [docs/LICENSING.md](docs/LICENSING.md)."
    )
    if "**Licensing:** the public community edition" not in text:
        index = text.find("\n## ")
        text = text[:index].rstrip() + "\n\n" + banner + "\n" + text[index:] if index >= 0 else text.rstrip() + "\n\n" + banner + "\n"
    body = f"""
The public community edition is licensed under the **GNU General Public License v3.0 or later** (`GPL-3.0-or-later`). See [LICENSE](LICENSE).

A separate negotiated commercial license is available for proprietary integration, OEM/white-label distribution, closed-source redistribution, warranty, maintenance, priority support, training, and engineering services. See [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md).

Names, logos, icons, and official-release branding are not granted under the software license. See [TRADEMARK.md](TRADEMARK.md).

Revisions through `{APACHE_SHA}` remain available under Apache-2.0 on branch `archive/apache-2.0-final`. The former license is preserved in [LICENSE-APACHE-2.0](LICENSE-APACHE-2.0).
"""
    text = replace_section(text, "License", body)
    write(path, text)


def update_project() -> None:
    path = ROOT / "ArIED61850Tester.csproj"
    text = read(path).replace("<PackageLicenseExpression>Apache-2.0</PackageLicenseExpression>", "<PackageLicenseExpression>GPL-3.0-or-later</PackageLicenseExpression>")
    if "<Copyright>" not in text:
        text = text.replace("    <Authors>Mas Ari / masarray</Authors>", "    <Authors>Mas Ari / masarray</Authors>\n    <Copyright>Copyright (C) 2026 Mas Ari / masarray</Copyright>")
    write(path, text)


def update_packaging() -> None:
    path = ROOT / "scripts" / "publish-windows-portable.ps1"
    text = read(path)
    marker = "# ARIED_LEGAL_FILES"
    if marker not in text:
        snippet = r'''
# ARIED_LEGAL_FILES: include licensing and attribution documents in every distributed package.
$legalFiles = @("LICENSE", "LICENSE-APACHE-2.0", "COMMERCIAL-LICENSE.md", "TRADEMARK.md", "COPYRIGHT.md", "THIRD_PARTY_NOTICES.md", "NOTICE")
foreach ($legalFile in $legalFiles) {
    $sourceLegalFile = Join-Path $root $legalFile
    if (Test-Path $sourceLegalFile) {
        Copy-Item $sourceLegalFile (Join-Path $publishDir $legalFile) -Force
    }
}
'''.strip()
        text = text.replace("Compress-Archive", snippet + "\n\nCompress-Archive", 1)
        write(path, text)


def create_legal_documents(audit: dict) -> None:
    write(ROOT / "COMMERCIAL-LICENSE.md", """# Commercial Licensing

ArIED 61850 is publicly available under the GNU General Public License v3.0 or later (`GPL-3.0-or-later`).

A separate negotiated commercial license is available for organizations that need proprietary or closed-source integration, OEM or white-label distribution, redistribution outside GPL obligations for a combined proprietary product, private product branches, warranty, maintenance, priority support, training, or engineering services.

This document is an invitation to discuss commercial terms. It is not itself a commercial license and grants no additional rights.

Contact the project owner through the `masarray` GitHub profile. Do not post confidential commercial or substation information in a public issue.

Commercial licensing can cover only rights controlled by the relevant copyright holder. The ARIEC61850 engine and all third-party components remain subject to their applicable licenses.
""")

    write(ROOT / "TRADEMARK.md", """# Trademark and Official Branding Policy

The software license does not grant permission to use the **ArIED 61850**, **ARIEC61850**, or related names, logos, icons, official-release badges, and branding in a way that suggests sponsorship, certification, approval, or official status.

Truthful references such as “based on ArIED 61850”, links to the official repository, and unmodified screenshots used for review or education are permitted. Modified distributions must use a distinct name and visual identity unless written permission is obtained.

Permission is required for OEM/white-label branding, use of official icons as a modified product's primary identity, or claims such as “official”, “certified”, or “approved”. Statutory fair use and nominative use rights are not restricted.
""")

    write(ROOT / "COPYRIGHT.md", f"""# Copyright and Provenance

Primary project copyright notice:

> Copyright (C) 2026 {OWNER}

Git history is the detailed record of authorship. Third-party dependencies, assets, and separately attributed material remain owned by their respective copyright holders.

The repository audit performed on {EFFECTIVE_DATE} found {audit['commits']} commit(s). Human pull-request activity returned by GitHub is documented in `docs/LICENSE_AUDIT_{EFFECTIVE_DATE}.md`.

This repository audit cannot determine the effect of employment agreements, invention-assignment clauses, customer contracts, confidential information, employer equipment, or off-repository collaboration. Those items require separate review before relying on commercial enforcement.
""")

    write(ROOT / "CONTRIBUTOR-LICENSE-AGREEMENT.md", """# Contributor License Agreement

By submitting a contribution and affirmatively agreeing in the pull request, the contributor represents that they have the legal right and, where necessary, employer authorization to submit it; retains ownership; and grants Mas Ari / masarray and the project a worldwide, non-exclusive, royalty-free, perpetual, irrevocable license to use, modify, sublicense, relicense, and distribute the contribution under GPL-compatible open-source terms and separate commercial terms.

The contributor also grants a corresponding patent license for patent claims necessarily infringed by the submitted contribution. Contributions are provided without warranty unless separately agreed in writing.

Do not submit confidential, employer-owned, customer-owned, unlawfully copied, or restrictive-license material. Organizations requiring a separately signed agreement should contact the maintainer before submitting code.
""")

    write(ROOT / "DCO.txt", """Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

Everyone is permitted to copy and distribute verbatim copies of this license document, but changing it is not allowed.

Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I have the right to submit it under the open source license indicated in the file; or

(b) The contribution is based upon previous work covered under an appropriate open source license and I have the right under that license to submit it with modifications under the same open source license, unless permitted otherwise; or

(c) The contribution was provided directly to me by another person who certified (a), (b), or (c), and I have not modified it.

(d) I understand and agree that this project and the contribution are public and that a record of the contribution, including the sign-off, is maintained indefinitely and may be redistributed consistently with the project license.
""")

    write(ROOT / "NOTICE", f"""ArIED 61850
Copyright (C) 2026 {OWNER}

Current public license: GNU General Public License v3.0 or later.
Commercial licensing may be obtained separately from the copyright holder.

License transition effective {EFFECTIVE_DATE}:
- Last Apache-2.0 revision: {APACHE_SHA}
- Historical branch: archive/apache-2.0-final
- Historical license copy: LICENSE-APACHE-2.0

The ARIEC61850 engine and third-party components remain governed by their own applicable licenses. See THIRD_PARTY_NOTICES.md.
""")

    write(ROOT / "THIRD_PARTY_NOTICES.md", """# Third-Party Notices

The GPL licensing of ArIED 61850 does not change the license of ARIEC61850 or any third-party package, tool, sample, font, image, or asset. Each component remains subject to its own license and attribution requirements.

Before every public or commercial release, review the resolved dependency graph, bundled engine revision, application assets, and release archive. Preserve all required notices and license copies.
""")

    write(ROOT / "docs" / "LICENSING.md", f"""# Licensing Model

## Community edition

The current public source is licensed under **GNU GPL v3.0 or later** (`GPL-3.0-or-later`). Anyone may run, inspect, modify, and redistribute it subject to the GPL. Distribution of object code must satisfy corresponding-source obligations.

## Commercial licensing and services

A separately negotiated commercial license is available for proprietary integration, OEM/white-label distribution, private product branches, and contractual support. See [COMMERCIAL-LICENSE.md](../COMMERCIAL-LICENSE.md).

## Historical Apache boundary

Revision `{APACHE_SHA}` and earlier public revisions remain available under Apache-2.0 on branch `archive/apache-2.0-final`. Existing Apache rights are not withdrawn. The historical text is in [LICENSE-APACHE-2.0](../LICENSE-APACHE-2.0).

## Engine dependency

ArIED links directly to ARIEC61850. A distributed combined build must use mutually compatible licenses or a separately authorized commercial arrangement for every component.

## Contributions and branding

New contributions require DCO sign-off and agreement to [CONTRIBUTOR-LICENSE-AGREEMENT.md](../CONTRIBUTOR-LICENSE-AGREEMENT.md). Branding is governed separately by [TRADEMARK.md](../TRADEMARK.md).

## Ownership boundary

Repository history cannot resolve employment, invention assignment, customer confidentiality, or off-repository ownership. Obtain professional review before signing a high-value commercial or OEM agreement.
""")

    def items(values: list[str], empty: str) -> str:
        return "\n".join(f"- `{value}`" for value in values) if values else f"- {empty}"

    write(ROOT / "docs" / f"LICENSE_AUDIT_{EFFECTIVE_DATE}.md", f"""# License and Provenance Audit — {EFFECTIVE_DATE}

This is a repository-evidence audit, not a legal opinion.

- Repository: `{REPO}`
- Audited Apache boundary: `{APACHE_SHA}`
- Historical branch: `archive/apache-2.0-final`
- Commit count visible to audit: {audit['commits']}

## Git author identities

{items(audit['authors'], 'None detected')}

## Pull-request author identities

{items(audit['pr_authors'], 'No PR author data returned')}

## External human PR authors

{items(audit['external'], 'No external human PR author detected; automated accounts are excluded')}

## Co-author trailers

{items(audit['coauthors'], 'None detected')}

## Direct NuGet PackageReference entries

{items(audit['packages'], 'No direct PackageReference entries detected')}

## Tracked binary/archive/capture files

{items(audit['binaries'], 'No tracked binary-like files detected by extension')}

## Manual blockers

GitHub cannot establish whether work was created under an employment or invention-assignment obligation, with employer resources, from confidential customer/vendor information, or with unrecorded collaborators. Keep independent-creation evidence and obtain legal review before enterprise licensing.
""")

    write(ROOT / ".github" / "pull_request_template.md", """## Summary

Describe the change and its engineering purpose.

## Validation

- [ ] Build completed
- [ ] Relevant tests completed
- [ ] No confidential SCL/PCAP/customer data included
- [ ] No proprietary or restrictive-license code copied or mechanically translated

## Contribution licensing

- [ ] I have read and agree to `CONTRIBUTOR-LICENSE-AGREEMENT.md`.
- [ ] I have the legal right and, where necessary, employer authorization to submit this contribution.
- [ ] Every commit includes a DCO sign-off (`Signed-off-by: Name <email>`).
""")


def update_contributing() -> None:
    path = ROOT / "CONTRIBUTING.md"
    text = read(path) or "# Contributing\n"
    body = """
The public project is distributed under `GPL-3.0-or-later` and maintains a separate commercial-licensing path. Before merge, contributors must agree to `CONTRIBUTOR-LICENSE-AGREEMENT.md`, sign off each commit under `DCO.txt`, have the legal right and any required employer authorization, and avoid confidential or proprietary material.
"""
    write(path, replace_section(text, "Contribution licensing and provenance", body))


def main() -> None:
    license_path = ROOT / "LICENSE"
    historical = ROOT / "LICENSE-APACHE-2.0"
    if not historical.exists():
        write(historical, read(license_path))

    gpl = Path("/usr/share/common-licenses/GPL-3").read_text(encoding="utf-8")
    if "GNU GENERAL PUBLIC LICENSE" not in gpl or "Version 3, 29 June 2007" not in gpl or len(gpl) < 30000:
        raise RuntimeError("Runner GPL v3 text failed validation.")
    write(license_path, gpl)

    audit = audit_repository()
    update_readme()
    update_project()
    update_packaging()
    create_legal_documents(audit)
    update_contributing()

    failure = ROOT / "LICENSE_TRANSITION_FAILURE.txt"
    if failure.exists():
        failure.unlink()
    Path(__file__).unlink()

    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
