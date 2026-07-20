# ARSAS website measurement

ARSAS uses a lightweight, evidence-oriented measurement pipeline. Runtime analytics are optional and remain disabled when no valid measurement ID is configured. Search and performance reports are private GitHub Actions artifacts; they are not deployed to the public website.

## What is measured

| Question | Source | Output |
|---|---|---|
| Which pages are visited most? | GA4 `page_view` | Page path, views and active users |
| Which queries bring users? | Google Search Console | Query, clicks, impressions, CTR and average position |
| Which download buttons are clicked? | GA4 events | `download_installer`, `download_portable`, `download_checksums` |
| English vs Indonesian traffic | Page registry + GA4/Search Console | Views, search impressions and clicks by site language |
| Which pages have high impressions but low clicks? | Search Console | Pages and queries above the configured opportunity thresholds |
| Are links broken or 404s occurring? | Build-time crawler + deployed probe + GA4 | Missing files/fragments, HTTP failures, 404 paths and referrers |
| Are Core Web Vitals healthy? | Browser PerformanceObserver + PageSpeed/CrUX | LCP, CLS and INP field/lab evidence |

The browser client disables Google advertising signals, does not request ad-personalization signals, respects `Do Not Track`, loads asynchronously and performs no network request when the measurement ID is absent.

## Repository configuration

Configure these **Actions variables**:

- `GA4_MEASUREMENT_ID`: public web stream ID such as `G-XXXXXXXXXX`. Leaving it empty keeps client measurement disabled.
- `GA4_PROPERTY_ID`: numeric GA4 property ID used by the private reporting workflow.
- `GSC_SITE_URL`: the exact verified Search Console property, normally `https://masarray.github.io/arsas/` for a URL-prefix property.
- `PAGESPEED_URLS`: optional comma-separated URLs. When omitted, the workflow checks the English and Indonesian home/download pages plus Smart Reporting and Guides.

Configure these **Actions secrets**:

- `GOOGLE_SERVICE_ACCOUNT_JSON`: JSON for a service account with read-only access to the GA4 property and Search Console property. A `base64:<payload>` value is also accepted.
- `PAGESPEED_API_KEY`: optional PageSpeed Insights API key. The report still attempts the public endpoint when this secret is absent.

Grant the service account Viewer/read access only. It does not need permission to modify analytics, Search Console, releases or the website.

## Workflow behavior

`.github/workflows/site-measurement.yml` runs:

- on relevant pull requests and pushes: deterministic build, measurement contract validation, internal links and fragment validation;
- every Monday at 03:17 UTC, or manually: deployed page checks, official release-asset checks, an intentional 404 probe, GA4 aggregate reports, Search Console reports and PageSpeed/CrUX collection.

Artifacts:

- `site-measurement-quality`: local link and instrumentation evidence, retained for 30 days;
- `site-measurement-<run>`: private Markdown/JSON traffic, search, 404 and Core Web Vitals evidence, retained for 90 days.

The same Markdown report is written to the GitHub Actions job summary.

## Opportunity rules

The initial low-CTR queue is deliberately conservative:

- query opportunity: at least 50 impressions, CTR below 3%, average position 20 or better;
- page opportunity: at least 100 impressions, CTR below 3%, average position 20 or better.

These thresholds are implemented in `scripts/build-site-measurement-report.py` and can be adjusted after several reporting cycles establish a stable baseline.

## Event contract

The local `landing/analytics.js` client emits:

- `page_view`;
- `page_not_found`;
- `language_switch`;
- `download_installer`;
- `download_portable`;
- `download_checksums`;
- `web_vital_lcp`;
- `web_vital_cls`;
- `web_vital_inp`;
- diagnostic `web_vital_ttfb`.

Every event carries page path, page title, site language, content group and stable release version. Download events also carry the official file name, destination URL and visible link text.

## Interpreting Core Web Vitals

Browser RUM events provide continuous observations from measured visits. The scheduled PageSpeed report remains the decision source for field CWV because it uses CrUX data when enough real-user samples exist. When CrUX has insufficient traffic, the report retains Lighthouse lab values and marks field data unavailable instead of inventing a pass/fail result.

## Continuous-improvement loop

1. Review the weekly job summary.
2. Repair any broken internal link or failed 404 behavior immediately.
3. Prioritize high-impression pages with low CTR for title, description and intent alignment.
4. Compare English and Indonesian traffic before deciding which translations to expand.
5. Trace download clicks back to the page that generated them.
6. Investigate repeated 404 paths and add a valid route or redirect where appropriate.
7. Treat poor LCP, CLS or INP as a release-quality issue, then confirm the improvement in the next field-data cycle.
