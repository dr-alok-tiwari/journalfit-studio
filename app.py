from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import streamlit as st

from journalfit_core import (
    APP_NAME,
    APP_VERSION,
    AREA_TERMS,
    MatchWeights,
    build_markdown_report,
    classify_area,
    clean,
    data_quality_summary,
    empty_journal_frame,
    extract_manuscript_bytes,
    inferred_area,
    load_and_merge_sources,
    load_metadata_bytes,
    load_metadata_paths,
    recommend,
    safe_url,
)

AUTHOR = "Dr. Alok Tiwari"
APP_URL = "https://journalfit-studio-by-dr-alok-tiwari.streamlit.app/"
GITHUB_URL = "https://github.com/dr-alok-tiwari/journalfit-studio"
PORTFOLIO_URL = "https://dr-alok-tiwari.github.io/"
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
FILE_PRIORITY = [
    "journal_metadata.xlsx", "journal_metadata.csv", "sample_journal_metadata.csv",
    "ABS_Submission_Links.xlsx", "ABDC-Ranking.xlsx",
]

SAMPLE_MANUSCRIPT = {
    "title": "Responsible artificial intelligence adoption in healthcare organizations: A governance and analytics perspective",
    "abstract": (
        "This study examines how healthcare organizations adopt responsible artificial intelligence for clinical and managerial "
        "decision support. We develop and test a governance-oriented model linking data readiness, algorithmic transparency, "
        "leadership support, and institutional accountability to adoption outcomes. Using a mixed-method design, the study combines "
        "survey evidence with interviews from hospital administrators and analytics professionals. The findings contribute to "
        "healthcare management, information systems, and responsible innovation research by clarifying organizational mechanisms "
        "that enable trustworthy AI deployment."
    ),
    "keywords": "responsible AI; healthcare analytics; governance; technology adoption; decision support",
}


def local_metadata_files() -> list[Path]:
    DATA_DIR.mkdir(exist_ok=True)
    priority = {name: index for index, name in enumerate(FILE_PRIORITY)}
    files = [
        path for path in DATA_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in {".csv", ".xlsx", ".xls"} and path.name != "journal_enrichment.csv"
    ]
    return sorted(files, key=lambda path: (priority.get(path.name, 99), path.name.lower()))


@st.cache_data(show_spinner=False)
def cached_local_metadata(file_signatures: tuple[tuple[str, int, int], ...], all_sheets: bool) -> pd.DataFrame:
    paths = [signature[0] for signature in file_signatures]
    return load_metadata_paths(paths, all_sheets=all_sheets)


