from __future__ import annotations

import io
import re
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None
try:
    import docx
except Exception:
    docx = None

APP_NAME = "JournalFit Studio"
APP_VERSION = "4.1.0"
AUTHOR = "Dr. Alok Tiwari"
APP_URL = "https://journalfit-studio-by-dr-alok-tiwari.streamlit.app/"
GITHUB_URL = "https://github.com/dr-alok-tiwari/journalfit-studio"
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
ERROR_LOG = OUTPUT_DIR / "journalfit_error.log"
SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
FILE_PRIORITY = ["journal_metadata.xlsx", "journal_metadata.csv", "sample_journal_metadata.csv", "ABS_Submission_Links.xlsx", "ABDC-Ranking.xlsx"]

ALIASES = {
    "journal_title": ["journal title", "title", "journal", "journal name", "source title", "publication title", "periodical title"],
    "publisher": ["publisher", "publisher name"],
    "issn": ["issn", "print issn", "p-issn", "issn-l"],
    "eissn": ["eissn", "online issn", "electronic issn", "issnonline"],
    "field": ["field", "discipline", "category", "subject", "subject area", "research area", "abdc field"],
    "abdc_rating": ["2025 rating", "abdc rating", "abdc category", "rating"],
    "ajg_2024": ["ajg 2024", "abs 2024", "cabs 2024", "ajg rating", "abs rating"],
    "official_url": ["journal url", "url", "homepage", "official url", "journal website", "website"],
    "submission_url": ["link to submission", "submission link", "submission url", "author guidelines", "guide for authors"],
    "aims_scope": ["aims scope", "aims and scope", "scope", "journal scope", "description", "about journal", "aims"],
    "preferred_methods": ["preferred methods", "methods", "methodology"],
    "typical_topics": ["typical topics", "topics", "keywords", "journal keywords", "themes"],
    "editorial_notes": ["editorial notes", "notes", "remarks"],
}
CANONICAL = list(ALIASES) + ["source_file", "source_sheet", "source_kind"]
AREA_TERMS = {
    "Information Systems / Analytics": ["analytics", "data", "digital", "algorithm", "artificial intelligence", "machine learning", "information system"],
    "Healthcare Management": ["healthcare", "hospital", "patient", "clinical", "health", "medical"],
    "Strategy / Governance": ["strategy", "governance", "policy", "responsible", "accountability", "institution"],
    "Finance": ["finance", "banking", "investment", "risk", "portfolio", "fintech"],
    "Marketing": ["marketing", "consumer", "brand", "retail", "customer"],
    "Operations / Supply Chain": ["operations", "supply chain", "logistics", "quality", "process"],
    "HRM / OB": ["human resource", "employee", "leadership", "team", "workplace"],
    "Economics": ["economics", "econometric", "policy", "welfare", "labour"],
    "Education / Learning": ["education", "learning", "teaching", "student", "pedagogy"],
    "Tourism": ["tourism", "hospitality", "travel", "destination"],
}


def ensure_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)


def log_error(context: str, exc: Exception) -> None:
    try:
        ensure_dirs()
        with ERROR_LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {context}: {type(exc).__name__}: {exc}\n")
    except Exception:
        pass


def clean(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return re.sub(r"\s+", " ", str(value).replace("\n", " ").replace("\r", " ").replace("\t", " ")).strip()


def norm_col(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean(value).lower()).strip()


def norm_title(value: object) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", clean(value).lower().replace("&", "and"))).strip()


def safe_url(value: object) -> str:
    text = clean(value)
    if text.startswith(("http://", "https://")):
        return text
    return "https://" + text if "." in text and " " not in text else ""


def search_url(query: str) -> str:
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)


def metadata_files() -> List[Path]:
    ensure_dirs()
    priority = {name: idx for idx, name in enumerate(FILE_PRIORITY)}
    files = [p for p in DATA_DIR.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS and p.name != "journal_enrichment.csv"]
    return sorted(files, key=lambda p: (priority.get(p.name, 99), p.name.lower()))


