from __future__ import annotations

import io
import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Sequence

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional dependency guard
    PdfReader = None

try:
    import docx
except Exception:  # pragma: no cover - optional dependency guard
    docx = None

APP_NAME = "JournalFit Studio"
APP_VERSION = "5.0.0"
SUPPORTED_METADATA_EXTENSIONS = {".csv", ".xlsx", ".xls"}
SUPPORTED_MANUSCRIPT_EXTENSIONS = {".pdf", ".docx", ".txt"}

ALIASES = {
    "journal_title": [
        "journal title", "title", "journal", "journal name", "source title",
        "publication title", "periodical title",
    ],
    "publisher": ["publisher", "publisher name"],
    "issn": ["issn", "print issn", "p-issn", "issn-l"],
    "eissn": ["eissn", "online issn", "electronic issn", "issnonline"],
    "field": ["field", "discipline", "category", "subject", "subject area", "research area", "abdc field"],
    "abdc_rating": ["2025 rating", "abdc rating", "abdc category", "abdc", "rating"],
    "ajg_2024": ["ajg 2024", "abs 2024", "cabs 2024", "ajg rating", "abs rating", "ajg", "abs"],
    "official_url": ["journal url", "url", "homepage", "official url", "journal website", "website"],
    "submission_url": ["link to submission", "submission link", "submission url", "author guidelines", "guide for authors"],
    "aims_scope": ["aims scope", "aims and scope", "scope", "journal scope", "description", "about journal", "aims"],
    "preferred_methods": ["preferred methods", "methods", "methodology"],
    "typical_topics": ["typical topics", "topics", "keywords", "journal keywords", "themes"],
    "editorial_notes": ["editorial notes", "notes", "remarks"],
    "verification_status": ["verified url status", "verification status", "verified", "data status"],
}

CANONICAL_COLUMNS = list(ALIASES) + ["source_file", "source_sheet", "source_kind"]

AREA_TERMS = {
    "Information Systems / Analytics": [
        "analytics", "data", "digital", "algorithm", "artificial intelligence",
        "machine learning", "information system", "big data", "decision support",
    ],
    "Healthcare Management": [
        "healthcare", "hospital", "patient", "clinical", "health", "medical",
        "care delivery", "health system",
    ],
    "Strategy / Governance": [
        "strategy", "governance", "policy", "responsible", "accountability",
        "institution", "innovation", "regulation",
    ],
    "Finance": ["finance", "banking", "investment", "risk", "portfolio", "fintech", "accounting"],
    "Marketing": ["marketing", "consumer", "brand", "retail", "customer", "advertising"],
    "Operations / Supply Chain": [
        "operations", "supply chain", "logistics", "quality", "process", "inventory", "procurement",
    ],
    "HRM / OB": [
        "human resource", "employee", "leadership", "team", "workplace", "organizational behavior", "talent",
    ],
    "Economics": ["economics", "econometric", "policy", "welfare", "labour", "macroeconomic", "microeconomic"],
    "Education / Learning": [
        "education", "learning", "teaching", "student", "pedagogy", "assessment", "curriculum",
    ],
    "Tourism": ["tourism", "hospitality", "travel", "destination", "hotel"],
}

RATING_ORDER = {"A*": 8, "4*": 8, "A": 7, "4": 7, "3": 6, "B": 5, "2": 4, "C": 3, "1": 2}


@dataclass(frozen=True)
class MatchWeights:
    semantic: float = 0.58
    keyword: float = 0.22
    metadata: float = 0.10
    area: float = 0.10

    def normalized(self) -> "MatchWeights":
        total = self.semantic + self.keyword + self.metadata + self.area
        if total <= 0:
            return MatchWeights()
        return MatchWeights(
            semantic=self.semantic / total,
            keyword=self.keyword / total,
            metadata=self.metadata / total,
            area=self.area / total,
        )


