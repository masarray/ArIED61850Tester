# Per-card interoperable SCL export

Each IED card exposes a **Save SCL** action after ArIED has a complete typed model.

## Supported sources

- **Opened SCL design model** — Edition 2 uses the engine-owned generic interoperability converter against the original source file and the IED represented by that card. Edition 1 is rebuilt from the typed `SclWorkspace.DesignModel` using the schema-aware exporter.
- **Live MMS discovery** — Edition 2 and Edition 1 are generated from the last successful full IP discovery model. A saved signal cache alone is not treated as complete engineering evidence; use **Re-scan** to capture a full model first.

## Edition choices

- **Edition 2 (Schema V3.1)** → `.iid`
- **Edition 1 (Schema V1.6)** → `.icd`

The chosen profile controls root schema metadata, supported ReportControl fields, Services declarations, and default file extension.

## Companion evidence

The ARIEC61850 export services write the SCL file together with a JSON report and a Markdown summary. The schema-aware discovery exporter also records excluded-attribute evidence where applicable. Conversion findings and export warnings remain visible in ArIED Diagnostics and in the companion report.

## Scope

The output reflects the typed model available from the opened file or the latest successful MMS discovery. Engineering information that cannot be obtained through the source model is not invented. Export success is interoperability evidence, not a claim of formal IEC 61850 conformance or operational approval.
