# Deployment Guide

This guide explains how to run JournalFit Studio locally, through Docker, or on Streamlit Community Cloud.

## Local installation

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

## Streamlit Community Cloud

Use the following deployment settings:

```text
Repository: dr-alok-tiwari/journalfit-studio
Branch: main
Main file path: app.py
```

Public demo URL:

```text
https://journalfit-studio-by-dr-alok-tiwari.streamlit.app/
```

## Metadata files

The app supports journal metadata in these formats:

```text
.csv
.xlsx
.xls
```

The repository includes:

```text
data/sample_journal_metadata.csv
```

This sample is detected automatically on Streamlit Cloud. For real use, replace it with verified journal metadata or upload metadata from the sidebar.

## Docker installation

```bash
docker compose up --build
```

Open:

```text
http://localhost:8501
```

Run in background:

```bash
docker compose up -d --build
```

Stop:

```bash
docker compose down
```

View logs:

```bash
docker compose logs -f
```

## Production considerations

For wider use, consider HTTPS, authentication, access control, a clear privacy policy for manuscript uploads, a file-retention policy, metadata refresh workflows, accessibility testing, and a support channel.

For confidential manuscripts, local or institution-hosted deployment is preferred unless the hosted environment has an approved privacy policy.
