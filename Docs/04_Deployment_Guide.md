# Deployment Guide

This guide explains how to run JournalFit Studio locally or through Docker.

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

For wider use, consider:

- HTTPS and reverse proxy configuration.
- Institutional authentication or SSO.
- Role-based access.
- Clear privacy policy for manuscript uploads.
- Server-side file-retention policy.
- Audit logging for metadata changes.
- Scheduled metadata review and data-refresh workflows.
- Accessibility testing on desktop and mobile.
- User-support and issue-reporting channel.

## Streamlit Community Cloud

The public demo URL is:

```text
https://journalfit-studio-by-dr-alok-tiwari.streamlit.app/
```

For confidential manuscripts, local or institution-hosted deployment is preferred unless the hosted environment has an approved privacy policy.
