"""
JournalFit Studio
Journal discovery and fit assistant for researchers.

Purpose
-------
This Streamlit application helps researchers shortlist potentially suitable journals
from locally provided journal metadata and a manuscript title/abstract/keywords.
It is a journal-fit discovery tool, not a ranking authority and not an acceptance
prediction system.

Run locally:
    streamlit run app.py

Run with Docker:
    docker compose up --build
"""

from __future__ import annotations

import html
import io
import os
import re
import textwrap
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None

try:
    import docx
except Exception:  # pragma: no cover
    docx = None


APP_NAME = "JournalFit Studio"
APP_SUBTITLE = "Journal discovery and fit assistant"
APP_VERSION = "4.0.0"
APP_URL = "https://journalfit-studio-by-dr-alok-tiwari.streamlit.app/"
GITHUB_URL = "https://github.com/dr-alok-tiwari/journalfit-studio"
PORTFOLIO_URL = "https://dr-alok-tiwari.github.io/"
AUTHOR = "Dr. Alok Tiwari"

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
ENRICHMENT_FILE = DATA_DIR / "journal_enrichment.csv"
ERROR_LOG_FILE = OUTPUT_DIR / "journalfit_error.log"

DEFAULT_WORKBOOK_PRIORITY = [
    "journal_metadata.xlsx",
    "ABS_Submission_Links.xlsx",
    "ABDC-Ranking.xlsx",
    "ABDC-JQL-2025-v1-260326.xlsx",
]

CANONICAL_COLUMNS = [
    "journal_title",
    "publisher",
    "issn",
    "eissn",
    "field",
    "for_code",
    "for_label",
    "abdc_rating",
    "ajg_2024",
    "ajg_2021",
    "citescore_rank",
    "snip_rank",
    "sjr_rank",
    "jif_rank",
    "official_url",
    "submission_url",
    "submission_link_type",
    "verified_url_status",
    "aims_scope",
    "preferred_methods",
    "typical_topics",
    "editorial_notes",
    "source_file",
    "source_sheet",
    "source_kind",
]

COLUMN_ALIASES = {
    "journal_title": [
        "journal title", "title", "journal", "journal name", "source title",
        "publication title", "periodical title", "abdc matched title"
    ],
    "publisher": ["publisher", "publisher name", "abdc publisher", "imprint"],
    "issn": ["issn", "print issn", "p-issn", "issn-l", "abdc issn"],
    "eissn": ["eissn", "issn online", "online issn", "electronic issn", "issnonline", "abdc issnonline"],
    "field": ["field", "discipline", "category", "subject", "subject area", "research area", "abdc field"],
    "for_code": ["for", "for code", "field of research", "anzsrc for", "abdc for"],
    "abdc_rating": ["2025 rating", "abdc rating", "abdc category", "abdc category (2025)", "rating"],
    "ajg_2024": ["ajg 2024", "abs 2024", "cabs 2024", "ajg rating", "abs rating", "academic journal guide 2024"],
    "ajg_2021": ["ajg 2021", "abs 2021", "cabs 2021"],
    "citescore_rank": ["citescore rank", "citescore"],
    "snip_rank": ["snip rank", "snip"],
    "sjr_rank": ["sjr rank", "sjr"],
    "jif_rank": ["jif rank", "jif", "journal impact factor rank"],
    "official_url": ["journal url", "url", "homepage", "official url", "journal website", "website"],
    "submission_url": ["link to submission", "submission link", "submission url", "author guidelines", "submission guidelines", "guide for authors"],
    "submission_link_type": ["submission link type", "link type", "url status"],
    "verified_url_status": ["verified url status", "url verification", "verified", "verification status"],
    "aims_scope": ["aims scope", "aims and scope", "scope", "journal scope", "description", "about journal", "aims"],
    "preferred_methods": ["preferred methods", "methods", "methodological fit", "methodology"],
    "typical_topics": ["typical topics", "topics", "keywords", "journal keywords", "themes"],
    "editorial_notes": ["editorial notes", "notes", "curation notes", "remarks"],
}

FOR_MAP = {
    "3501": "Accounting, Auditing and Accountability",
    "3502": "Banking, Finance and Investment",
    "3503": "Business Systems in Context",
    "3504": "Commercial Services",
    "3505": "Human Resources and Industrial Relations",
    "3506": "Marketing",
    "3507": "Strategy, Management and Organisational Behaviour",
    "3508": "Tourism",
    "3509": "Transportation, Logistics and Supply Chains",
    "3599": "Other Commerce, Management, Tourism and Services",
    "3801": "Applied Economics",
    "3802": "Econometrics",
    "3803": "Economic Theory",
    "3804": "Economics",
    "3899": "Other Economics",
    "4602": "Artificial Intelligence",
    "4609": "Information Systems",
    "4801": "Commercial Law",
}

AREA_KEYWORDS = {
    "Accounting": ["accounting", "audit", "auditing", "financial reporting", "earnings", "disclosure", "tax", "assurance"],
    "Finance": ["finance", "banking", "investment", "asset pricing", "capital market", "risk", "portfolio", "fintech"],
    "Marketing": ["marketing", "consumer", "brand", "retail", "customer", "advertising", "market", "service quality"],
    "Information Systems / Analytics": ["information system", "analytics", "data", "digital", "platform", "algorithm", "artificial intelligence", "machine learning", "information technology", "cyber", "privacy"],
    "Strategy / Governance": ["strategy", "governance", "corporate governance", "regulation", "policy", "board", "responsible", "accountability", "institution", "capability"],
    "HRM / OB": ["human resource", "hrm", "employee", "workplace", "leadership", "team", "organizational behaviour", "motivation", "wellbeing"],
    "Operations / Supply Chain": ["operations", "supply chain", "logistics", "inventory", "quality", "process", "production", "optimization"],
    "Entrepreneurship": ["entrepreneur", "startup", "venture", "innovation", "ecosystem", "small business", "new venture"],
    "Healthcare Management": ["healthcare", "hospital", "patient", "clinical", "health", "medical", "public health", "care"],
    "Economics": ["economics", "econometric", "macroeconomic", "microeconomic", "policy", "welfare", "labour market"],
    "Tourism": ["tourism", "hospitality", "travel", "destination", "hotel", "visitor"],
    "Education / Learning": ["education", "learning", "teaching", "student", "pedagogy", "training", "classroom"],
    "Ethics / Responsible Technology": ["ethics", "fairness", "bias", "trust", "privacy", "governance", "responsible", "accountability", "transparency"],
}

