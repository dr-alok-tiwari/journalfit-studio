# Journal Metadata Template

JournalFit Studio works best with a curated metadata file. The file may be in Excel or CSV format. The app detects many common column names automatically, but the following names are recommended for clarity.

## Recommended columns

| Column | Purpose |
|---|---|
| journal_title | Official journal title. |
| publisher | Publisher name. |
| issn | Print ISSN. |
| eissn | Electronic ISSN. |
| field | Subject area or discipline. |
| for_code | Optional field-of-research code. |
| official_url | Official journal homepage. |
| submission_url | Official author guidelines or submission page. |
| aims_scope | Aims and scope summary from official source. |
| preferred_methods | Typical methods, article types, or methodological orientation. |
| typical_topics | Main topics covered by the journal. |
| editorial_notes | Local notes from verified review. |
| verified_url_status | Example: verified, pending, search-only. |
| abdc_rating | Optional contextual field only. |
| ajg_2024 | Optional contextual field only. |

## Metadata-quality tips

- Prefer official journal websites over third-party summaries.
- Record the date when metadata was checked.
- Avoid unverified submission URLs.
- Separate official URLs from search links.
- Use clear local notes when a journal seems broad, narrow, interdisciplinary, or method-specific.
- Refresh metadata periodically.

## Example row

```csv
journal_title,publisher,issn,eissn,field,official_url,submission_url,aims_scope,preferred_methods,typical_topics,editorial_notes,verified_url_status
Sample Journal of Management Analytics,Example Publisher,1234-5678,8765-4321,Information Systems / Analytics,https://example.org/journal,https://example.org/journal/submit,"Publishes work on analytics, data-driven decision-making, and digital transformation.","Empirical, computational, design science, review","business analytics; digital platforms; responsible technology","Demo row only; replace with verified data.",demo-only
```
