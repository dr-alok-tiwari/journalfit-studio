# JournalFit Studio

**Explainable, local-first journal discovery for researchers**  
Developed by **Dr. Alok Tiwari**, Assistant Professor, Big Data Analytics, Goa Institute of Management, Goa.

- Live app: https://journalfit-studio-by-dr-alok-tiwari.streamlit.app/
- Portfolio: https://dr-alok-tiwari.github.io/

## What changed in v5

- A redesigned responsive interface with a guided manuscript-to-shortlist workflow.
- PDF, DOCX, and TXT extraction with editable title, abstract, and keywords.
- Transparent scoring with semantic, keyword, research-area, and metadata-quality evidence.
- Shortlist table, score visualisation, journal cards, side-by-side comparison, and exports.
- A searchable journal-database explorer and visible data-quality indicators.
- Clear demo-data warnings so sample records cannot be mistaken for production recommendations.
- Modular core logic and automated tests.
- Streamlit Community Cloud-safe dependency constraints.

## Important limitation

The bundled `data/sample_journal_metadata.csv` contains **demonstration records only**. Upload or add a verified journal metadata file before making a real submission decision. Journal-fit scores are not acceptance probabilities, journal-quality ratings, or substitutes for official journal information.

## Project structure

```text
journalfit-studio/
├── app.py
├── journalfit_core.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── APP_METADATA.json
├── data/
│   └── sample_journal_metadata.csv
├── tests/
│   └── test_core.py
└── .streamlit/
    └── config.toml
```

## Run locally

Python 3.11 or 3.12 is recommended.

```bash
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows
pip install -r requirements.txt
streamlit run app.py
```

## Run tests

```bash
pip install pytest
pytest -q
```

## Deploy on Streamlit Community Cloud

Use:

```text
Repository: dr-alok-tiwari/journalfit-studio
Branch: main (after the upgrade pull request is merged)
Main file path: app.py
Python: 3.11 or 3.12
```

The repository includes `requirements.txt` in the root, requires no secrets, and requires no external Linux packages. If the existing deployment uses an incompatible Python version, redeploy it from Streamlit Community Cloud's advanced settings with Python 3.11 or 3.12.

## Metadata format

CSV, XLSX, and XLS are supported. Common recognized columns include:

```text
journal_title / journal name / source title
publisher
issn / eissn
field / subject area / research area
abdc_rating / ajg_2024
official_url / submission_url
aims_scope / preferred_methods / typical_topics / editorial_notes
verification_status
```

For production data, record the source and verification status for rankings, URLs, indexing, fees, and other time-sensitive claims.

## Scoring model

The default score combines:

- semantic evidence (58%)
- keyword overlap (22%)
- metadata completeness (10%)
- research-area alignment (10%)

Weights are adjustable in the interface and normalized automatically. Semantic evidence blends absolute TF-IDF cosine similarity with relative position in the currently filtered candidate set. This avoids presenting the strongest candidate as a perfect match when all candidates are weak.

## Responsible use

Always verify the current aims and scope, accepted article types, ranking/indexing, fees, ethics, turnaround claims, and author guidelines on official sources before submission.

## Suggested citation

```text
Tiwari, A. (2026). JournalFit Studio: An explainable local-first journal discovery and fit assistant for researchers. GitHub. https://github.com/dr-alok-tiwari/journalfit-studio
```