STOPWORDS_EXTRA = {
    "study", "research", "paper", "article", "manuscript", "results", "findings", "using", "based",
    "among", "also", "across", "within", "towards", "approach", "analysis", "model", "models",
    "effect", "effects", "role", "impact", "impacts", "case", "cases", "evidence", "review",
}

RATING_ORDER_ABDC = {"A*": 4, "A": 3, "B": 2, "C": 1}
RATING_ORDER_AJG = {"4*": 5, "4": 4, "3": 3, "2": 2, "1": 1}


@dataclass
class FitWeights:
    semantic: float = 0.58
    keyword: float = 0.22
    area: float = 0.12
    metadata: float = 0.08


def ensure_runtime_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log_exception(context: str, exc: Exception) -> None:
    try:
        ensure_runtime_dirs()
        with ERROR_LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {context}: {type(exc).__name__}: {exc}\n")
    except Exception:
        pass


def clean_text(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_title(value: object) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"^the\s+", "", text)
    text = text.replace("&", "and")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_issn(value: object) -> str:
    text = clean_text(value).upper()
    match = re.search(r"\b\d{4}-?\d{3}[0-9X]\b", text)
    if not match:
        return ""
    raw = match.group(0).replace("-", "")
    return f"{raw[:4]}-{raw[4:]}" if len(raw) == 8 else raw


def normalize_rating(value: object, kind: str) -> str:
    text = clean_text(value).upper().replace(" ", "")
    if kind == "abdc" and text in RATING_ORDER_ABDC:
        return text
    if kind == "ajg" and text in RATING_ORDER_AJG:
        return text
    return clean_text(value)


def tokenize(text: str) -> List[str]:
    text = clean_text(text).lower()
    text = re.sub(r"[^a-z0-9\-\s]", " ", text)
    tokens = [t for t in re.split(r"\s+", text) if len(t) >= 3]
    return [t for t in tokens if t not in STOPWORDS_EXTRA]


def google_search_url(query: str) -> str:
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)


def scholar_search_url(query: str) -> str:
    return "https://scholar.google.com/scholar?q=" + urllib.parse.quote_plus(query)


def safe_link(url: object) -> str:
    text = clean_text(url)
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        return text
    return "https://" + text if "." in text else ""


def workbook_files() -> List[Path]:
    ensure_runtime_dirs()
    files = sorted(DATA_DIR.glob("*.xlsx")) + sorted(DATA_DIR.glob("*.xls"))
    priority = {name: i for i, name in enumerate(DEFAULT_WORKBOOK_PRIORITY)}
    return sorted(files, key=lambda p: (priority.get(p.name, 99), p.name.lower()))


def list_sheets_from_bytes(file_bytes: bytes) -> List[str]:
    try:
        return pd.ExcelFile(io.BytesIO(file_bytes)).sheet_names
    except Exception:
        return []


def detect_column(df: pd.DataFrame, canonical: str) -> Optional[str]:
    aliases = COLUMN_ALIASES.get(canonical, [])
    normalized_cols = {re.sub(r"[^a-z0-9]+", " ", str(c).lower()).strip(): c for c in df.columns}
    for alias in aliases:
        key = re.sub(r"[^a-z0-9]+", " ", alias.lower()).strip()
        if key in normalized_cols:
            return normalized_cols[key]
    for key, original in normalized_cols.items():
        for alias in aliases:
            alias_key = re.sub(r"[^a-z0-9]+", " ", alias.lower()).strip()
            if len(alias_key) >= 4 and (alias_key in key or key in alias_key):
                return original
    return None


def infer_source_kind(filename: str, df: pd.DataFrame) -> str:
    col_text = " ".join(map(str, df.columns)).lower()
    fname = filename.lower()
    if "abs" in fname or "ajg" in fname or "ajg 2024" in col_text:
        return "ABS/AJG context"
    if "abdc" in fname or "2025 rating" in col_text or "abdc category" in col_text:
        return "ABDC context"
    return "Journal metadata"


@st.cache_data(show_spinner=False)
def read_excel_detect_header(file_bytes: bytes, sheet_name: str = "Auto") -> pd.DataFrame:
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        sheet = xl.sheet_names[0] if sheet_name == "Auto" else sheet_name
        preview = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet, header=None, nrows=30)
    except Exception as exc:
        log_exception("read_excel_preview", exc)
        return pd.DataFrame()

    best_header, best_score = 0, -1
    for i in range(len(preview)):
        vals = [clean_text(v).lower() for v in preview.iloc[i].tolist()]
        row_text = " | ".join(vals)
        score = sum(token in row_text for token in ["journal title", "journal", "publisher", "issn", "rating", "ajg", "abdc", "field", "scope", "url"])
        score += min(3, sum(bool(v) for v in vals) // 2)
        if score > best_score:
            best_header, best_score = i, score

    try:
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet, header=best_header)
    except Exception as exc:
        log_exception("read_excel_full", exc)
        return pd.DataFrame()

    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    df.columns = [clean_text(c) for c in df.columns]
    df.attrs["detected_header"] = best_header
    return df.reset_index(drop=True)