@st.cache_data(show_spinner=False)
def cached_uploaded_metadata(file_bytes: bytes, filename: str, all_sheets: bool) -> pd.DataFrame:
    return load_metadata_bytes(file_bytes, filename, all_sheets=all_sheets)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root { --ink:#10233f; --muted:#61708a; --line:#dfe7f2; --soft:#f5f8fc; --brand:#5b4bdb; --accent:#ff8a3d; }
        .stApp { background:
            radial-gradient(circle at 3% 0%, rgba(104,82,255,.12), transparent 27rem),
            radial-gradient(circle at 97% 8%, rgba(255,151,73,.13), transparent 25rem),
            linear-gradient(180deg,#fbfcff 0%,#f6f8fc 60%,#fbfcff 100%); color:var(--ink); }
        .block-container { max-width: 1440px; padding-top: 1.2rem; padding-bottom: 3rem; }
        [data-testid="stHeader"] { background: transparent; }
        section[data-testid="stSidebar"] { background:linear-gradient(180deg,#111a34 0%,#17264b 58%,#251b4b 100%); border-right:0; }
        section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 { color:#f7f9ff; }
        section[data-testid="stSidebar"] [data-baseweb="select"] *,
        section[data-testid="stSidebar"] input { color:#12213b !important; }
        .hero { position:relative; overflow:hidden; padding:2.2rem 2.35rem; border:1px solid rgba(91,75,219,.16);
            border-radius:28px; background:rgba(255,255,255,.88); box-shadow:0 26px 70px rgba(25,35,65,.10); }
        .hero:after { content:""; position:absolute; width:280px; height:280px; border-radius:50%; right:-90px; top:-120px;
            background:linear-gradient(135deg,rgba(91,75,219,.24),rgba(255,138,61,.18)); filter:blur(4px); }
        .eyebrow { color:#5b4bdb; font-size:.78rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
        .hero h1 { color:#10233f; font-size:clamp(2.2rem,5vw,4.2rem); line-height:1; margin:.45rem 0 .85rem; letter-spacing:-.055em; }
        .hero h1 span { background:linear-gradient(90deg,#5b4bdb,#8b4fd9,#ff7d45); -webkit-background-clip:text; color:transparent; }
        .hero p { max-width:760px; color:#52627c; font-size:1.06rem; line-height:1.65; margin:0; }
        .chip { display:inline-flex; align-items:center; gap:.4rem; margin:.9rem .45rem 0 0; padding:.48rem .78rem;
            border-radius:999px; border:1px solid #dfe4f2; background:#fff; color:#35445f; font-size:.78rem; font-weight:700; }
        .section-head { margin:1.6rem 0 .75rem; }
        .section-head h2 { margin:0; color:#152744; font-size:1.55rem; letter-spacing:-.025em; }
        .section-head p { margin:.22rem 0 0; color:#6b7890; }
        .soft-card { background:rgba(255,255,255,.92); border:1px solid var(--line); border-radius:20px; padding:1rem 1.1rem;
            box-shadow:0 10px 32px rgba(32,49,82,.06); }
        .alert-demo { background:#fff8ed; border:1px solid #ffd7ad; border-left:5px solid #f58a35; border-radius:16px;
            padding:.9rem 1rem; color:#704319; margin:.85rem 0; }
        .alert-safe { background:#eef8f5; border:1px solid #c8e9df; border-left:5px solid #1d9a76; border-radius:16px;
            padding:.9rem 1rem; color:#205c4c; margin:.85rem 0; }
        .journal-card { background:#fff; border:1px solid #e1e8f2; border-radius:20px; padding:1rem 1.15rem; margin:.55rem 0;
            box-shadow:0 9px 25px rgba(27,42,74,.055); }
        .journal-rank { display:inline-grid; place-items:center; width:32px; height:32px; border-radius:10px; color:#fff;
            background:linear-gradient(135deg,#5b4bdb,#8f55dc); font-weight:800; margin-right:.55rem; }
        .journal-title { color:#152744; font-size:1.08rem; font-weight:800; }
        .journal-meta { color:#6a7890; font-size:.84rem; margin-top:.45rem; }
        .score-pill { float:right; padding:.38rem .7rem; border-radius:999px; background:#eff0ff; color:#4c3ec0; font-weight:800; }
        .footer { margin-top:2.2rem; padding:1.2rem 1.35rem; border-radius:20px; color:#dfe8fb;
            background:linear-gradient(135deg,#111a34,#1c2e58 62%,#38205c); }
        .footer a { color:#ffd4b5; text-decoration:none; }
        div[data-testid="stMetric"] { background:rgba(255,255,255,.9); border:1px solid #e1e8f2; padding:.8rem 1rem; border-radius:17px;
            box-shadow:0 7px 22px rgba(24,40,73,.05); }
        div[data-testid="stForm"] { border:1px solid #dfe7f2; border-radius:22px; padding:1.05rem 1.15rem; background:rgba(255,255,255,.78); }
        .stButton>button, .stFormSubmitButton>button, .stDownloadButton>button { border-radius:12px; min-height:2.75rem; font-weight:750; }
        .stFormSubmitButton>button { border:0; color:#fff; background:linear-gradient(90deg,#5b4bdb,#7653dc 58%,#ff8247); }
        .stTabs [data-baseweb="tab-list"] { gap:.4rem; }
        .stTabs [data-baseweb="tab"] { height:3rem; border-radius:12px 12px 0 0; font-weight:700; }
        @media (max-width: 768px) { .hero { padding:1.45rem; border-radius:21px; } .block-container { padding-left:1rem; padding-right:1rem; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"<div class='section-head'><h2>{html.escape(title)}</h2><p>{html.escape(subtitle)}</p></div>",
        unsafe_allow_html=True,
    )


def initialize_state() -> None:
    defaults = {
        "manuscript_title": "",
        "manuscript_abstract": "",
        "manuscript_keywords": "",
        "results": None,
        "last_query": {},
        "result_context": None,
        "manuscript_upload_key": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_manuscript(values: dict[str, str]) -> None:
    st.session_state.manuscript_title = values.get("title", "")
    st.session_state.manuscript_abstract = values.get("abstract", "")
    st.session_state.manuscript_keywords = values.get("keywords", "")
    st.session_state.results = None


def sidebar_controls(journals: pd.DataFrame) -> dict[str, object]:
    with st.sidebar:
        st.markdown(f"## 📚 {APP_NAME}")
        st.caption("Explainable, local-first journal discovery")
        st.markdown("---")

        st.markdown("### 1 · Journal database")
        files = local_metadata_files()
        selected_paths: list[str] = []
        if files:
            selected_names = st.multiselect(
                "Bundled metadata",
                [path.name for path in files],
                default=[files[0].name],
                help="Choose one or more metadata files stored in the repository's data folder.",
            )
            selected_paths = [str(path) for path in files if path.name in selected_names]
        else:
            st.warning("No bundled metadata found.")

        uploaded_metadata = st.file_uploader(
            "Add your metadata",
            type=["csv", "xlsx", "xls"],
            help="Supported columns include journal title, field, ranking, aims/scope, publisher, and URLs.",
        )
        all_sheets = st.toggle("Read all Excel sheets", value=False)

        st.markdown("### 2 · Matching preferences")
        context = st.selectbox("Ranking context", ["All metadata", "ABDC only", "ABS/AJG only"])
        rating_options = ["A*", "A", "B", "C", "4*", "4", "3", "2", "1"]
        ratings = st.multiselect("Target ratings", rating_options, placeholder="All ratings")
        area = st.selectbox("Research area", ["Auto"] + list(AREA_TERMS))
        top_n = st.slider("Shortlist size", 5, 50, 15, 5)

        fields = ["All"]
        if not journals.empty:
            fields += sorted(value for value in journals["field"].map(clean).unique().tolist() if value)[:300]
        field_filter = st.selectbox("Field/category", fields)

        with st.expander("Advanced scoring"):
            st.caption("Weights are normalized automatically.")
            semantic_weight = st.slider("Semantic evidence", 0, 100, 58, 2)
            keyword_weight = st.slider("Keyword overlap", 0, 100, 22, 2)
            metadata_weight = st.slider("Metadata completeness", 0, 100, 10, 2)
            area_weight = st.slider("Area alignment", 0, 100, 10, 2)

        st.markdown("---")
        st.caption(f"Version {APP_VERSION} · No API key required")

    return {
        "selected_paths": selected_paths,
        "uploaded_metadata": uploaded_metadata,
        "all_sheets": all_sheets,
        "context": context,
        "ratings": ratings,
        "area": area,
        "top_n": top_n,
        "field_filter": field_filter,
        "weights": MatchWeights(semantic_weight, keyword_weight, metadata_weight, area_weight),
    }


def load_journals(selected_paths: list[str], uploaded_metadata, all_sheets: bool) -> tuple[pd.DataFrame, list[str]]:
    messages: list[str] = []
    signatures = tuple(
        (path, Path(path).stat().st_mtime_ns, Path(path).stat().st_size)
        for path in selected_paths if Path(path).exists()
    )
    local_df = cached_local_metadata(signatures, all_sheets) if signatures else empty_journal_frame()

    uploaded_df = empty_journal_frame()
    if uploaded_metadata is not None:
        try:
            uploaded_df = cached_uploaded_metadata(uploaded_metadata.getvalue(), uploaded_metadata.name, all_sheets)
        except Exception as exc:
            messages.append(f"Could not read {uploaded_metadata.name}: {exc}")

    return load_and_merge_sources([local_df, uploaded_df]), messages


def manuscript_panel() -> tuple[str, str, str, bool]:
    section_header("Describe your manuscript", "Paste the core text or extract it from a PDF, DOCX, or TXT file.")
    upload_col, action_col = st.columns([2.2, 1])
    with upload_col:
        manuscript = st.file_uploader(
            "Upload manuscript (optional)",
            type=["pdf", "docx", "txt"],
            key=f"manuscript_{st.session_state.manuscript_upload_key}",
        )
    with action_col:
        st.write("")
        st.write("")
        extract_clicked = st.button("Extract manuscript text", use_container_width=True, disabled=manuscript is None)

    if extract_clicked and manuscript is not None:
        try:
            with st.spinner("Extracting title, abstract, and keywords…"):
                set_manuscript(extract_manuscript_bytes(manuscript.getvalue(), manuscript.name))
            st.success("Text extracted. Review it before running the match.")
        except Exception as exc:
            st.error(f"Manuscript extraction failed: {exc}")

    utility_left, utility_middle, utility_right = st.columns([1, 1, 3])
    with utility_left:
        if st.button("Load sample", use_container_width=True):
            set_manuscript(SAMPLE_MANUSCRIPT)
            st.rerun()
    with utility_middle:
        if st.button("Clear", use_container_width=True):
            set_manuscript({"title": "", "abstract": "", "keywords": ""})
            st.session_state.manuscript_upload_key += 1
            st.rerun()
    with utility_right:
        total_chars = len(clean(st.session_state.manuscript_title + st.session_state.manuscript_abstract + st.session_state.manuscript_keywords))
        st.caption(f"Current manuscript evidence: {total_chars:,} characters")

    with st.form("journal_match_form", clear_on_submit=False):
        title = st.text_input("Manuscript title", key="manuscript_title", placeholder="Enter the complete manuscript title")
        abstract = st.text_area(
            "Abstract",
            key="manuscript_abstract",
            height=240,
            placeholder="Paste a structured abstract or a clear summary of the research question, context, method, and contribution.",
        )
        keywords = st.text_input(
            "Author keywords",
            key="manuscript_keywords",
            placeholder="e.g., responsible AI; healthcare analytics; governance",
        )
        submitted = st.form_submit_button("✨ Generate journal shortlist", use_container_width=True)
    return title, abstract, keywords, submitted


def overview_metrics(journals: pd.DataFrame, results: pd.DataFrame | None) -> None:
    quality = data_quality_summary(journals)
    cols = st.columns(5)
    cols[0].metric("Journal records", f"{quality['records']:,}")
    cols[1].metric("Unique fields", f"{quality['unique_fields']:,}")
    cols[2].metric("Scope coverage", f"{quality['scope_coverage']:.0f}%")
    cols[3].metric("Official URLs", f"{quality['url_coverage']:.0f}%")
    cols[4].metric("Shortlisted", f"{len(results):,}" if results is not None else "0")

    if quality["demo_records"]:
        st.markdown(
            f"<div class='alert-demo'><b>Demo-data mode:</b> {quality['demo_records']} of {quality['records']} records are marked as examples. "
            "Upload verified journal metadata before using the shortlist for a real submission decision.</div>",
            unsafe_allow_html=True,
        )
    elif quality["records"]:
        st.markdown(
            "<div class='alert-safe'><b>Local-first analysis:</b> Manuscript text and uploaded metadata are processed in the running app session. "
            "No external AI API is required by this application.</div>",
            unsafe_allow_html=True,
        )


def results_table(results: pd.DataFrame) -> None:
    visible = results.rename(columns={
        "journal_title": "Journal", "field": "Field", "publisher": "Publisher",
        "official_url": "Official page", "submission_url": "Submission page",
    })
    columns = [
        "Journal", "Journal-fit score", "Suitability band", "Evidence confidence",
        "Semantic fit", "Keyword overlap", "Field", "Context signals", "Publisher",
        "Official page", "Submission page",
    ]
    st.dataframe(
        visible[[column for column in columns if column in visible.columns]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Journal-fit score": st.column_config.ProgressColumn("Fit score", min_value=0, max_value=100, format="%.1f"),
            "Semantic fit": st.column_config.ProgressColumn("Semantic", min_value=0, max_value=100, format="%.1f"),
            "Keyword overlap": st.column_config.ProgressColumn("Keywords", min_value=0, max_value=100, format="%.1f"),
            "Official page": st.column_config.LinkColumn("Official page", display_text="Open"),
            "Submission page": st.column_config.LinkColumn("Submission", display_text="Open"),
        },
    )


def score_chart(results: pd.DataFrame) -> None:
    chart_data = results.head(12).set_index("journal_title")[["Semantic fit", "Keyword overlap", "Area alignment", "Metadata richness"]]
    st.bar_chart(chart_data, height=max(320, 38 * len(chart_data)))


def journal_cards(results: pd.DataFrame) -> None:
    for index, row in results.head(12).iterrows():
        title = html.escape(clean(row.get("journal_title")))
        field = html.escape(clean(row.get("field")) or "Field not specified")
        context = html.escape(clean(row.get("Context signals")))
        band = html.escape(clean(row.get("Suitability band")))
        confidence = html.escape(clean(row.get("Evidence confidence")))
        score = float(row.get("Journal-fit score", 0))
        st.markdown(
            f"<div class='journal-card'><span class='journal-rank'>{index + 1}</span>"
            f"<span class='journal-title'>{title}</span><span class='score-pill'>{score:.1f}</span>"
            f"<div class='journal-meta'>{field} · {context} · {band} · {confidence}</div></div>",
            unsafe_allow_html=True,
        )
        with st.expander("Why this journal matched", expanded=index == 0):
            why_col, link_col = st.columns([1.7, 1])
            with why_col:
                st.markdown(
                    f"**Semantic evidence:** {row.get('Semantic fit', 0):.1f}/100  \n"
                    f"**Keyword overlap:** {row.get('Keyword overlap', 0):.1f}/100  \n"
                    f"**Area alignment:** {row.get('Area alignment', 0):.1f}/100  \n"
                    f"**Metadata completeness:** {row.get('Metadata richness', 0):.1f}/100"
                )
                st.markdown(f"**Matched terms:** {clean(row.get('Matched keywords')) or 'No direct phrase overlap found.'}")
                scope = clean(row.get("aims_scope"))
                if scope:
                    st.markdown(f"**Aims/scope evidence:** {scope}")
                st.caption("The score is evidence for triage, not an acceptance probability or quality ranking.")
            with link_col:
                official = safe_url(row.get("official_url"))
                submission = safe_url(row.get("submission_url"))
                st.link_button(
                    "Official journal page" if official else "Search official page",
                    official or row.get("Official journal search"),
                    use_container_width=True,
                )
                st.link_button(
                    "Submission guidance" if submission else "Search author guidance",
                    submission or row.get("Official journal search"),
                    use_container_width=True,
                )
                st.link_button("Google Scholar", row.get("Scholar search"), use_container_width=True)


def compare_panel(results: pd.DataFrame) -> None:
    options = results["journal_title"].tolist()
    selected = st.multiselect("Select up to four journals", options, default=options[: min(3, len(options))], max_selections=4)
    if not selected:
        st.info("Select journals to compare their evidence components.")
        return
    comparison = results[results["journal_title"].isin(selected)].copy()
    comparison = comparison.set_index("journal_title")[[
        "Journal-fit score", "Semantic fit", "Keyword overlap", "Area alignment", "Metadata richness"
    ]]
    st.bar_chart(comparison.T, height=420)


def downloads_panel(title: str, abstract: str, keywords: str, results: pd.DataFrame) -> None:
    report = build_markdown_report(title, abstract, keywords, results)
    download_one, download_two = st.columns(2)
    with download_one:
        st.download_button(
            "⬇ Download decision report",
            data=report,
            file_name="journalfit_decision_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with download_two:
        st.download_button(
            "⬇ Download shortlist CSV",
            data=results.drop(columns=["Rank priority"], errors="ignore").to_csv(index=False).encode("utf-8"),
            file_name="journalfit_shortlist.csv",
            mime="text/csv",
            use_container_width=True,
        )


def database_explorer(journals: pd.DataFrame) -> None:
    section_header("Explore the journal database", "Audit the records used by the recommender before trusting its output.")
    if journals.empty:
        st.warning("No journal metadata is loaded.")
        return
    query = st.text_input("Search journals, fields, publishers, or scope", placeholder="Type a journal, field, publisher, or topic")
    filtered = journals.copy()
    if query:
        searchable = filtered[["journal_title", "field", "publisher", "aims_scope", "typical_topics"]].fillna("").agg(" ".join, axis=1)
        filtered = filtered[searchable.str.contains(query, case=False, regex=False)]
    st.caption(f"Showing {len(filtered):,} of {len(journals):,} records")
    st.dataframe(
        filtered[[
            "journal_title", "field", "publisher", "abdc_rating", "ajg_2024",
            "aims_scope", "official_url", "verification_status", "source_file",
        ]].rename(columns={
            "journal_title": "Journal", "field": "Field", "publisher": "Publisher",
            "abdc_rating": "ABDC", "ajg_2024": "AJG", "aims_scope": "Aims and scope",
            "official_url": "Official page", "verification_status": "Data status", "source_file": "Source",
        }),
        use_container_width=True,
        hide_index=True,
        column_config={"Official page": st.column_config.LinkColumn("Official page", display_text="Open")},
    )


def methodology_panel() -> None:
    section_header("How the score works", "Transparent evidence components, adjustable weights, and explicit limitations.")
    st.markdown(
        """
        **JournalFit Studio uses four signals:**

        1. **Semantic evidence** compares the manuscript text with journal title, field, aims/scope, methods, and topics using local TF-IDF cosine similarity. The component blends absolute similarity with relative rank inside the filtered candidate set.
        2. **Keyword overlap** measures how many manuscript phrases appear in the journal metadata.
        3. **Metadata completeness** rewards records with field, URLs, aims/scope, topics, and method information because richer records support more defensible matching.
        4. **Area alignment** checks domain-specific terms for the selected or automatically inferred research area.

        The combined score is a **triage signal only**. It does not estimate acceptance probability, peer-review quality, speed, indexing validity, or journal legitimacy.
        """
    )
    st.info("For a production deployment, maintain a verified journal database and record the source and verification date for every ranking, URL, fee, and indexing claim.")


def main() -> None:
    st.set_page_config(
        page_title=f"{APP_NAME} · Explainable journal discovery",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={"Get help": GITHUB_URL, "Report a bug": f"{GITHUB_URL}/issues"},
    )
    inject_css()
    initialize_state()

    st.markdown(
        f"""
        <div class='hero'>
            <div class='eyebrow'>Research decision support · Local-first · Explainable</div>
            <h1>Find journals with <span>evidence, not guesswork.</span></h1>
            <p>Match a manuscript against your own journal metadata, understand why each journal appears, compare alternatives, and export a verification-ready shortlist.</p>
            <span class='chip'>🔐 No API key</span><span class='chip'>📄 PDF / DOCX / TXT</span>
            <span class='chip'>📊 ABDC & AJG context</span><span class='chip'>🧭 Transparent scoring</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    initial_files = local_metadata_files()
    initial_signatures = tuple((str(path), path.stat().st_mtime_ns, path.stat().st_size) for path in initial_files[:1])
    initial_journals = cached_local_metadata(initial_signatures, False) if initial_signatures else empty_journal_frame()
    controls = sidebar_controls(initial_journals)
    journals, load_messages = load_journals(
        controls["selected_paths"], controls["uploaded_metadata"], controls["all_sheets"]
    )
    for message in load_messages:
        st.warning(message)

    current_result_context = (
        len(journals),
        tuple(sorted(journals["source_file"].map(clean).unique().tolist())) if not journals.empty else (),
        controls["area"], controls["context"], tuple(controls["ratings"]), controls["field_filter"],
        controls["top_n"], controls["weights"],
    )
    if st.session_state.results is not None and st.session_state.result_context != current_result_context:
        st.session_state.results = None

    results = st.session_state.results
    overview_metrics(journals, results)

    discover_tab, explore_tab, methods_tab = st.tabs(["✨ Discover", "🗂 Explore database", "🧮 Scoring & limitations"])
    with discover_tab:
        title, abstract, keywords, submitted = manuscript_panel()
        manuscript_text = clean(f"{title} {abstract} {keywords}")
        if manuscript_text:
            detected = inferred_area(manuscript_text)
            signals = classify_area(manuscript_text).head(4)
            signal_col, text_col = st.columns([1, 2.2])
            with signal_col:
                st.metric("Likely research area", detected)
            with text_col:
                evidence = signals[signals["Evidence count"] > 0]
                if not evidence.empty:
                    st.caption("Detected signals: " + " · ".join(
                        f"{row['Area']} ({row['Matched terms']})" for _, row in evidence.iterrows()
                    ))

        if submitted:
            if journals.empty:
                st.error("No journal metadata is available. Select bundled metadata or upload a CSV/XLSX/XLS file.")
            else:
                try:
                    with st.spinner("Comparing manuscript evidence with journal metadata…"):
                        st.session_state.results = recommend(
                            title=title,
                            abstract=abstract,
                            author_keywords=keywords,
                            journals=journals,
                            area=controls["area"],
                            context=controls["context"],
                            ratings=controls["ratings"],
                            field_filter=controls["field_filter"],
                            top_n=controls["top_n"],
                            weights=controls["weights"],
                        )
                        st.session_state.last_query = {"title": title, "abstract": abstract, "keywords": keywords}
                        st.session_state.result_context = current_result_context
                    st.rerun()
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception as exc:
                    st.error(f"Journal matching failed: {exc}")

        results = st.session_state.results
        if results is None:
            st.info("Add manuscript evidence and generate a shortlist. Use **Load sample** to preview the workflow.")
        elif results.empty:
            st.warning("No journals remain after the selected filters. Broaden the ranking, field, or area settings.")
        else:
            section_header("Your evidence-based shortlist", "Inspect the table, compare score components, and verify each journal at the official source.")
            result_tabs = st.tabs(["Shortlist", "Evidence chart", "Journal cards", "Compare", "Export"])
            with result_tabs[0]:
                results_table(results)
            with result_tabs[1]:
                score_chart(results)
            with result_tabs[2]:
                journal_cards(results)
            with result_tabs[3]:
                compare_panel(results)
            with result_tabs[4]:
                query = st.session_state.last_query
                downloads_panel(query.get("title", title), query.get("abstract", abstract), query.get("keywords", keywords), results)

    with explore_tab:
        database_explorer(journals)

    with methods_tab:
        methodology_panel()

    st.markdown(
        f"""
        <div class='footer'><b>{APP_NAME} v{APP_VERSION}</b> · Developed by {AUTHOR}<br>
        <a href='{APP_URL}'>Live app</a> · <a href='{GITHUB_URL}'>GitHub</a> · <a href='{PORTFOLIO_URL}'>Developer profile</a><br>
        <span style='font-size:.82rem;opacity:.82'>Always verify current aims/scope, rankings, indexing, fees, ethics, and author guidelines on official sources.</span></div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
