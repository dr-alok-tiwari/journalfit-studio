# Changelog

## v5.0.0 — 2026-07-16

- Rebuilt the Streamlit interface around a guided manuscript-to-shortlist workflow.
- Added manuscript extraction from PDF, DOCX, and TXT with editable extracted content.
- Added database-quality metrics, explicit demo-data warnings, and a searchable journal explorer.
- Added interactive shortlist, evidence charts, journal cards, comparison, and report/CSV exports.
- Moved matching, parsing, metadata normalization, and reporting into `journalfit_core.py`.
- Corrected semantic scoring so a weak candidate set does not automatically produce a perfect top match.
- Added absolute and relative semantic evidence, metadata-confidence labels, configurable normalized weights, and stale-result invalidation.
- Improved metadata merging, file-change-aware caching, URL normalization, error handling, and manuscript title detection.
- Added six automated unit tests and strengthened GitHub Actions CI.
- Constrained dependency major versions and refreshed Streamlit security/theme settings for reliable Community Cloud deployment.

## v4.0.0

- Reframed the app from a ranking-focused workflow to a journal discovery and fit assistant.
- Added a new vibrant, responsive Streamlit interface for desktop and mobile screens.
- Added clearer responsible-use language across the app and documentation.
- Added explanation of journal-fit score components: semantic fit, keyword overlap, area alignment, and metadata richness.
- Added Dockerfile and Docker Compose support.
- Added `Docs/` folder with handbook, responsible-use guide, data template, deployment guide, roadmap, feedback brief, and production checklist.
- Added sample metadata template.
- Added GitHub Actions smoke-test workflow.
- Added contributor recognition and non-affiliation statement.