def best_header(preview: pd.DataFrame) -> int:
    tokens = ["journal", "publisher", "issn", "rating", "ajg", "abdc", "field", "scope", "url"]
    scores = []
    for _, row in preview.iterrows():
        row_text = " | ".join(clean(x).lower() for x in row.tolist())
        scores.append(sum(t in row_text for t in tokens) + min(3, sum(bool(clean(x)) for x in row.tolist()) // 2))
    return int(np.argmax(scores)) if scores else 0


@st.cache_data(show_spinner=False)
def read_table(file_bytes: bytes, filename: str, sheet: str = "Auto") -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".csv":
            last: Optional[Exception] = None
            for encoding in ["utf-8-sig", "utf-8", "latin-1"]:
                try:
                    preview = pd.read_csv(io.BytesIO(file_bytes), header=None, nrows=30, encoding=encoding)
                    return pd.read_csv(io.BytesIO(file_bytes), header=best_header(preview), encoding=encoding).dropna(how="all").dropna(axis=1, how="all")
                except Exception as exc:
                    last = exc
            raise last or RuntimeError("CSV could not be read")
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        real_sheet = xl.sheet_names[0] if sheet == "Auto" else sheet
        preview = pd.read_excel(io.BytesIO(file_bytes), sheet_name=real_sheet, header=None, nrows=30)
        return pd.read_excel(io.BytesIO(file_bytes), sheet_name=real_sheet, header=best_header(preview)).dropna(how="all").dropna(axis=1, how="all")
    except Exception as exc:
        log_error(f"read_table:{filename}:{sheet}", exc)
        return pd.DataFrame()


def sheets_for(file_bytes: bytes, filename: str) -> List[str]:
    if Path(filename).suffix.lower() == ".csv":
        return ["CSV"]
    try:
        return pd.ExcelFile(io.BytesIO(file_bytes)).sheet_names
    except Exception as exc:
        log_error(f"sheets_for:{filename}", exc)
        return []


def find_column(df: pd.DataFrame, target: str) -> Optional[str]:
    lookup = {norm_col(c): c for c in df.columns}
    for alias in ALIASES[target]:
        key = norm_col(alias)
        if key in lookup:
            return lookup[key]
    for key, original in lookup.items():
        for alias in ALIASES[target]:
            alias_key = norm_col(alias)
            if len(alias_key) > 3 and (alias_key in key or key in alias_key):
                return original
    return None


def canonicalize(raw: pd.DataFrame, source_file: str, source_sheet: str) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=CANONICAL + ["title_key"])
    raw = raw.copy()
    raw.columns = [clean(c) for c in raw.columns]
    out = pd.DataFrame(index=raw.index)
    for col in ALIASES:
        detected = find_column(raw, col)
        out[col] = raw[detected] if detected else ""
    if out["journal_title"].map(clean).eq("").all():
        for col in raw.columns:
            if raw[col].dropna().astype(str).head(10).str.len().median() > 5:
                out["journal_title"] = raw[col]
                break
    for col in out.columns:
        out[col] = out[col].map(clean)
    out["official_url"] = out["official_url"].map(safe_url)
    out["submission_url"] = out["submission_url"].map(safe_url)
    out["source_file"] = source_file
    out["source_sheet"] = source_sheet
    text = (source_file + " " + " ".join(raw.columns)).lower()
    out["source_kind"] = "ABS/AJG context" if "ajg" in text or "abs" in text else "ABDC context" if "abdc" in text else "Journal metadata"
    out = out[out["journal_title"].map(clean).ne("")].copy()
    out["title_key"] = out["journal_title"].map(norm_title)
    return out


def merge_records(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=CANONICAL + ["title_key"])
    rows = []
    for _, group in df.groupby("title_key", dropna=False):
        row = {}
        for col in group.columns:
            values = [clean(x) for x in group[col].tolist() if clean(x)]
            if col in {"source_file", "source_sheet", "source_kind"}:
                row[col] = "; ".join(sorted(set(values)))
            else:
                row[col] = values[0] if values else ""
        rows.append(row)
    out = pd.DataFrame(rows)
    for col in CANONICAL:
        if col not in out.columns:
            out[col] = ""
    out["title_key"] = out["journal_title"].map(norm_title)
    return out


@st.cache_data(show_spinner=False)
def load_local(paths: tuple[str, ...], sheet_choice: str) -> pd.DataFrame:
    frames = []
    for path_text in paths:
        path = Path(path_text)
        if not path.exists():
            continue
        data = path.read_bytes()
        sheets = ["CSV"] if path.suffix.lower() == ".csv" else sheets_for(data, path.name)
        if sheet_choice == "Auto" and sheets:
            sheets = [sheets[0]]
        for sheet in sheets:
            frame = canonicalize(read_table(data, path.name, sheet), path.name, sheet)
            if not frame.empty:
                frames.append(frame)
    return merge_records(pd.concat(frames, ignore_index=True)) if frames else pd.DataFrame(columns=CANONICAL + ["title_key"])


def load_upload(uploaded, sheet_choice: str) -> pd.DataFrame:
    if uploaded is None:
        return pd.DataFrame(columns=CANONICAL + ["title_key"])
    data = uploaded.getvalue()
    sheets = ["CSV"] if Path(uploaded.name).suffix.lower() == ".csv" else sheets_for(data, uploaded.name)
    if sheet_choice == "Auto" and sheets:
        sheets = [sheets[0]]
    frames = [canonicalize(read_table(data, uploaded.name, sheet), uploaded.name, sheet) for sheet in sheets]
    frames = [f for f in frames if not f.empty]
    return merge_records(pd.concat(frames, ignore_index=True)) if frames else pd.DataFrame(columns=CANONICAL + ["title_key"])


def load_enrichment(uploaded) -> pd.DataFrame:
    frames = []
    local = DATA_DIR / "journal_enrichment.csv"
    if local.exists():
        frames.append(canonicalize(pd.read_csv(local), local.name, "CSV"))
    if uploaded is not None:
        frames.append(canonicalize(pd.read_csv(uploaded), uploaded.name, "CSV"))
    frames = [f for f in frames if not f.empty]
    return merge_records(pd.concat(frames, ignore_index=True)) if frames else pd.DataFrame(columns=CANONICAL + ["title_key"])


def extract_manuscript(uploaded) -> dict[str, str]:
    if uploaded is None:
        return {"title": "", "abstract": "", "keywords": ""}
    try:
        data = uploaded.getvalue()
        name = uploaded.name.lower()
        if name.endswith(".pdf") and PdfReader:
            text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages[:8])
        elif name.endswith(".docx") and docx:
            text = "\n".join(p.text for p in docx.Document(io.BytesIO(data)).paragraphs)
        else:
            text = data.decode("utf-8", errors="ignore")
    except Exception as exc:
        log_error("extract_manuscript", exc)
        return {"title": "", "abstract": "", "keywords": ""}
    lines = [clean(x) for x in text.splitlines() if clean(x)]
    title = lines[0][:220] if lines else ""
    joined = "\n".join(lines)
    match = re.search(r"(?is)\babstract\b[:\s-]*(.*?)(\bkeywords\b|\bkey words\b|\bintroduction\b|\n\s*1\.?\s+)", joined)
    abstract = clean(match.group(1))[:5000] if match else clean(" ".join(lines[1:8]))[:2500]
    kw_match = re.search(r"(?is)\bkey\s*words?\b[:\s-]*(.*?)(\n\s*\d|\bintroduction\b|\bbackground\b)", joined)
    keywords = clean(kw_match.group(1))[:500] if kw_match else "; ".join(keywords_from_text(title + " " + abstract, 8))
    return {"title": title, "abstract": abstract, "keywords": keywords}


