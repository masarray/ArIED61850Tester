# Clean-Room and Interoperability Policy

ArIED 61850 is an independently designed Windows application built on the separately maintained ARIEC61850 engine. This policy prevents copyright, license, trade-secret, trademark, and contractual contamination from external IEC 61850 stacks and proprietary engineering products.

## Independent implementation rule

Application code, services, models, documentation, tests, visual assets, and workflows must be written independently. Implementation may rely on public IEC/ISO protocol requirements, owner-created design notes, synthetic SCL, project-owned captures and encoders, and vendor-neutral black-box interoperability facts obtained through lawful use.

The application must not copy, translate, mechanically port, wrap, link, or adapt source code, generated bindings, examples, tests, comments, API structures, naming schemes, or binaries from libiec61850 or any other external IEC 61850 protocol stack.

## Proprietary tool rule

Proprietary IEC 61850 tools may be used only as lawfully licensed black-box interoperability participants in an isolated laboratory. Developers must not:

- decompile, disassemble, patch, inspect memory, extract resources or databases, or bypass technical restrictions;
- copy manuals, help text, screenshots, icons, logos, product photos, report templates, wording, internal files, or captured UI assets;
- reproduce the distinctive selection, arrangement, interaction flow, artwork, color system, typography, or overall presentation of another product;
- commit raw proprietary-client captures as permanent implementation fixtures;
- imply affiliation, sponsorship, endorsement, certification, partnership, or compatibility approval by the product owner.

A protocol behavior observed with an external client must be reduced to a vendor-neutral standards fact and independently reconstructed using ARIEC61850's own encoders or a public protocol grammar.

## Independent user-interface rule

Common engineering functions such as an IED tree, signal table, event list, report monitor, waveform plot, phasor diagram, SCL view, command panel, or diagnostic log may be implemented because they serve functional engineering needs. Their particular visual composition and expressive details must be independently designed.

Do not use third-party screenshots as design specifications or imitate proprietary window layouts, ribbon structures, pane arrangements, icons, labels, report appearance, or marketing presentation. Project screenshots must be produced only from ArIED itself using synthetic or sanitized data.

## Data and fixture provenance

Repository and release content must not contain:

- customer or employer confidential SCL, PCAP, credentials, station names, serial numbers, screenshots, or project evidence;
- external protocol-stack source, binaries, headers, wrappers, or copied tests;
- proprietary software executables, manuals, brochures, help files, screenshots, icons, logos, fonts, report templates, or extracted resources;
- generated build outputs except in controlled release artifacts;
- wording that identifies a proprietary product as the source of implementation behavior.

All committed fixtures must be synthetic, project-owned, emitted by ARIEC61850, or manually reconstructed from a public protocol grammar.

## Trademark and public wording

Third-party names may be used only where factually necessary in reviewed legal, provenance, or interoperability records. Product and company names remain property of their respective owners.

Recommended statement:

> ArIED 61850 and ARIEC61850 are independently developed, vendor-neutral engineering tools. They are not affiliated with, sponsored by, certified by, or endorsed by MZ Automation, OMICRON, or any other IEC 61850 tool vendor.

## Review requirement

Any change involving an external interoperability observation, imported capture, product-specific workaround, third-party asset, or vendor-named test requires explicit provenance review before merge. When lawful origin and independent derivation cannot be demonstrated, the material must not enter the repository or release package.
