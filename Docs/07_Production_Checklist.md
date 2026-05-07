# Production Readiness Checklist

Use this checklist before sharing JournalFit Studio with external users.

## Interface

- [ ] Confirm desktop layout displays the hero section, sidebar, input fields, metrics, and recommendation table correctly.
- [ ] Confirm mobile layout stacks columns cleanly and keeps buttons visible.
- [ ] Confirm all disclaimers are visible before and after recommendations.
- [ ] Confirm contributor attribution appears in the footer.
- [ ] Confirm external links open correctly.

## Data

- [ ] Add verified journal metadata to `data/`.
- [ ] Remove demo-only rows before real use.
- [ ] Confirm official URLs and submission URLs are current.
- [ ] Record metadata source and verification date.
- [ ] Maintain `journal_enrichment.csv` for scope and topic enrichment.

## Privacy

- [ ] Decide whether the deployment permits confidential manuscript uploads.
- [ ] Publish a privacy and retention note for hosted use.
- [ ] Prefer local or institution-hosted deployment for confidential work.
- [ ] Avoid retaining manuscript text unless explicitly required and approved.

## Technical

- [ ] Run `python smoke_test.py`.
- [ ] Run `python -m py_compile app.py`.
- [ ] Test `streamlit run app.py` locally.
- [ ] Test `docker compose up --build`.
- [ ] Confirm `data/` and `outputs/` mount correctly in Docker.
- [ ] Check logs in `outputs/` if errors occur.

## Responsible use

- [ ] Confirm users understand that this is not an acceptance-prediction system.
- [ ] Confirm users understand that ranking fields are optional context only.
- [ ] Confirm users manually verify official journal information before submission.
- [ ] Confirm the tool is not used for promotion, hiring, or performance evaluation.