def keywords_from_text(text: str, n: int = 20) -> List[str]:
    text = clean(text)
    if len(text) < 30:
        return []
    try:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 3), max_features=3000)
        matrix = vectorizer.fit_transform([text])
        terms = np.array(vectorizer.get_feature_names_out())
        scores = matrix.toarray()[0]
        return [clean(terms[i]).lower() for i in scores.argsort()[::-1][:n] if len(clean(terms[i])) > 3]
    except Exception:
        return []


def journal_text(row: pd.Series) -> str:
    title = clean(row.get("journal_title"))
    parts = [title, title, title, row.get("field", ""), row.get("publisher", ""), row.get("aims_scope", ""), row.get("preferred_methods", ""), row.get("typical_topics", ""), row.get("editorial_notes", "")]
    return clean(" ".join(map(str, parts)))


def classify_area(text: str) -> pd.DataFrame:
    lower = clean(text).lower()
    rows = []
    for area, terms in AREA_TERMS.items():
        hits = [t for t in terms if t in lower]
        rows.append({"Area": area, "Evidence count": len(hits), "Matched terms": ", ".join(hits)})
    return pd.DataFrame(rows).sort_values(["Evidence count", "Area"], ascending=[False, True])


def area_terms(text: str, area: str) -> str:
    if area != "Auto":
        return " ".join(AREA_TERMS.get(area, []))
    top = classify_area(text)
    return " ".join(t for a in top[top["Evidence count"] > 0].head(3)["Area"].tolist() for t in AREA_TERMS.get(a, []))