def to_canonical(raw_df: pd.DataFrame, source_file: str, source_sheet: str) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS + ["title_key"])

    df = raw_df.copy()
    df.columns = [clean_text(c) for c in df.columns]
    out = pd.DataFrame(index=df.index)

    for col in CANONICAL_COLUMNS:
        if col in {"source_file", "source_sheet", "source_kind", "for_label"}:
            continue
        detected = detect_column(df, col)
        out[col] = df[detected] if detected is not None else ""

    if out.get("journal_title", pd.Series(dtype=str)).map(clean_text).eq("").all():
        for c in df.columns:
            sample = df[c].dropna().astype(str).head(10).str.len().median()
            if pd.notna(sample) and sample > 5:
                out["journal_title"] = df[c]
                break

    for col in out.columns:
        out[col] = out[col].map(clean_text)

    out["journal_title"] = out["journal_title"].map(clean_text)
    out["issn"] = out["issn"].map(normalize_issn)
    out["eissn"] = out["eissn"].map(normalize_issn)
    out["abdc_rating"] = out["abdc_rating"].map(lambda x: normalize_rating(x, "abdc"))
    out["ajg_2024"] = out["ajg_2024"].map(lambda x: normalize_rating(x, "ajg"))
    out["ajg_2021"] = out["ajg_2021"].map(lambda x: normalize_rating(x, "ajg"))
    out["for_code"] = out["for_code"].map(lambda x: re.sub(r"\.0$", "", clean_text(x)))

    def label_for_code(code: str) -> str:
        match = re.search(r"\d{4}", clean_text(code))
        return FOR_MAP.get(match.group(0), f"FoR {match.group(0)}") if match else clean_text(code)

    out["for_label"] = out["for_code"].map(label_for_code)
    out["field"] = out.apply(lambda r: clean_text(r.get("field")) or clean_text(r.get("for_label")), axis=1)
    out["source_file"] = source_file
    out["source_sheet"] = source_sheet
    out["source_kind"] = infer_source_kind(source_file, raw_df)
    out = out[out["journal_title"].astype(str).str.strip().ne("")].copy()
    out["title_key"] = out["journal_title"].map(normalize_title)
    return out


def merge_records(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    if "title_key" not in df.columns:
        df["title_key"] = df["journal_title"].map(normalize_title)
    df["issn_key"] = df.apply(lambda r: clean_text(r.get("issn", "")) or clean_text(r.get("eissn", "")), axis=1)

    merged_rows: List[Dict[str, str]] = []
    used = set()
    for idx, row in df.iterrows():
        if idx in used:
            continue
        mask = pd.Series(False, index=df.index)
        if clean_text(row.get("issn_key")):
            mask |= df["issn_key"].eq(row["issn_key"])
        if clean_text(row.get("title_key")):
            mask |= df["title_key"].eq(row["title_key"])
        subset = df[mask].copy()
        used.update(subset.index.tolist())

        merged: Dict[str, str] = {}
        for col in df.columns:
            values = [clean_text(v) for v in subset[col].tolist() if clean_text(v)]
            if col in {"source_file", "source_sheet", "source_kind"}:
                merged[col] = "; ".join(sorted(set(values)))
            elif col == "abdc_rating":
                ratings = [v for v in values if v in RATING_ORDER_ABDC]
                merged[col] = max(ratings, key=lambda x: RATING_ORDER_ABDC[x]) if ratings else (values[0] if values else "")
            elif col in {"ajg_2024", "ajg_2021"}:
                ratings = [v for v in values if v in RATING_ORDER_AJG]
                merged[col] = max(ratings, key=lambda x: RATING_ORDER_AJG[x]) if ratings else (values[0] if values else "")
            elif col in {"official_url", "submission_url"}:
                verified = [safe_link(v) for v in values if safe_link(v) and "google.com/search" not in safe_link(v).lower()]
                merged[col] = verified[0] if verified else (safe_link(values[0]) if values else "")
            elif col in {"aims_scope", "preferred_methods", "typical_topics", "editorial_notes"}:
                merged[col] = " | ".join(dict.fromkeys(values[:4]))
            else:
                merged[col] = values[0] if values else ""
        merged_rows.append(merged)

    out = pd.DataFrame(merged_rows)
    for col in CANONICAL_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    out["title_key"] = out["journal_title"].map(normalize_title)
    return out


@st.cache_data(show_spinner=False)
def load_local_workbooks(selected_paths: Tuple[str, ...], sheet_choice: str) -> pd.DataFrame:
    frames = []
    for path_str in selected_paths:
        path = Path(path_str)
        if not path.exists():
            continue
        file_bytes = path.read_bytes()
        sheets = list_sheets_from_bytes(file_bytes)
        sheet_names = sheets if sheet_choice == "All sheets" else [sheets[0] if sheet_choice == "Auto" and sheets else sheet_choice]
        for sheet in sheet_names:
            try:
                raw = read_excel_detect_header(file_bytes, sheet)
                canonical = to_canonical(raw, path.name, sheet)
                if not canonical.empty:
                    frames.append(canonical)
            except Exception as exc:
                log_exception(f"load_local_workbook:{path.name}:{sheet}", exc)
    if not frames:
        return pd.DataFrame(columns=CANONICAL_COLUMNS + ["title_key"])
    return merge_records(pd.concat(frames, ignore_index=True, sort=False))


def load_uploaded_workbook(uploaded_file, sheet_choice: str) -> pd.DataFrame:
    if uploaded_file is None:
        return pd.DataFrame(columns=CANONICAL_COLUMNS + ["title_key"])
    try:
        file_bytes = uploaded_file.getvalue()
        sheets = list_sheets_from_bytes(file_bytes)
        sheet_names = sheets if sheet_choice == "All sheets" else [sheets[0] if sheet_choice == "Auto" and sheets else sheet_choice]
        frames = []
        for sheet in sheet_names:
            raw = read_excel_detect_header(file_bytes, sheet)
            frames.append(to_canonical(raw, uploaded_file.name, sheet))
        return merge_records(pd.concat(frames, ignore_index=True, sort=False)) if frames else pd.DataFrame(columns=CANONICAL_COLUMNS + ["title_key"])
    except Exception as exc:
        log_exception("load_uploaded_workbook", exc)
        st.error("The uploaded workbook could not be read. Please check the file format and column headers.")
        return pd.DataFrame(columns=CANONICAL_COLUMNS + ["title_key"])


def load_enrichment(uploaded_enrichment=None) -> pd.DataFrame:
    frames = []
    if ENRICHMENT_FILE.exists():
        try:
            frames.append(pd.read_csv(ENRICHMENT_FILE))
        except Exception as exc:
            log_exception("load_enrichment_local", exc)
    if uploaded_enrichment is not None:
        try:
            frames.append(pd.read_csv(uploaded_enrichment))
        except Exception as exc:
            log_exception("load_enrichment_upload", exc)
            st.warning("The uploaded enrichment CSV could not be read.")
    if not frames:
        return pd.DataFrame(columns=CANONICAL_COLUMNS + ["title_key"])
    normed = [to_canonical(frame, f"enrichment_{i+1}.csv", "CSV") for i, frame in enumerate(frames)]
    return merge_records(pd.concat(normed, ignore_index=True, sort=False))


def extract_keywords(text: str, n: int = 18) -> List[str]:
    text = clean_text(text)
    if len(text) < 30:
        return []
    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 3),
            max_features=3000,
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9\-]{2,}\b",
        )
        matrix = vectorizer.fit_transform([text])
        scores = matrix.toarray()[0]
        terms = np.array(vectorizer.get_feature_names_out())
        order = scores.argsort()[::-1]
        out = []
        for idx in order:
            term = clean_text(terms[idx]).lower()
            if len(term) < 4 or term in STOPWORDS_EXTRA:
                continue
            if any(term == prev or term in prev or prev in term for prev in out[:8]):
                continue
            out.append(term)
            if len(out) >= n:
                break
        return out
    except Exception:
        counts = pd.Series(tokenize(text)).value_counts()
        return counts.head(n).index.tolist()


