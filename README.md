# JournalFit Studio

**Journal discovery and fit assistant for researchers**  
Developed by **Dr. Alok Tiwari**, Assistant Professor, Big Data Analytics, Goa Institute of Management, Goa.

Live app: <https://journalfit-ranking-studio-by-dr-alok-tiwari.streamlit.app/>  
Portfolio: <https://dr-alok-tiwari.github.io/>

---

## Purpose

JournalFit Studio helps researchers identify potentially suitable journals from a manuscript title, abstract, keywords, research area, and local journal metadata. It is meant to support journal discovery, scope-fit checking, and submission preparation.

The tool is **not** a journal-ranking authority, acceptance-prediction system, publisher database, or official tool of any ranking or indexing body. Ranking-related fields, when present in a user-provided workbook, are treated as optional context only.

---

## What the tool does

- Reads local or uploaded journal metadata workbooks.
- Accepts a manuscript title, abstract, and keywords.
- Optionally extracts title, abstract, and keywords from PDF, DOCX, or TXT files.
- Computes journal-fit evidence using local TF-IDF similarity, keyword overlap, area alignment, and metadata richness.
- Produces a suitable-journal shortlist with explainable fit signals.
- Creates verification links, downloadable reports, and a next-step prompt for manual review.
- Works without API keys and without scraping publisher or ranking websites.

---

## What the tool does not do

- It does not guarantee acceptance.
- It does not predict editorial decision, review speed, publication speed, APC, indexing status, or journal quality.
- It does not replace official journal websites, author guidelines, aims and scope, editorial policies, or ethics checks.
- It does not act as an official ABDC, ABS/AJG, Scopus, Web of Science, publisher, or indexing-platform service.
- It does not send manuscript content to external language-model APIs by default.

---

## Project structure

```text
journalfit-ranking-studio/
├── app.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── APP_METADATA.json
├── LICENSE
├── README.md
├── data/
│   ├── .gitkeep
│   └── sample_journal_metadata.csv
├── outputs/
│   └── .gitkeep
├── Docs/
│   ├── 01_Handbook.md
│   ├── 02_Responsible_Use.md
│   ├── 03_Data_Template.md
│   ├── 04_Deployment_Guide.md
│   ├── 05_Roadmap_for_Wider_Use.md
│   ├── 06_ABDC_Feedback_Brief.md
│   └── assets/
└── .streamlit/
    └── config.toml
```

---

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows
pip install -r requirements.txt
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

---

## Docker deployment

```bash
docker compose up --build
```

Open:

```text
http://localhost:8501
```

To run in the background:

```bash
docker compose up -d --build
```

To stop:

```bash
docker compose down
```

---

## Data model

Place Excel workbooks inside `data/` or upload them from the sidebar. The app detects common journal metadata columns, including:

```text
journal_title, title, journal name, source title
publisher
issn, eissn
field, subject area, research area
for_code, FoR
abdc_rating, ajg_2024, ajg_2021
citescore_rank, snip_rank, sjr_rank, jif_rank
official_url, submission_url
aims_scope, preferred_methods, typical_topics, editorial_notes
```

A sample metadata file is available at:

```text
data/sample_journal_metadata.csv
```

For production use, convert the CSV template into a curated Excel workbook or maintain it as a local enrichment file named:

```text
data/journal_enrichment.csv
```

---

## Recommended workflow

1. Add or upload a journal metadata workbook.
2. Paste the manuscript title, abstract, and keywords.
3. Run journal discovery.
4. Review the shortlist and explanation panel.
5. Visit official journal websites and verify final suitability.
6. Export the report and shortlist for your records.
7. Improve the local metadata file with verified aims, scope, URLs, and editorial notes.

---

## Responsible-use note

Journal-fit scores are decision-support signals. They should not be treated as acceptance probabilities, quality judgements, or mechanical submission instructions. Researchers must verify all final details using official journal sources.

---

## Contributor recognition

This tool was designed and developed by **Dr. Alok Tiwari** as an independent research-support contribution for improving journal discovery, journal-fit literacy, and responsible submission preparation among faculty members, PhD scholars, early-career researchers, and research offices.

---

## Suggested citation

```text
Tiwari, A. (2026). JournalFit Studio: A local-first journal discovery and fit assistant for researchers. GitHub. https://github.com/dr-alok-tiwari/journalfit-ranking-studio
```

---

## Documentation

See the `Docs/` folder for the handbook, responsible-use guide, data template, deployment guide, roadmap, and reviewer feedback brief.
