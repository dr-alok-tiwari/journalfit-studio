# JournalFit Studio

**Journal discovery and fit assistant for researchers**  
Developed by **Dr. Alok Tiwari**, Assistant Professor, Big Data Analytics, Goa Institute of Management, Goa.

Live app: https://journalfit-studio-by-dr-alok-tiwari.streamlit.app/  
Portfolio: https://dr-alok-tiwari.github.io/

---

## Purpose

JournalFit Studio helps researchers identify potentially suitable journals from a manuscript title, abstract, keywords, research area, and local journal metadata.

It is a decision-support tool, not a journal-ranking authority, acceptance-prediction system, publisher database, or official tool of any ranking or indexing body.

---

## What the tool does

- Reads local or uploaded journal metadata in CSV, XLSX, or XLS format.
- Accepts a manuscript title, abstract, and keywords.
- Optionally extracts title, abstract, and keywords from PDF, DOCX, or TXT files.
- Computes journal-fit evidence using local TF-IDF similarity, keyword overlap, area alignment, and metadata richness.
- Produces an explainable journal shortlist.
- Creates verification links and downloadable reports.
- Works without API keys and without scraping publisher or ranking websites.

---

## Project structure

```text
journalfit-studio/
├── app.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── APP_METADATA.json
├── README.md
├── data/
│   ├── .gitkeep
│   └── sample_journal_metadata.csv
├── outputs/
│   └── .gitkeep
├── Docs/
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

## Streamlit Cloud deployment

Use these settings:

```text
Repository: dr-alok-tiwari/journalfit-studio
Branch: main
Main file path: app.py
```

The repository now includes a CSV sample metadata file that the app can detect automatically, so the app opens with usable demo metadata even when no Excel workbook is uploaded.

---

## Metadata format

The app supports CSV, XLSX, and XLS metadata files. Common supported columns include:

```text
journal_title, title, journal name, source title
publisher
issn, eissn
field, subject area, research area
abdc_rating, ajg_2024, ajg_2021
official_url, submission_url
aims_scope, preferred_methods, typical_topics, editorial_notes
```

A sample file is available at:

```text
data/sample_journal_metadata.csv
```

For production use, replace the demo rows with verified journal metadata.

---

## Responsible-use note

Journal-fit scores are decision-support signals. They should not be treated as acceptance probabilities, quality judgments, or mechanical submission instructions. Researchers must verify final details using official journal sources.

---

## Suggested citation

```text
Tiwari, A. (2026). JournalFit Studio: A local-first journal discovery and fit assistant for researchers. GitHub. https://github.com/dr-alok-tiwari/journalfit-studio
```