def classify_research_area(text: str) -> pd.DataFrame:
    text_l = clean_text(text).lower()
    rows = []
    for area, terms in AREA_KEYWORDS.items():
        hits = [term for term in terms if term.lower() in text_l]
        rows.append({"Area": area, "Evidence count": len(hits), "Matched terms": ", ".join(hits)})
    return pd.DataFrame(rows).sort_values(["Evidence count", "Area"], ascending=[False, True]).reset_index(drop=True)


def area_expansion_text(text: str, selected_area: str = "Auto") -> str:
    if selected_area != "Auto":
        return " ".join(AREA_KEYWORDS.get(selected_area, []))
    area_df = classify_research_area(text)
    areas = area_df[area_df["Evidence count"] > 0].head(3)["Area"].tolist()
    return " ".join(term for area in areas for term in AREA_KEYWORDS.get(area, []))


def journal_text(row: pd.Series) -> str:
    title = clean_text(row.get("journal_title", ""))
    parts = [
        title, title, title,
        row.get("field", ""), row.get("for_label", ""), row.get("publisher", ""),
        row.get("aims_scope", ""), row.get("preferred_methods", ""),
        row.get("typical_topics", ""), row.get("editorial_notes", ""),
    ]
    return clean_text(" ".join(map(str, parts)))


def keyword_overlap_score(keywords: List[str], row_text: str) -> Tuple[float, List[str], List[str]]:
    if not keywords:
        return 0.0, [], []
    row_l = row_text.lower()
    matched = []
    for kw in keywords:
        kw_l = kw.lower()
        kw_tokens = [t for t in tokenize(kw_l) if len(t) >= 4]
        if kw_l in row_l or any(t in row_l for t in kw_tokens):
            matched.append(kw)
    missing = [kw for kw in keywords if kw not in matched]
    return min(100.0, 100.0 * len(matched) / max(1, len(keywords))), matched, missing


def area_score(row: pd.Series, selected_area: str, query_text: str) -> float:
    combined = " ".join([clean_text(row.get("field")), clean_text(row.get("for_label")), journal_text(row)]).lower()
    if selected_area != "Auto":
        terms = AREA_KEYWORDS.get(selected_area, [])
        return min(100.0, 35.0 * sum(t.lower() in combined for t in terms))
    top_areas = classify_research_area(query_text).head(3)
    score = 0.0
    for _, area_row in top_areas.iterrows():
        if area_row["Evidence count"] <= 0:
            continue
        terms = AREA_KEYWORDS.get(area_row["Area"], [])
        score += min(40.0, 12.0 * sum(t.lower() in combined for t in terms))
    return min(100.0, score)


def metadata_score(row: pd.Series) -> float:
    key_cols = ["aims_scope", "typical_topics", "preferred_methods", "official_url", "submission_url", "field"]
    filled = sum(bool(clean_text(row.get(col))) for col in key_cols)
    return round(100.0 * filled / len(key_cols), 2)


def context_label(row: pd.Series) -> str:
    labels = []
    abdc = clean_text(row.get("abdc_rating"))
    ajg = clean_text(row.get("ajg_2024"))
    if abdc:
        labels.append(f"ABDC {abdc}")
    if ajg:
        labels.append(f"AJG {ajg}")
    return "; ".join(labels) if labels else "Metadata only"


def fit_band(score: float) -> str:
    if score >= 75:
        return "Strong fit candidate"
    if score >= 55:
        return "Moderate fit candidate"
    if score >= 38:
        return "Exploratory candidate"
    return "Weak evidence in current metadata"


def compute_recommendations(
    abstract: str,
    title: str,
    author_keywords: str,
    journals: pd.DataFrame,
    selected_area: str,
    context_filter: str,
    preferred_context: str,
    field_filter: str,
    top_n: int,
    weights: FitWeights = FitWeights(),
) -> pd.DataFrame:
    df = journals.copy()
    if df.empty:
        return pd.DataFrame()

    if context_filter == "ABDC context only":
        df = df[df["abdc_rating"].map(clean_text).ne("")].copy()
    elif context_filter == "ABS/AJG context only":
        df = df[df["ajg_2024"].map(clean_text).ne("")].copy()

    if preferred_context != "All":
        if preferred_context in RATING_ORDER_ABDC:
            df = df[df["abdc_rating"].eq(preferred_context)].copy()
        elif preferred_context in RATING_ORDER_AJG:
            df = df[df["ajg_2024"].eq(preferred_context)].copy()

    if field_filter != "All":
        df = df[df["field"].fillna("").astype(str).str.contains(re.escape(field_filter), case=False, na=False)].copy()

    if df.empty:
        return df

    query_text = clean_text(" ".join([title, abstract, author_keywords]))
    expanded_query = clean_text(" ".join([query_text, area_expansion_text(query_text, selected_area)]))
    keywords = extract_keywords(query_text, 22)
    df["_journal_text"] = df.apply(journal_text, axis=1)

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=6000,
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9\-]{2,}\b",
        )
        corpus = [expanded_query] + df["_journal_text"].tolist()
        matrix = vectorizer.fit_transform(corpus)
        similarities = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
        max_sim = max(float(similarities.max()), 1e-9)
        df["Semantic fit"] = np.round(100.0 * similarities / max_sim, 2)
    except Exception as exc:
        log_exception("compute_semantic_similarity", exc)
        df["Semantic fit"] = 0.0

    overlap_rows = [keyword_overlap_score(keywords, row_text) for row_text in df["_journal_text"].tolist()]
    df["Keyword overlap"] = [round(x[0], 2) for x in overlap_rows]
    df["Matched keywords"] = [", ".join(x[1][:10]) for x in overlap_rows]
    df["Missing keywords"] = [", ".join(x[2][:10]) for x in overlap_rows]
    df["Area alignment"] = df.apply(lambda r: area_score(r, selected_area, query_text), axis=1).round(2)
    df["Metadata richness"] = df.apply(metadata_score, axis=1).round(2)

    df["Journal-fit score"] = (
        weights.semantic * df["Semantic fit"] +
        weights.keyword * df["Keyword overlap"] +
        weights.area * df["Area alignment"] +
        weights.metadata * df["Metadata richness"]
    ).round(2)
    df["Suitability band"] = df["Journal-fit score"].map(fit_band)
    df["Context signals"] = df.apply(context_label, axis=1)
    df["Official journal search"] = df["journal_title"].map(lambda j: google_search_url(f'"{j}" journal aims scope submission'))
    df["Scholar search"] = df["journal_title"].map(lambda j: scholar_search_url(f'"{j}"'))

    display_cols = [
        "journal_title", "Journal-fit score", "Suitability band", "Semantic fit", "Keyword overlap",
        "Area alignment", "Metadata richness", "field", "Context signals", "publisher", "issn", "eissn",
        "official_url", "submission_url", "Matched keywords", "Missing keywords",
        "source_file", "source_sheet", "Official journal search", "Scholar search",
    ]
    out = df.sort_values("Journal-fit score", ascending=False).head(top_n).copy()
    return out[[c for c in display_cols if c in out.columns]]


