# Iran Drug Shortage DB — MVP

An automated, auditable pipeline for collecting Iranian drug-shortage signals and preserving their history.

## MVP sources

- **MedUnited RSS** — discovery layer for Iranian pharmaceutical news.
- **Doshanbehaye Darouei** — direct HTML monitoring fallback.
- **IFDANA** — official Food and Drug Administration news site (`ifdana.fda.gov.ir`), monitored directly as a primary official source.

The system intentionally stores the original URL and source for every signal. A news item is a *signal*, not proof of a national shortage; downstream verification can promote signals into verified shortage events.

## Pipeline

`source -> collect -> shortage filter -> basic drug-name extraction -> deduplicate -> SQLite history`

GitHub Actions runs the collector every 6 hours and commits database changes.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
iran-shortages run
iran-shortages search سوتالول
```

## Data model

Each signal stores: title, URL, source, publication time, extracted drug name, status, country, source kind, first-seen and last-seen timestamps, plus a deterministic fingerprint for deduplication.

## Why SQLite first?

For the MVP it makes the whole project portable and lets GitHub Actions preserve a historical dataset without infrastructure. When volume grows, the same model can move to PostgreSQL and expose a REST/search API.

## Next engineering steps

1. Replace the generic IFDANA HTML parsing with a site-specific adapter once its current DOM is profiled.
2. Add the official IFDANA Telegram channel as a resilient secondary discovery path.
3. Add article-page extraction and source-of-origin resolution.
4. Add a verified-event table distinct from raw signals.
5. Add Persian/Latin drug normalization using a curated drug dictionary.
6. Add dashboard/API and notifications for new verified shortages.
7. Investigate TTAC lawful/public endpoints separately; do not make the MVP depend on undocumented private APIs.