def clean(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return re.sub(r"\s+", " ", str(value).replace("\n", " ").replace("\r", " ").replace("\t", " ")).strip()


def norm_col(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean(value).lower()).strip()


def norm_title(value: object) -> str:
    text = clean(value).lower().replace("&", " and ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def safe_url(value: object) -> str:
    text = clean(value)
    if not text:
        return ""
    if text.startswith(("http://", "https://")):
        return text
    return f"https://{text}" if "." in text and " " not in text else ""


def search_url(query: str) -> str:
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)


def scholar_url(journal_title: str) -> str:
    return "https://scholar.google.com/scholar?q=" + urllib.parse.quote_plus(f'"{journal_title}"')


def empty_journal_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=CANONICAL_COLUMNS + ["title_key"])


def best_header(preview: pd.DataFrame) -> int:
    tokens = ["journal", "publisher", "issn", "rating", "ajg", "abdc", "field", "scope", "url"]
    scores: list[float] = []
    for _, row in preview.iterrows():
        values = [clean(x) for x in row.tolist()]
        row_text = " | ".join(values).lower()
        token_score = sum(token in row_text for token in tokens)
        populated_score = min(3, sum(bool(value) for value in values) / 2)
        scores.append(token_score + populated_score)
    return int(np.argmax(scores)) if scores else 0


def read_table(file_bytes: bytes, filename: str, sheet: str = "Auto") -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_METADATA_EXTENSIONS:
        raise ValueError(f"Unsupported metadata format: {suffix or 'unknown'}")

    if suffix == ".csv":
        last_error: Optional[Exception] = None
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                preview = pd.read_csv(io.BytesIO(file_bytes), header=None, nrows=30, encoding=encoding)
                header = best_header(preview)
                return (
                    pd.read_csv(io.BytesIO(file_bytes), header=header, encoding=encoding)
                    .dropna(how="all")
                    .dropna(axis=1, how="all")
                )
            except Exception as exc:
                last_error = exc
        raise ValueError(f"CSV could not be read: {last_error}") from last_error

    workbook = pd.ExcelFile(io.BytesIO(file_bytes))
    selected_sheet = workbook.sheet_names[0] if sheet == "Auto" else sheet
    if selected_sheet not in workbook.sheet_names:
        raise ValueError(f"Sheet '{selected_sheet}' was not found in {filename}")
    preview = pd.read_excel(io.BytesIO(file_bytes), sheet_name=selected_sheet, header=None, nrows=30)
    header = best_header(preview)
    return (
        pd.read_excel(io.BytesIO(file_bytes), sheet_name=selected_sheet, header=header)
        .dropna(how="all")
        .dropna(axis=1, how="all")
    )


def sheets_for(file_bytes: bytes, filename: str) -> list[str]:
    if Path(filename).suffix.lower() == ".csv":
        return ["CSV"]
    return pd.ExcelFile(io.BytesIO(file_bytes)).sheet_names


def find_column(df: pd.DataFrame, target: str) -> Optional[str]:
    lookup = {norm_col(column): column for column in df.columns}
    for alias in ALIASES[target]:
        key = norm_col(alias)
        if key in lookup:
            return lookup[key]
    for normalized, original in lookup.items():
        for alias in ALIASES[target]:
            alias_key = norm_col(alias)
            if len(alias_key) > 3 and (alias_key in normalized or normalized in alias_key):
                return original
    return None


def canonicalize(raw: pd.DataFrame, source_file: str, source_sheet: str) -> pd.DataFrame:
    if raw.empty:
        return empty_journal_frame()

    raw = raw.copy()
    raw.columns = [clean(column) for column in raw.columns]
    output = pd.DataFrame(index=raw.index)

    for canonical_column in ALIASES:
        detected = find_column(raw, canonical_column)
        output[canonical_column] = raw[detected] if detected else ""

    if output["journal_title"].map(clean).eq("").all():
        candidate_columns = sorted(
            raw.columns,
            key=lambda column: raw[column].dropna().astype(str).head(20).str.len().median(),
            reverse=True,
        )
        if candidate_columns:
            output["journal_title"] = raw[candidate_columns[0]]

    for column in output.columns:
        output[column] = output[column].map(clean)

    output["official_url"] = output["official_url"].map(safe_url)
    output["submission_url"] = output["submission_url"].map(safe_url)
    output["source_file"] = source_file
    output["source_sheet"] = source_sheet

    source_description = f"{source_file} {' '.join(raw.columns)}".lower()
    if "ajg" in source_description or "abs" in source_description:
        output["source_kind"] = "ABS/AJG context"
    elif "abdc" in source_description:
        output["source_kind"] = "ABDC context"
    else:
        output["source_kind"] = "Journal metadata"

    output = output[output["journal_title"].map(clean).ne("")].copy()
    output["title_key"] = output["journal_title"].map(norm_title)
    return output[output["title_key"].ne("")]