def recommend(title: str, abstract: str, author_keywords: str, journals: pd.DataFrame, area: str, context: str, rating: str, field_filter: str, top_n: int) -> pd.DataFrame:
    df = journals.copy()
    if context == "ABDC context only":
        df = df[df["abdc_rating"].map(clean).ne("")]
    if context == "ABS/AJG context only":
        df = df[df["ajg_2024"].map(clean).ne("")]
    if rating != "All":
        df = df[df["abdc_rating"].eq(rating) | df["ajg_2024"].eq(rating)]
    if field_filter != "All":
        df = df[df["field"].str.contains(re.escape(field_filter), case=False, na=False)]
    if df.empty:
        return df
    query = clean(" ".join([title, abstract, author_keywords, area_terms(title + " " + abstract + " " + author_keywords, area)]))
    df["_text"] = df.apply(journal_text, axis=1)
    try:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=6000)
        matrix = vectorizer.fit_transform([query] + df["_text"].tolist())
        sims = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
        df["Semantic fit"] = np.round(100 * sims / max(float(sims.max()), 1e-9), 2)
    except Exception as exc:
        log_error("recommend", exc)
        df["Semantic fit"] = 0.0
    kws = keywords_from_text(title + " " + abstract + " " + author_keywords, 20)
    lower_text = df["_text"].str.lower()
    matched = [[kw for kw in kws if kw in txt] for txt in lower_text]
    df["Keyword overlap"] = [round(100 * len(x) / max(1, len(kws)), 2) for x in matched]
    df["Matched keywords"] = [", ".join(x[:10]) for x in matched]
    df["Metadata richness"] = df[["field", "official_url", "submission_url", "aims_scope", "typical_topics"]].map(lambda x: bool(clean(x))).mean(axis=1).mul(100).round(2)
    df["Area alignment"] = df["_text"].str.lower().map(lambda txt: min(100, 15 * sum(term in txt for term in AREA_TERMS.get(area, []) if area != "Auto"))) if area != "Auto" else 0
    df["Journal-fit score"] = (0.62 * df["Semantic fit"] + 0.22 * df["Keyword overlap"] + 0.08 * df["Metadata richness"] + 0.08 * df["Area alignment"]).round(2)
    df["Suitability band"] = pd.cut(df["Journal-fit score"], bins=[-1, 38, 55, 75, 101], labels=["Weak evidence", "Exploratory", "Moderate fit", "Strong fit"])
    df["Context signals"] = df.apply(lambda r: "; ".join(x for x in [f"ABDC {clean(r.get('abdc_rating'))}" if clean(r.get("abdc_rating")) else "", f"AJG {clean(r.get('ajg_2024'))}" if clean(r.get("ajg_2024")) else ""] if x) or "Metadata only", axis=1)
    df["Official journal search"] = df["journal_title"].map(lambda j: search_url(f'"{j}" journal aims scope submission'))
    df["Scholar search"] = df["journal_title"].map(lambda j: "https://scholar.google.com/scholar?q=" + urllib.parse.quote_plus(f'"{j}"'))
    cols = ["journal_title", "Journal-fit score", "Suitability band", "Semantic fit", "Keyword overlap", "Area alignment", "Metadata richness", "field", "Context signals", "publisher", "issn", "eissn", "official_url", "submission_url", "Matched keywords", "source_file", "Official journal search", "Scholar search"]
    return df.sort_values("Journal-fit score", ascending=False).head(top_n)[[c for c in cols if c in df.columns]]


def report_md(title: str, abstract: str, keywords: str, results: pd.DataFrame) -> str:
    lines = ["# JournalFit Studio Report", "", f"Generated: {datetime.now():%Y-%m-%d %H:%M}", f"Tool: {APP_NAME} v{APP_VERSION}", "", "## Manuscript", f"**Title:** {title}", f"**Keywords:** {keywords}", "", abstract, "", "## Shortlisted journals"]
    for i, (_, r) in enumerate(results.iterrows(), 1):
        lines += ["", f"### {i}. {clean(r.get('journal_title'))}", f"- Score: {r.get('Journal-fit score')}", f"- Band: {r.get('Suitability band')}", f"- Field: {r.get('field')}", f"- Context: {r.get('Context signals')}"]
    return "\n".join(lines)


