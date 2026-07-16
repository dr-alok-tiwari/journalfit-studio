from __future__ import annotations

import pandas as pd
import pytest

from journalfit_core import (
    MatchWeights,
    canonicalize,
    clean,
    data_quality_summary,
    extract_manuscript_bytes,
    merge_records,
    recommend,
    safe_url,
)


def sample_journals() -> pd.DataFrame:
    raw = pd.DataFrame([
        {
            "Journal Title": "Healthcare Analytics Review",
            "Field": "Healthcare Management",
            "Aims and Scope": "Healthcare analytics, hospital management, patient systems and responsible artificial intelligence.",
            "Topics": "healthcare analytics; responsible AI; hospital governance",
            "Journal URL": "https://example.org/health",
            "ABDC Rating": "A",
        },
        {
            "Journal Title": "Retail Marketing Quarterly",
            "Field": "Marketing",
            "Aims and Scope": "Consumer behavior, retail branding and advertising.",
            "Topics": "consumer; brand; retail",
            "Journal URL": "https://example.org/marketing",
            "ABDC Rating": "B",
        },
    ])
    return canonicalize(raw, "journals.csv", "CSV")


def test_clean_and_safe_url() -> None:
    assert clean("a\n b\t c") == "a b c"
    assert safe_url("example.org/journal") == "https://example.org/journal"
    assert safe_url("not a url") == ""


def test_canonicalize_and_merge_prefers_richer_scope() -> None:
    first = sample_journals()
    duplicate = first.iloc[[0]].copy()
    duplicate["aims_scope"] = "A much longer and richer aims and scope description for healthcare analytics and governance research."
    merged = merge_records(pd.concat([first, duplicate], ignore_index=True))
    assert len(merged) == 2
    scope = merged.loc[merged["journal_title"] == "Healthcare Analytics Review", "aims_scope"].iloc[0]
    assert scope.startswith("A much longer")


def test_recommend_places_relevant_journal_first() -> None:
    results = recommend(
        title="Responsible artificial intelligence adoption in hospitals",
        abstract="We study healthcare analytics, hospital governance, patient systems and responsible AI adoption using mixed methods.",
        author_keywords="healthcare analytics; responsible AI; governance",
        journals=sample_journals(),
        area="Healthcare Management",
        context="All metadata",
        ratings=[],
        top_n=2,
        weights=MatchWeights(),
    )
    assert results.iloc[0]["journal_title"] == "Healthcare Analytics Review"
    assert results.iloc[0]["Journal-fit score"] > results.iloc[1]["Journal-fit score"]
    assert 0 <= results.iloc[0]["Journal-fit score"] <= 100


def test_recommend_validates_short_input() -> None:
    with pytest.raises(ValueError):
        recommend("Short", "Too short", "", sample_journals())


def test_extract_txt_manuscript() -> None:
    content = b"""Responsible AI Governance in Hospitals
Alok Tiwari, Example University

Abstract
This paper examines responsible artificial intelligence governance in hospital analytics and patient decision support.
Keywords: responsible AI; healthcare analytics; governance
1 Introduction
Background text."""
    parsed = extract_manuscript_bytes(content, "paper.txt")
    assert "Responsible AI Governance" in parsed["title"]
    assert "hospital analytics" in parsed["abstract"]
    assert "responsible AI" in parsed["keywords"]


def test_data_quality_identifies_demo_rows() -> None:
    journals = sample_journals()
    journals.loc[0, "verification_status"] = "demo-only"
    summary = data_quality_summary(journals)
    assert summary["records"] == 2
    assert summary["demo_records"] == 1