def merge_records(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return empty_journal_frame()

    rows: list[dict[str, object]] = []
    for _, group in df.groupby("title_key", dropna=False, sort=False):
        row: dict[str, object] = {}
        for column in group.columns:
            values = [clean(value) for value in group[column].tolist() if clean(value)]
            unique_values = list(dict.fromkeys(values))
            if column in {"source_file", "source_sheet", "source_kind"}:
                row[column] = "; ".join(sorted(set(unique_values)))
            elif column in {"aims_scope", "typical_topics", "preferred_methods", "editorial_notes"}:
                row[column] = max(unique_values, key=len) if unique_values else ""
            else:
                row[column] = unique_values[0] if unique_values else ""
        rows.append(row)

    output = pd.DataFrame(rows)
    for column in CANONICAL_COLUMNS:
        if column not in output.columns:
            output[column] = ""
    output["title_key"] = output["journal_title"].map(norm_title)
    return output.reset_index(drop=True)


def load_metadata_bytes(file_bytes: bytes, filename: str, all_sheets: bool = False) -> pd.DataFrame:
    sheets = sheets_for(file_bytes, filename)
    selected_sheets = sheets if all_sheets else sheets[:1]
    frames = [canonicalize(read_table(file_bytes, filename, sheet), filename, sheet) for sheet in selected_sheets]
    frames = [frame for frame in frames if not frame.empty]
    return merge_records(pd.concat(frames, ignore_index=True)) if frames else empty_journal_frame()


def load_metadata_paths(paths: Sequence[str], all_sheets: bool = False) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path_text in paths:
        path = Path(path_text)
        if not path.exists() or path.suffix.lower() not in SUPPORTED_METADATA_EXTENSIONS:
            continue
        frame = load_metadata_bytes(path.read_bytes(), path.name, all_sheets=all_sheets)
        if not frame.empty:
            frames.append(frame)
    return merge_records(pd.concat(frames, ignore_index=True)) if frames else empty_journal_frame()


def _extract_text(file_bytes: bytes, filename: str, max_pdf_pages: int = 12) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        if PdfReader is None:
            raise RuntimeError("PDF support is unavailable because pypdf is not installed.")
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages[:max_pdf_pages])
    if suffix == ".docx":
        if docx is None:
            raise RuntimeError("DOCX support is unavailable because python-docx is not installed.")
        document = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    if suffix == ".txt":
        return file_bytes.decode("utf-8", errors="ignore")
    raise ValueError(f"Unsupported manuscript format: {suffix or 'unknown'}")


def _looks_like_author_line(line: str) -> bool:
    lowered = line.lower()
    return any(token in lowered for token in ("@", "university", "institute", "department", "corresponding author", "orcid"))


def extract_manuscript_bytes(file_bytes: bytes, filename: str) -> dict[str, str]:
    text = _extract_text(file_bytes, filename)
    lines = [clean(line) for line in text.splitlines() if clean(line)]
    if not lines:
        return {"title": "", "abstract": "", "keywords": ""}

    abstract_index = next((index for index, line in enumerate(lines[:80]) if re.match(r"(?i)^abstract\b", line)), None)
    title_candidates = lines[:abstract_index] if abstract_index not in (None, 0) else lines[:12]
    title_candidates = [
        line for line in title_candidates
        if 20 <= len(line) <= 260 and not _looks_like_author_line(line) and not re.match(r"(?i)^(abstract|keywords?|introduction)\b", line)
    ]
    title = max(title_candidates, key=len) if title_candidates else lines[0][:260]

    joined = "\n".join(lines)
    abstract_match = re.search(
        r"(?is)\babstract\b[:\s\-]*(.*?)(?=\bkeywords?\b|\bkey\s+words\b|\bintroduction\b|\n\s*1\.?\s+)",
        joined,
    )
    abstract = clean(abstract_match.group(1))[:7000] if abstract_match else clean(" ".join(lines[1:12]))[:3500]

    keyword_match = re.search(
        r"(?is)\bkey\s*words?\b[:\s\-]*(.*?)(?=\n\s*\d|\bintroduction\b|\bbackground\b|$)",
        joined,
    )
    keywords = clean(keyword_match.group(1))[:700] if keyword_match else "; ".join(keywords_from_text(f"{title} {abstract}", 8))
    return {"title": title, "abstract": abstract, "keywords": keywords}