def main() -> None:
    ensure_dirs()
    st.set_page_config(page_title=f"{APP_NAME} | Journal discovery", page_icon="📚", layout="wide")
    st.markdown("""
    <style>
    .stApp{background:linear-gradient(135deg,#f8fbff,#fff7ed 55%,#f5f3ff)}
    .hero{border:1px solid #e0e7ff;border-radius:26px;padding:28px;background:#ffffffd9;box-shadow:0 20px 45px #0f172a18}.hero h1{font-size:44px;margin:0}.grad{background:linear-gradient(90deg,#2563eb,#7c3aed,#ec4899,#f97316);-webkit-background-clip:text;color:transparent}.badge{display:inline-block;border:1px solid #e0e7ff;border-radius:999px;padding:8px 12px;margin:12px 8px 0 0;background:white;color:#3730a3;font-weight:800;font-size:12px}.notice{border-left:5px solid #f97316;background:white;border-radius:14px;padding:14px 18px;margin:16px 0}.section-title{font-size:28px;font-weight:900;margin-top:24px}.footer{margin-top:36px;padding:22px;border-radius:22px;background:#0f172a;color:#e2e8f0}.footer a{color:#bfdbfe}
    section[data-testid="stSidebar"]{background:linear-gradient(180deg,#07162f,#111827 52%,#20133b);color:white}section[data-testid="stSidebar"] *{color:inherit}section[data-testid="stSidebar"] [data-baseweb="select"] *{color:#0f172a!important}
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(f"### 📚 {APP_NAME}")
        st.caption("CSV, XLSX, and XLS journal metadata are supported.")
        files = metadata_files()
        selected_paths: tuple[str, ...] = tuple()
        if files:
            selected = st.multiselect("Local journal metadata files", [p.name for p in files], default=[files[0].name])
            selected_paths = tuple(str(p) for p in files if p.name in selected)
        else:
            st.info("No local metadata found in data/. Upload a file below.")
        uploaded_meta = st.file_uploader("Upload journal metadata", type=["csv", "xlsx", "xls"])
        uploaded_enrich = st.file_uploader("Optional enrichment CSV", type=["csv"])
        sheet_choice = st.selectbox("Excel sheet", ["Auto", "All sheets"])
        context = st.selectbox("Context filter", ["All metadata", "ABDC context only", "ABS/AJG context only"])
        rating = st.selectbox("Rating/context value", ["All", "A*", "A", "B", "C", "4*", "4", "3", "2", "1"])
        area = st.selectbox("Research-area support", ["Auto"] + list(AREA_TERMS))
        top_n = st.slider("Number of journals", 5, 100, 30, 5)
        with st.expander("App health"):
            st.json({"version": APP_VERSION, "metadata_files_detected": len(files), "available_metadata_files": [p.name for p in files], "supported_extensions": sorted(SUPPORTED_EXTENSIONS)})

    st.markdown(f"<div class='hero'><h1>JournalFit <span class='grad'>Studio</span></h1><p>Researcher-first journal discovery using manuscript title, abstract, keywords, research area, and local journal metadata.</p><span class='badge'>CSV/XLSX/XLS metadata</span><span class='badge'>No API keys</span><span class='badge'>Responsible use</span><span class='badge'>© {AUTHOR}</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='notice'><b>Integrity note:</b> This is decision support only. Always verify official journal pages, aims and scope, fees, indexing, and author guidelines.</div>", unsafe_allow_html=True)

    local_df = load_local(selected_paths, sheet_choice)
    upload_df = load_upload(uploaded_meta, sheet_choice)
    enrich_df = load_enrichment(uploaded_enrich)
    frames = [x for x in [local_df, upload_df, enrich_df] if not x.empty]
    journals = merge_records(pd.concat(frames, ignore_index=True)) if frames else pd.DataFrame(columns=CANONICAL + ["title_key"])

    if "parsed" not in st.session_state:
        st.session_state.parsed = {"title": "", "abstract": "", "keywords": ""}
    if "results" not in st.session_state:
        st.session_state.results = None

    st.markdown("<div class='section-title'>1. Manuscript input</div>", unsafe_allow_html=True)
    left, right = st.columns([2, 1])
    with right:
        manuscript = st.file_uploader("Optional: upload manuscript", type=["pdf", "docx", "txt"])
        if manuscript:
            st.session_state.parsed = extract_manuscript(manuscript)
            st.success("Manuscript parsed. Please review the extracted text.")
        fields = ["All"] + (sorted([x for x in journals["field"].map(clean).unique().tolist() if x])[:250] if not journals.empty else [])
        field_filter = st.selectbox("Field/category filter", fields)
        st.caption("Detected research-area signals")
        st.dataframe(classify_area(" ".join(st.session_state.parsed.values())).head(5), use_container_width=True, hide_index=True)
    with left:
        title = st.text_input("Manuscript title", value=st.session_state.parsed.get("title", ""))
        abstract = st.text_area("Abstract", value=st.session_state.parsed.get("abstract", ""), height=250)
        keywords = st.text_input("Author keywords", value=st.session_state.parsed.get("keywords", ""))
        run = st.button("🔎 Find suitable journals")

    if run:
        if journals.empty:
            st.error("No journal metadata is available. Add CSV/XLSX/XLS metadata to data/ or upload a metadata file from the sidebar.")
        elif len(clean(title + abstract + keywords)) < 60:
            st.warning("Please provide a more complete title, abstract, or keyword set.")
        else:
            st.session_state.results = recommend(title, abstract, keywords, journals, area, context, rating, field_filter, top_n)

    results = st.session_state.results
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Journal records", f"{len(journals):,}")
    c2.metric("Fields detected", f"{journals['field'].map(clean).ne('').sum():,}" if not journals.empty else "0")
    c3.metric("URLs available", f"{journals['official_url'].map(clean).ne('').sum():,}" if not journals.empty else "0")
    c4.metric("Recommendations", f"{len(results):,}" if results is not None else "0")

    st.markdown("<div class='section-title'>2. Suitable journal shortlist</div>", unsafe_allow_html=True)
    if results is None:
        st.info("Run journal discovery to generate a shortlist.")
    elif results.empty:
        st.warning("No journals matched the current filters.")
    else:
        visible = results.rename(columns={"journal_title": "Journal", "field": "Field", "publisher": "Publisher"})
        st.dataframe(visible[[c for c in ["Journal", "Journal-fit score", "Suitability band", "Semantic fit", "Keyword overlap", "Area alignment", "Metadata richness", "Field", "Context signals", "Publisher", "official_url", "submission_url"] if c in visible]], use_container_width=True, hide_index=True)
        for i, (_, row) in enumerate(results.head(10).iterrows(), 1):
            with st.expander(f"{i}. {clean(row.get('journal_title'))} — {row.get('Suitability band')} ({row.get('Journal-fit score')})", expanded=i == 1):
                col1, col2 = st.columns([1.4, 1])
                with col1:
                    st.markdown(f"**Why it appeared:** semantic fit `{row.get('Semantic fit')}`, keyword overlap `{row.get('Keyword overlap')}`, metadata richness `{row.get('Metadata richness')}`.")
                    st.markdown(f"**Matched keywords:** {clean(row.get('Matched keywords')) or 'No direct keyword evidence in current metadata.'}")
                    st.markdown("**Before submission:** verify aims/scope, article type, fees, indexing, ethics, and author guidelines from the official journal page.")
                with col2:
                    official = safe_url(row.get("official_url"))
                    submission = safe_url(row.get("submission_url"))
                    st.link_button("Official journal page" if official else "Search official page", official or row.get("Official journal search"), use_container_width=True)
                    st.link_button("Submission information" if submission else "Search submission info", submission or row.get("Official journal search"), use_container_width=True)
                    st.link_button("Scholar search", row.get("Scholar search"), use_container_width=True)
        st.download_button("⬇️ Download journal-fit report", report_md(title, abstract, keywords, results), "journalfit_report.md", "text/markdown")
        st.download_button("⬇️ Download shortlist CSV", results.to_csv(index=False).encode("utf-8"), "journalfit_shortlist.csv", "text/csv")

    st.markdown(f"<div class='footer'><b>{APP_NAME} v{APP_VERSION}</b> · Developed by {AUTHOR}.<br/>Live app: <a href='{APP_URL}'>{APP_URL}</a><br/>GitHub: <a href='{GITHUB_URL}'>{GITHUB_URL}</a></div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