def parse_uploaded_manuscript(uploaded_file) -> Dict[str, str]:
    if uploaded_file is None:
        return {"title": "", "abstract": "", "keywords": "", "text": ""}
    filename = uploaded_file.name.lower()
    try:
        raw_bytes = uploaded_file.getvalue()
        text = ""
        if filename.endswith(".pdf"):
            if PdfReader is None:
                raise RuntimeError("PDF reader is not installed.")
            reader = PdfReader(io.BytesIO(raw_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages[:8])
        elif filename.endswith(".docx"):
            if docx is None:
                raise RuntimeError("python-docx is not installed.")
            document = docx.Document(io.BytesIO(raw_bytes))
            text = "\n".join(p.text for p in document.paragraphs)
        else:
            text = raw_bytes.decode("utf-8", errors="ignore")
    except Exception as exc:
        log_exception("parse_uploaded_manuscript", exc)
        st.warning("The manuscript could not be parsed. You may paste the title, abstract, and keywords manually.")
        return {"title": "", "abstract": "", "keywords": "", "text": ""}

    lines = [clean_text(line) for line in text.splitlines() if clean_text(line)]
    title = lines[0][:220] if lines else ""
    abstract = ""
    keywords = ""

    joined = "\n".join(lines)
    abstract_match = re.search(r"(?is)\babstract\b[:\s-]*(.*?)(\bkeywords\b|\bkey words\b|\bintroduction\b|\n\s*1\.?\s+)", joined)
    if abstract_match:
        abstract = clean_text(abstract_match.group(1))[:5000]
    elif len(lines) > 1:
        abstract = clean_text(" ".join(lines[1:8]))[:2500]

    keywords_match = re.search(r"(?is)\bkey\s*words?\b[:\s-]*(.*?)(\n\s*\d|\bintroduction\b|\bbackground\b)", joined)
    if keywords_match:
        keywords = clean_text(keywords_match.group(1))[:500]
    else:
        keywords = "; ".join(extract_keywords(" ".join([title, abstract]), 8))

    return {"title": title, "abstract": abstract, "keywords": keywords, "text": text[:20000]}


def project_health_summary() -> Dict[str, object]:
    ensure_runtime_dirs()
    files = workbook_files()
    return {
        "app_version": APP_VERSION,
        "data_dir": str(DATA_DIR),
        "outputs_dir": str(OUTPUT_DIR),
        "workbooks_detected": len(files),
        "available_workbooks": [p.name for p in files],
        "enrichment_file_present": ENRICHMENT_FILE.exists(),
        "error_log_file": str(ERROR_LOG_FILE),
    }


def create_markdown_report(title: str, abstract: str, keywords: str, results: pd.DataFrame) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# JournalFit Studio Report",
        "",
        f"Generated: {now}",
        f"Tool: {APP_NAME} v{APP_VERSION}",
        "",
        "## Manuscript",
        f"**Title:** {title or '[Not provided]'}",
        "",
        f"**Keywords:** {keywords or '[Not provided]'}",
        "",
        "**Abstract:**",
        "",
        abstract or "[Not provided]",
        "",
        "## Important note",
        "",
        "Journal-fit suggestions are decision-support outputs. Researchers must verify final suitability using the official journal website, aims and scope, author guidelines, indexing status, editorial policies, and publication ethics information.",
        "",
        "## Shortlisted journals",
        "",
    ]
    if results.empty:
        lines.append("No recommendations were generated.")
    else:
        for i, row in results.iterrows():
            lines.extend([
                f"### {len([l for l in lines if l.startswith('### ')]) + 1}. {clean_text(row.get('journal_title'))}",
                f"- Journal-fit score: {row.get('Journal-fit score', '')}",
                f"- Suitability band: {row.get('Suitability band', '')}",
                f"- Field: {row.get('field', '')}",
                f"- Context signals: {row.get('Context signals', '')}",
                f"- Matched keywords: {row.get('Matched keywords', '')}",
                f"- Official URL: {row.get('official_url', '') or '[Verify manually]'}",
                f"- Submission URL: {row.get('submission_url', '') or '[Verify manually]'}",
                "",
            ])
    return "\n".join(lines)


def create_prompt(title: str, abstract: str, keywords: str, row: pd.Series) -> str:
    journal = clean_text(row.get("journal_title"))
    return f"""You are helping me verify whether the following manuscript is suitable for the journal named below. Do not assume acceptance likelihood. Focus only on fit, scope, manuscript positioning, and verification questions.\n\nManuscript title:\n{title}\n\nAbstract:\n{abstract}\n\nKeywords:\n{keywords}\n\nCandidate journal:\n{journal}\n\nKnown context from my local metadata:\n- Field: {clean_text(row.get('field'))}\n- Publisher: {clean_text(row.get('publisher'))}\n- Context signals: {clean_text(row.get('Context signals'))}\n- Matched keywords: {clean_text(row.get('Matched keywords'))}\n\nPlease provide:\n1. Scope-fit assessment.\n2. Possible mismatch risks.\n3. Questions I should verify on the official journal website.\n4. How to adjust title, abstract, and keywords for better fit if the journal is suitable.\n5. A final cautionary note reminding me to verify official aims and scope, indexing, fees, publication ethics, and submission guidelines."""