def keywords_from_text(text: str, n: int = 20) -> list[str]:
    text = clean(text)
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
        terms = np.array(vectorizer.get_feature_names_out())
        scores = matrix.toarray()[0]
        order = np.lexsort((-np.char.str_len(terms.astype(str)), -scores))
        return [clean(terms[index]).lower() for index in order[:n] if len(clean(terms[index])) > 3]
    except (ValueError, AttributeError):
        return []


def classify_area(text: str) -> pd.DataFrame:
    lowered = clean(text).lower()
    rows = []
    for area, terms in AREA_TERMS.items():
        hits = [term for term in terms if term in lowered]
        rows.append({"Area": area, "Evidence count": len(hits), "Matched terms": ", ".join(hits)})
    return pd.DataFrame(rows).sort_values(["Evidence count", "Area"], ascending=[False, True]).reset_index(drop=True)


def inferred_area(text: str) -> str:
    classified = classify_area(text)
    if classified.empty or int(classified.iloc[0]["Evidence count"]) == 0:
        return "Unclear"
    return str(classified.iloc[0]["Area"])


def area_query_terms(text: str, area: str) -> str:
    if area != "Auto":
        return " ".join(AREA_TERMS.get(area, []))
    classified = classify_area(text)
    top_areas = classified[classified["Evidence count"] > 0].head(3)["Area"].tolist()
    return " ".join(term for top_area in top_areas for term in AREA_TERMS.get(top_area, []))


def journal_text(row: pd.Series) -> str:
    title = clean(row.get("journal_title"))
    parts = [
        title, title, row.get("field", ""), row.get("publisher", ""), row.get("aims_scope", ""),
        row.get("preferred_methods", ""), row.get("typical_topics", ""), row.get("editorial_notes", ""),
    ]
    return clean(" ".join(map(str, parts)))


def data_quality_summary(journals: pd.DataFrame) -> dict[str, object]:
    if journals.empty:
        return {
            "records": 0, "unique_fields": 0, "scope_coverage": 0.0,
            "url_coverage": 0.0, "ranking_coverage": 0.0, "demo_records": 0,
        }
    records = len(journals)
    demo_mask = journals["verification_status"].str.contains("demo", case=False, na=False) | journals["editorial_notes"].str.contains("demo row", case=False, na=False)
    return {
        "records": records,
        "unique_fields": int(journals["field"].map(clean).replace("", np.nan).nunique()),
        "scope_coverage": round(100 * journals["aims_scope"].map(clean).ne("").mean(), 1),
        "url_coverage": round(100 * journals["official_url"].map(clean).ne("").mean(), 1),
        "ranking_coverage": round(100 * (journals["abdc_rating"].map(clean).ne("") | journals["ajg_2024"].map(clean).ne("")).mean(), 1),
        "demo_records": int(demo_mask.sum()),
    }


def _filter_journals(
    journals: pd.DataFrame,
    context: str,
    ratings: Sequence[str],
    field_filter: str,
) -> pd.DataFrame:
    filtered = journals.copy()
    if context == "ABDC only":
        filtered = filtered[filtered["abdc_rating"].map(clean).ne("")]
    elif context == "ABS/AJG only":
        filtered = filtered[filtered["ajg_2024"].map(clean).ne("")]

    clean_ratings = {clean(rating).upper() for rating in ratings if clean(rating) and rating != "All"}
    if clean_ratings:
        abdc = filtered["abdc_rating"].map(lambda value: clean(value).upper())
        ajg = filtered["ajg_2024"].map(lambda value: clean(value).upper())
        filtered = filtered[abdc.isin(clean_ratings) | ajg.isin(clean_ratings)]

    if field_filter != "All":
        filtered = filtered[filtered["field"].str.contains(re.escape(field_filter), case=False, na=False)]
    return filtered.copy()


