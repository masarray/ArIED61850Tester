# Third-Party Notices

ArIED 61850 is distributed under `GPL-3.0-or-later`. Its licensing does not change the license of ARIEC61850 or any third-party package, tool, standard, sample, font, image, or asset. Each component remains subject to its own license and attribution requirements.

## ARIEC61850 engine

ArIED references the separately maintained ARIEC61850 source project at build time. Distributed combined builds must comply with the license and notices of the exact ARIEC61850 revision that is packaged. The application repository does not replace, relicense, or conceal the engine.

## External IEC 61850 protocol stacks

No source code, binary, header, generated binding, wrapper, example, test, or API layer from libiec61850 or any other external IEC 61850 protocol stack is included, linked, or directly required by this application repository.

ArIED is not a port, fork, wrapper, derivative, drop-in replacement, or commercially licensed edition of libiec61850. `libiec61850`, `MZ Automation`, and related names belong to their respective owners. ArIED is not affiliated with, sponsored by, certified by, or endorsed by MZ Automation.

## Proprietary IEC 61850 engineering tools

No executable, library, manual, brochure, help file, screenshot, icon, logo, product photo, report template, text, UI resource, database, capture, or extracted asset from OMICRON products or other proprietary IEC 61850 engineering tools is included in this repository or release package.

Commercial products may be used separately by lawful licensees for black-box interoperability testing. This does not make them application dependencies and does not authorize copying their software, documentation, visual design, reports, resources, or confidential data.

`OMICRON`, `IEDScout`, `SVScout`, `StationScout`, and other third-party product names and marks belong to their respective owners. ArIED 61850 is not affiliated with, sponsored by, certified by, or endorsed by OMICRON electronics GmbH.

## Assets and releases

All application icons, screenshots, illustrations, UI resources, and marketing images included in a release must be project-owned or separately licensed for that use. Screenshots must be generated from ArIED itself using synthetic or sanitized data.

Before every public or commercial release:

1. review the exact ARIEC61850 engine revision and its dependency graph;
2. run `scripts/verify-source-clean.ps1`;
3. inspect the portable archive for unexpected binaries, captures, manuals, logs, screenshots, or customer data;
4. preserve required license and attribution documents; and
5. confirm compliance with `docs/CLEAN_ROOM_AND_INTEROPERABILITY_POLICY.md`.