def copy_box(text: str, height: int = 180) -> None:
    escaped = html.escape(text)
    components.html(
        f"""
        <textarea id="copyText" style="width:100%;height:{height}px;border:1px solid #d7d9ff;border-radius:14px;padding:14px;font-family:Inter,Arial,sans-serif;font-size:13px;line-height:1.5;">{escaped}</textarea>
        <button onclick="navigator.clipboard.writeText(document.getElementById('copyText').value)" style="margin-top:10px;border:0;border-radius:999px;padding:10px 16px;background:linear-gradient(135deg,#4f46e5,#ec4899);color:#fff;font-weight:700;cursor:pointer;">Copy text</button>
        """,
        height=height + 70,
    )


def load_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
        .stApp {
            background:
                radial-gradient(circle at 12% 8%, rgba(79,70,229,.16), transparent 30%),
                radial-gradient(circle at 87% 10%, rgba(236,72,153,.14), transparent 32%),
                radial-gradient(circle at 76% 80%, rgba(249,115,22,.12), transparent 30%),
                linear-gradient(135deg, #f8fbff 0%, #fff7ed 50%, #f5f3ff 100%);
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #07162f 0%, #111827 52%, #20133b 100%);
            color: white;
        }
        section[data-testid="stSidebar"] * { color: inherit; }
        section[data-testid="stSidebar"] .stSelectbox label,
        section[data-testid="stSidebar"] .stSlider label,
        section[data-testid="stSidebar"] .stMultiSelect label,
        section[data-testid="stSidebar"] .stFileUploader label,
        section[data-testid="stSidebar"] .stCheckbox label { color: #f8fafc !important; font-weight: 700; }
        section[data-testid="stSidebar"] [data-baseweb="select"] * { color: #0f172a !important; }
        section[data-testid="stSidebar"] .stMarkdown p { color: #cbd5e1; }
        .main .block-container { max-width: 1500px; padding-top: 2rem; padding-bottom: 4rem; }
        .hero {
            border: 1px solid rgba(79,70,229,.16);
            border-radius: 32px;
            padding: 34px;
            background: linear-gradient(135deg, rgba(255,255,255,.92), rgba(250,245,255,.82), rgba(255,247,237,.92));
            box-shadow: 0 28px 70px rgba(15,23,42,.12);
            margin-bottom: 18px;
        }
        .hero-grid { display:grid; grid-template-columns: 88px 1fr; gap:24px; align-items:center; }
        .logo-card {
            width:86px;height:86px;border-radius:28px;display:flex;align-items:center;justify-content:center;
            background:linear-gradient(135deg,#4f46e5,#8b5cf6,#ec4899,#f97316);box-shadow:0 18px 42px rgba(79,70,229,.3);font-size:42px;
        }
        .eyebrow { display:inline-flex; align-items:center; gap:8px; padding:8px 14px; border-radius:999px; background:#eef2ff; color:#312e81; font-weight:800; font-size:12px; border:1px solid #c7d2fe; margin-bottom:10px; }
        .hero h1 { font-size:44px; line-height:1.05; margin:0 0 12px 0; letter-spacing:-1.5px; color:#0f172a; }
        .gradient-text { background:linear-gradient(90deg,#2563eb,#7c3aed,#ec4899,#f97316); -webkit-background-clip:text; color:transparent; }
        .hero p { color:#334155; font-size:17px; line-height:1.7; margin:0; max-width:960px; }
        .badge-row { display:flex; flex-wrap:wrap; gap:10px; margin-top:22px; }
        .badge { border:1px solid #e0e7ff; background:rgba(255,255,255,.78); color:#3730a3; padding:9px 13px; border-radius:999px; font-size:12px; font-weight:800; box-shadow:0 8px 20px rgba(15,23,42,.05); }
        .notice { border-left:5px solid #f97316; background:rgba(255,255,255,.88); border-radius:14px; padding:14px 18px; margin:16px 0; color:#1f2937; box-shadow:0 10px 26px rgba(15,23,42,.06); }
        .metric-card { padding:18px; border-radius:24px; background:rgba(255,255,255,.86); border:1px solid rgba(226,232,240,.9); box-shadow:0 18px 42px rgba(15,23,42,.08); min-height:118px; }
        .metric-kicker { font-size:12px; color:#64748b; font-weight:800; text-transform:uppercase; letter-spacing:.04em; }
        .metric-value { font-size:30px; color:#111827; font-weight:900; margin-top:6px; }
        .metric-note { font-size:12px; color:#64748b; margin-top:6px; }
        .section-title { margin-top:26px; color:#0f172a; font-size:28px; font-weight:900; letter-spacing:-.6px; }
        .soft-card { border:1px solid rgba(226,232,240,.9); background:rgba(255,255,255,.78); border-radius:24px; padding:20px; box-shadow:0 16px 36px rgba(15,23,42,.07); }
        .footer { margin-top:36px; padding:22px; border-radius:24px; background:#0f172a; color:#e2e8f0; font-size:13px; }
        .footer a { color:#bfdbfe; text-decoration:none; font-weight:700; }
        .stButton > button, .stDownloadButton > button {
            border-radius:999px !important; border:0 !important; font-weight:800 !important;
            background:linear-gradient(135deg,#4f46e5,#8b5cf6,#ec4899) !important; color:white !important;
            box-shadow:0 14px 32px rgba(79,70,229,.28) !important;
        }
        div[data-testid="stDataFrame"] { border-radius:20px; overflow:hidden; border:1px solid #e2e8f0; box-shadow:0 18px 44px rgba(15,23,42,.08); }
        .sidebar-brand {
            border:1px solid rgba(255,255,255,.16); border-radius:24px; padding:20px;
            background:linear-gradient(135deg,rgba(59,130,246,.28),rgba(236,72,153,.22)); margin-bottom:20px;
        }
        .sidebar-brand-title { font-weight:900; color:white; font-size:18px; margin-bottom:8px; }
        .sidebar-brand-sub { color:#cbd5e1; font-size:12px; line-height:1.6; }
        @media (max-width: 760px) {
            .main .block-container { padding: .8rem .8rem 3rem .8rem; }
            .hero { padding: 20px; border-radius: 24px; }
            .hero-grid { grid-template-columns: 1fr; gap: 14px; }
            .logo-card { width:72px;height:72px;border-radius:22px;font-size:34px; }
            .hero h1 { font-size: 30px; line-height: 1.12; }
            .hero p { font-size: 14px; }
            .badge { font-size: 11px; padding: 8px 10px; }
            .section-title { font-size: 23px; }
            .metric-value { font-size: 24px; }
            [data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> Dict[str, object]:
    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-brand">
                <div style="font-size:38px;line-height:1;">📚</div>
                <div class="sidebar-brand-title">{APP_NAME}</div>
                <div class="sidebar-brand-sub">Journal discovery using title, abstract, keywords, and local journal metadata.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Journal metadata")
        st.caption("Use local workbooks or upload journal metadata. Ranking fields are optional context, not the core purpose.")
        local_files = workbook_files()
        selected_paths: List[str] = []
        if local_files:
            selected_names = st.multiselect(
                "Local journal metadata workbooks",
                options=[p.name for p in local_files],
                default=[local_files[0].name],
                help="Files stored inside the data folder."
            )
            selected_paths = [str(p) for p in local_files if p.name in selected_names]
        else:
            st.info("No local workbook found in data/. You can upload one below.")

        uploaded_workbook = st.file_uploader("Upload journal workbook", type=["xlsx", "xls"], help="Columns such as journal title, field, aims/scope, URL, ISSN, or optional ABDC/AJG context are supported.")
        uploaded_enrichment = st.file_uploader("Optional enrichment CSV", type=["csv"], help="Add verified aims/scope, topics, official URLs, and notes.")
        sheet_choice = st.selectbox("Sheet", ["Auto", "All sheets"], index=0)

        with st.expander("App health", expanded=False):
            st.json(project_health_summary())

        st.markdown("### Discovery settings")
        context_filter = st.selectbox("Optional context filter", ["All metadata", "ABDC context only", "ABS/AJG context only"], index=0)
        preferred_context = st.selectbox("Optional rating/context value", ["All", "A*", "A", "B", "C", "4*", "4", "3", "2", "1"], index=0)
        selected_area = st.selectbox("Research-area support", ["Auto"] + list(AREA_KEYWORDS.keys()), index=0)
        top_n = st.slider("Number of suitable journals", 5, 100, 30, 5)

        st.markdown("### Contributor")
        st.caption(f"Developed by {AUTHOR}. Independent research-support contribution; not an official tool of any ranking or indexing body.")

    return {
        "selected_paths": tuple(selected_paths),
        "uploaded_workbook": uploaded_workbook,
        "uploaded_enrichment": uploaded_enrichment,
        "sheet_choice": sheet_choice,
        "context_filter": context_filter,
        "preferred_context": preferred_context,
        "selected_area": selected_area,
        "top_n": top_n,
    }


def render_hero() -> None:
    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-grid">
                <div class="logo-card">📚</div>
                <div>
                    <div class="eyebrow">Researcher-first journal discovery · Local-first · No API keys</div>
                    <h1>JournalFit <span class="gradient-text">Studio</span></h1>
                    <p>
                    A polished workspace for identifying potentially suitable journals from a manuscript title,
                    abstract, keywords, research area, and local journal metadata. Ranking fields, when present,
                    are treated as optional context rather than the basis of recommendation.
                    </p>
                    <div class="badge-row">
                        <span class="badge">🔎 Journal-fit discovery</span>
                        <span class="badge">🧾 Title + abstract matching</span>
                        <span class="badge">📁 Local workbook workflow</span>
                        <span class="badge">🔐 No external manuscript transfer</span>
                        <span class="badge">🧭 Responsible-use safeguards</span>
                        <span class="badge">© {AUTHOR}</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="notice">
        <strong>Integrity note:</strong> Journal-fit suggestions are decision-support outputs. They do not predict acceptance,
        publication speed, indexing status, APCs, or editorial suitability. Always verify the official journal website,
        aims and scope, author guidelines, indexing, fees, ethics policy, and submission route before submission.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metrics(journals: pd.DataFrame, results: Optional[pd.DataFrame]) -> None:
    c1, c2, c3, c4 = st.columns(4)
    values = [
        ("Journal records", f"{len(journals):,}", "Loaded from local/uploaded metadata"),
        ("Fields detected", f"{journals['field'].map(clean_text).ne('').sum():,}" if not journals.empty and 'field' in journals else "0", "Records with subject or field labels"),
        ("Verified URLs", f"{journals['official_url'].map(clean_text).ne('').sum():,}" if not journals.empty and 'official_url' in journals else "0", "Official links available locally"),
        ("Recommendations", f"{len(results):,}" if results is not None else "0", "Generated in this session"),
    ]
    for col, (kicker, value, note) in zip([c1, c2, c3, c4], values):
        with col:
            st.markdown(f"<div class='metric-card'><div class='metric-kicker'>{kicker}</div><div class='metric-value'>{value}</div><div class='metric-note'>{note}</div></div>", unsafe_allow_html=True)


def main() -> None:
    ensure_runtime_dirs()
    st.set_page_config(
        page_title=f"{APP_NAME} | Journal discovery",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    load_css()
    settings = render_sidebar()
    render_hero()

    local_df = load_local_workbooks(settings["selected_paths"], settings["sheet_choice"])
    uploaded_df = load_uploaded_workbook(settings["uploaded_workbook"], settings["sheet_choice"])
    enrichment_df = load_enrichment(settings["uploaded_enrichment"])
    frames = [df for df in [local_df, uploaded_df, enrichment_df] if not df.empty]
    journals = merge_records(pd.concat(frames, ignore_index=True, sort=False)) if frames else pd.DataFrame(columns=CANONICAL_COLUMNS + ["title_key"])

    fields = ["All"]
    if not journals.empty and "field" in journals.columns:
        fields += sorted([x for x in journals["field"].map(clean_text).unique().tolist() if x])[:250]

    if "manuscript_upload_parsed" not in st.session_state:
        st.session_state.manuscript_upload_parsed = {"title": "", "abstract": "", "keywords": ""}
    if "recommendations" not in st.session_state:
        st.session_state.recommendations = None

    st.markdown("<div class='section-title'>1. Manuscript input</div>", unsafe_allow_html=True)
    left, right = st.columns([2, 1])
    with right:
        manuscript_upload = st.file_uploader("Optional: upload manuscript to auto-fill title, abstract, and keywords", type=["pdf", "docx", "txt"])
        if manuscript_upload is not None:
            parsed = parse_uploaded_manuscript(manuscript_upload)
            st.session_state.manuscript_upload_parsed = parsed
            if parsed.get("abstract"):
                st.success("Manuscript parsed. Please review the extracted fields before running discovery.")
        field_filter = st.selectbox("Field/category filter", fields, index=0)
        st.caption("Detected research-area signals")
        area_preview_text = " ".join(st.session_state.manuscript_upload_parsed.values())
        st.dataframe(classify_research_area(area_preview_text).head(5), use_container_width=True, hide_index=True)

    with left:
        title = st.text_input("Manuscript title", value=st.session_state.manuscript_upload_parsed.get("title", ""), placeholder="Paste or type the manuscript title")
        abstract = st.text_area("Abstract", value=st.session_state.manuscript_upload_parsed.get("abstract", ""), height=250, placeholder="Paste the abstract, or upload a manuscript to auto-fill.")
        keywords = st.text_input("Author keywords", value=st.session_state.manuscript_upload_parsed.get("keywords", ""), placeholder="e.g., digital governance; algorithmic accountability; risk; transparency")
        run = st.button("🔎 Find suitable journals", use_container_width=False)

    if run:
        if journals.empty:
            st.error("No journal metadata is available. Please add an Excel workbook to data/ or upload a workbook from the sidebar.")
        elif len(clean_text(title + abstract + keywords)) < 60:
            st.warning("Please provide a more complete title, abstract, or keyword set before running journal discovery.")
        else:
            with st.spinner("Matching manuscript signals with local journal metadata..."):
                st.session_state.recommendations = compute_recommendations(
                    abstract=abstract,
                    title=title,
                    author_keywords=keywords,
                    journals=journals,
                    selected_area=settings["selected_area"],
                    context_filter=settings["context_filter"],
                    preferred_context=settings["preferred_context"],
                    field_filter=field_filter,
                    top_n=settings["top_n"],
                )

    results = st.session_state.recommendations
    render_metrics(journals, results)

    st.markdown("<div class='section-title'>2. Suitable journal shortlist</div>", unsafe_allow_html=True)
    if results is None:
        st.info("Run journal discovery to generate a shortlist.")
    elif results.empty:
        st.warning("No suitable journals were found under the current filters. Try using all metadata, increasing the recommendation count, or enriching journal-scope information.")
    else:
        visible = results.rename(columns={"journal_title": "Journal", "field": "Field", "publisher": "Publisher"})
        st.dataframe(
            visible[[c for c in ["Journal", "Journal-fit score", "Suitability band", "Semantic fit", "Keyword overlap", "Area alignment", "Metadata richness", "Field", "Context signals", "Publisher", "official_url", "submission_url"] if c in visible.columns]],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("<div class='section-title'>3. Recommendation explanations</div>", unsafe_allow_html=True)
        for i, (_, row) in enumerate(results.head(10).iterrows(), start=1):
            with st.expander(f"{i}. {clean_text(row.get('journal_title'))} — {row.get('Suitability band')} ({row.get('Journal-fit score')})", expanded=(i == 1)):
                c1, c2 = st.columns([1.3, 1])
                with c1:
                    st.markdown(f"**Why it appeared:** semantic fit `{row.get('Semantic fit')}`, keyword overlap `{row.get('Keyword overlap')}`, area alignment `{row.get('Area alignment')}`, metadata richness `{row.get('Metadata richness')}`.")
                    st.markdown(f"**Matched keywords:** {clean_text(row.get('Matched keywords')) or 'No direct keyword evidence in current metadata.'}")
                    st.markdown(f"**Missing keywords to verify manually:** {clean_text(row.get('Missing keywords')) or 'None shown.'}")
                    st.markdown(f"**Context signals:** {clean_text(row.get('Context signals'))}")
                with c2:
                    official = safe_link(row.get("official_url"))
                    submission = safe_link(row.get("submission_url"))
                    st.link_button("Official journal page" if official else "Search official journal page", official or row.get("Official journal search"), use_container_width=True)
                    st.link_button("Submission information" if submission else "Search submission information", submission or row.get("Official journal search"), use_container_width=True)
                    st.link_button("Scholar search", row.get("Scholar search"), use_container_width=True)
                st.markdown("**Verification checklist before submission**")
                st.markdown("- Confirm aims and scope on the official journal website.\n- Check article type, word limit, fees, indexing, ethics policy, and author guidelines.\n- Compare recent published articles with your manuscript.\n- Do not treat fit score or ranking context as acceptance likelihood.")

        st.markdown("<div class='section-title'>4. Export and next-step prompt</div>", unsafe_allow_html=True)
        report = create_markdown_report(title, abstract, keywords, results)
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("⬇️ Download journal-fit report", report, file_name="journalfit_report.md", mime="text/markdown")
        with c2:
            csv_bytes = results.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download shortlist CSV", csv_bytes, file_name="journalfit_shortlist.csv", mime="text/csv")

        first_row = results.iloc[0]
        st.markdown("Use this prompt to verify the top candidate carefully in any research-support workflow:")
        copy_box(create_prompt(title, abstract, keywords, first_row), height=240)

    st.markdown(
        f"""
        <div class="footer">
        <strong>{APP_NAME} v{APP_VERSION}</strong> · Developed by {AUTHOR}.<br/>
        Live app: <a href="{APP_URL}" target="_blank">{APP_URL}</a><br/>
        GitHub: <a href="{GITHUB_URL}" target="_blank">{GITHUB_URL}</a> · Portfolio: <a href="{PORTFOLIO_URL}" target="_blank">{PORTFOLIO_URL}</a><br/><br/>
        Independent research-support contribution. Not affiliated with, endorsed by, or presented as an official tool of any ranking, indexing, or publishing body.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