def _keyword_overlap(query_keywords: Sequence[str], journal_text_value: str) -> tuple[float, str]:
    lowered = journal_text_value.lower()
    matched = [keyword for keyword in query_keywords if keyword in lowered]
    score = 100 * len(matched) / max(1, len(query_keywords))
    return round(score, 2), ", ".join(matched[:12])


def _metadata_richness(row: pd.Series) -> float:
    fields = ["field", "official_url", "submission_url", "aims_scope", "typical_topics", "preferred_methods"]
    return round(100 * sum(bool(clean(row.get(field))) for field in fields) / len(fields), 2)


def _area_alignment(journal_text_value: str, area: str, manuscript_text: str) -> float:
    if area == "Auto":
        detected = inferred_area(manuscript_text)
        if detected == "Unclear":
            return 0.0
        terms = AREA_TERMS.get(detected, [])
    else:
        terms = AREA_TERMS.get(area, [])
    if not terms:
        return 0.0
    hits = sum(term in journal_text_value.lower() for term in terms)
    return round(100 * hits / len(terms), 2)


def _evidence_confidence(row: pd.Series) -> str:
    richness = float(row.get("Metadata richness", 0))
    scope_present = bool(clean(row.get("aims_scope")))
    demo = "demo" in clean(row.get("verification_status")).lower() or "demo row" in clean(row.get("editorial_notes")).lower()
    if demo:
        return "Demo data"
    if richness >= 80 and scope_present:
        return "High metadata confidence"
    if richness >= 50:
        return "Moderate metadata confidence"
    return "Limited metadata confidence"


def recommend(
    title: str,
    abstract: str,
    author_keywords: str,
    journals: pd.DataFrame,
    area: str = "Auto",
    context: str = "All metadata",
    ratings: Sequence[str] = (),
    field_filter: str = "All",
    top_n: int = 20,
    weights: MatchWeights = MatchWeights(),
) -> pd.DataFrame:
    manuscript_text = clean(" ".join([title, abstract, author_keywords]))
    if len(manuscript_text) < 60:
        raise ValueError("Provide a fuller title, abstract, or keyword set before matching journals.")
    if journals.empty:
        return journals.copy()

    filtered = _filter_journals(journals, context=context, ratings=ratings, field_filter=field_filter)
    if filtered.empty:
        return filtered

    query = clean(f"{manuscript_text} {area_query_terms(manuscript_text, area)}")
    filtered["_journal_text"] = filtered.apply(journal_text, axis=1)

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=8000,
        sublinear_tf=True,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9\-]{2,}\b",
    )
    matrix = vectorizer.fit_transform([query] + filtered["_journal_text"].tolist())
    similarities = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
    filtered["Semantic fit"] = np.round(100 * similarities, 2)

    if len(similarities) > 1:
        order = pd.Series(similarities).rank(pct=True, method="average").to_numpy()
        filtered["Relative semantic rank"] = np.round(100 * order, 2)
    else:
        filtered["Relative semantic rank"] = np.round(100 * similarities, 2)

    query_keywords = keywords_from_text(manuscript_text, 24)
    overlaps = [_keyword_overlap(query_keywords, text) for text in filtered["_journal_text"]]
    filtered["Keyword overlap"] = [score for score, _ in overlaps]
    filtered["Matched keywords"] = [keywords for _, keywords in overlaps]
    filtered["Metadata richness"] = filtered.apply(_metadata_richness, axis=1)
    filtered["Area alignment"] = filtered["_journal_text"].map(lambda text: _area_alignment(text, area, manuscript_text))

    normalized_weights = weights.normalized()
    semantic_signal = 0.75 * filtered["Semantic fit"] + 0.25 * filtered["Relative semantic rank"]
    filtered["Journal-fit score"] = (
        normalized_weights.semantic * semantic_signal
        + normalized_weights.keyword * filtered["Keyword overlap"]
        + normalized_weights.metadata * filtered["Metadata richness"]
        + normalized_weights.area * filtered["Area alignment"]
    ).round(2).clip(0, 100)

    filtered["Suitability band"] = pd.cut(
        filtered["Journal-fit score"],
        bins=[-0.01, 30, 50, 70, 100],
        labels=["Weak evidence", "Exploratory", "Moderate fit", "Strong fit"],
        include_lowest=True,
    ).astype(str)
    filtered["Context signals"] = filtered.apply(
        lambda row: "; ".join(
            signal for signal in (
                f"ABDC {clean(row.get('abdc_rating'))}" if clean(row.get("abdc_rating")) else "",
                f"AJG {clean(row.get('ajg_2024'))}" if clean(row.get("ajg_2024")) else "",
            ) if signal
        ) or "No ranking metadata",
        axis=1,
    )
    filtered["Evidence confidence"] = filtered.apply(_evidence_confidence, axis=1)
    filtered["Official journal search"] = filtered["journal_title"].map(
        lambda journal: search_url(f'"{journal}" journal aims scope submission')
    )
    filtered["Scholar search"] = filtered["journal_title"].map(scholar_url)
    filtered["Rank priority"] = filtered.apply(
        lambda row: max(RATING_ORDER.get(clean(row.get("abdc_rating")).upper(), 0), RATING_ORDER.get(clean(row.get("ajg_2024")).upper(), 0)),
        axis=1,
    )

    output_columns = [
        "journal_title", "Journal-fit score", "Suitability band", "Evidence confidence",
        "Semantic fit", "Relative semantic rank", "Keyword overlap", "Area alignment",
        "Metadata richness", "field", "Context signals", "publisher", "issn", "eissn",
        "official_url", "submission_url", "aims_scope", "preferred_methods", "typical_topics",
        "editorial_notes", "verification_status", "Matched keywords", "source_file",
        "Official journal search", "Scholar search", "Rank priority",
    ]
    return (
        filtered.sort_values(["Journal-fit score", "Rank priority", "Metadata richness"], ascending=[False, False, False])
        .head(max(1, int(top_n)))
        [[column for column in output_columns if column in filtered.columns]]
        .reset_index(drop=True)
    )


def build_markdown_report(title: str, abstract: str, keywords: str, results: pd.DataFrame) -> str:
    lines = [
        f"# {APP_NAME} Report",
        "",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
        f"Tool version: {APP_VERSION}",
        "",
        "> Decision-support output only. Scores are not acceptance probabilities or journal-quality judgments.",
        "",
        "## Manuscript",
        f"**Title:** {clean(title)}",
        f"**Keywords:** {clean(keywords) or 'Not supplied'}",
        "",
        clean(abstract),
        "",
        "## Shortlisted journals",
    ]
    for index, row in results.iterrows():
        lines.extend([
            "",
            f"### {index + 1}. {clean(row.get('journal_title'))}",
            f"- Journal-fit score: {row.get('Journal-fit score')}",
            f"- Suitability band: {row.get('Suitability band')}",
            f"- Evidence confidence: {row.get('Evidence confidence')}",
            f"- Field: {clean(row.get('field')) or 'Not available'}",
            f"- Ranking context: {clean(row.get('Context signals'))}",
            f"- Matched keywords: {clean(row.get('Matched keywords')) or 'No direct overlap found'}",
            f"- Official page: {clean(row.get('official_url')) or clean(row.get('Official journal search'))}",
        ])
    lines.extend([
        "",
        "## Verification checklist",
        "- Confirm aims and scope on the official journal website.",
        "- Confirm accepted article type and methodological fit.",
        "- Verify current indexing/ranking from the official source.",
        "- Check fees, turnaround claims, ethics, and author guidelines.",
    ])
    return "\n".join(lines)


def load_and_merge_sources(sources: Iterable[pd.DataFrame]) -> pd.DataFrame:
    frames = [source for source in sources if source is not None and not source.empty]
    return merge_records(pd.concat(frames, ignore_index=True)) if frames else empty_journal_frame()
