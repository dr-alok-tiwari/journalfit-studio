# JournalFit Studio Handbook

**Journal discovery and fit assistant for researchers**  
Developed by **Dr. Alok Tiwari**  
Assistant Professor, Big Data Analytics, Goa Institute of Management, Goa  
Live app: <https://journalfit-ranking-studio-by-dr-alok-tiwari.streamlit.app/>  
Portfolio: <https://dr-alok-tiwari.github.io/>

---

## 1. Executive summary

JournalFit Studio is a local-first journal discovery tool that helps researchers identify potentially suitable journals from a manuscript title, abstract, keywords, research area, and curated journal metadata. It is designed for faculty members, doctoral scholars, early-career researchers, research offices, and academic mentors who need a structured way to shortlist journals before undertaking manual verification.

The tool is deliberately positioned as a **journal-fit assistant**, not a ranking authority. It supports the early stage of journal discovery by comparing manuscript signals with locally available journal information such as subject area, aims and scope, topics, publisher, official URL, submission URL, and optional contextual fields. Ranking-related data can be included in a workbook if a user has lawful access to it, but such fields are treated as contextual filters rather than the central basis of recommendation.

The current version is a practical, transparent prototype. It is suitable for local and institutional review, demonstration, and small-scale research-support use. Wider deployment would require a governed data-refresh process, stronger metadata validation, institutional privacy review, user-access controls, and a clear public responsible-use policy.

---

## 2. Why this tool was created

Researchers often struggle to identify journals that match the scope, method, audience, and contribution of a manuscript. Many existing journal-finder systems are tied to particular publishers, indexing platforms, or proprietary databases. Researchers also tend to rely on fragmented manual searches, informal advice, and ranking labels without sufficiently checking aims and scope.

JournalFit Studio addresses this practical problem by creating a transparent local workflow where the researcher can:

1. Start with the manuscript title, abstract, and keywords.
2. Match the manuscript against a local journal metadata file.
3. Inspect why each journal appears in the shortlist.
4. Verify official journal information before making a submission decision.
5. Maintain an institutional or personal journal metadata enrichment file over time.

The purpose is to reduce blind trial-and-error, improve journal-scope literacy, and support more careful manuscript targeting.

---

## 3. Intended users

The tool is designed for:

- Faculty members preparing journal submissions.
- PhD scholars and early-career researchers learning journal discovery.
- Research mentors advising students on manuscript placement.
- Research offices that maintain journal-support resources.
- Academic departments that want a transparent internal workflow for journal-fit discussions.

It is not designed for automated performance evaluation, hiring decisions, promotion decisions, ranking enforcement, or mechanical journal selection.

---

## 4. Core workflow

The standard workflow has six stages.

### Stage 1: Prepare journal metadata

The user places a workbook in the `data/` folder or uploads a workbook through the sidebar. The workbook may include journal title, subject area, ISSN, publisher, aims and scope, official URL, submission URL, typical topics, methods, and local editorial notes.

### Stage 2: Enter manuscript information

The user pastes the manuscript title, abstract, and keywords. The app can also parse PDF, DOCX, or TXT files to pre-fill these fields, but the researcher should review and correct extracted text.

### Stage 3: Run journal discovery

The app compares manuscript signals with the journal metadata and generates a shortlist.

### Stage 4: Inspect fit explanations

Each recommendation includes a journal-fit score, semantic signal, keyword overlap, area alignment, metadata richness, matched keywords, and missing keywords.

### Stage 5: Verify official information

The researcher checks the journal website, aims and scope, author guidelines, article type, fees, ethics policy, indexing information, and submission route.

### Stage 6: Export and document the process

The app can export a Markdown report and CSV shortlist for records, supervision meetings, or internal submission planning.

---

## 5. Methodology overview

JournalFit Studio uses interpretable local text-matching methods rather than external services. The current methodology includes:

- TF-IDF similarity between manuscript text and journal metadata.
- Keyword overlap between manuscript keywords and journal text.
- Research-area alignment using transparent keyword dictionaries.
- Metadata-richness scoring to show whether sufficient local evidence exists.
- Optional display of contextual ranking fields if present in user-provided metadata.

The score is a practical fit indicator, not a statistical probability. A high score means the local metadata contains text signals similar to the manuscript. It does not mean the journal will accept the paper.

---

## 6. Interpretation of scores

The app uses four broad labels:

| Label | Meaning |
|---|---|
| Strong fit candidate | The local metadata contains strong textual evidence of relevance. |
| Moderate fit candidate | The journal may be relevant, but manual scope verification is needed. |
| Exploratory candidate | The journal may be worth checking when metadata is sparse or broad. |
| Weak evidence in current metadata | The current metadata does not provide enough evidence of fit. |

These labels are deliberately cautious. They are meant to guide verification, not replace judgement.

---

## 7. Data requirements

A strong deployment depends on the quality of the local metadata file. At minimum, the file should include:

- Journal title.
- Field or subject area.
- Publisher.
- ISSN or eISSN.
- Official journal website.
- Submission or author-guidelines URL.
- Aims and scope.
- Typical topics.
- Preferred methods or article types.
- Local editorial notes.

The more complete the metadata, the more useful the recommendation explanations become.

---

## 8. Privacy and data handling

The local version does not require API keys and does not send manuscript text to external services by default. Manuscript parsing and matching occur inside the running app environment.

For the hosted demonstration version, users should avoid uploading confidential manuscripts unless the deployment owner has provided an explicit privacy and retention policy. A formal institutional deployment should define data retention, logging, access control, and user-consent rules.

---

## 9. Current limitations

The current version has the following limitations:

- It depends on the completeness and quality of local journal metadata.
- It does not verify official URLs in real time.
- It does not check current indexing status, APCs, publication delays, or editorial board information.
- It does not identify predatory journals.
- It does not make acceptance predictions.
- It does not replace scholarly judgement, mentor review, or official journal verification.
- Hosted use requires a separate privacy policy before confidential material should be uploaded.

---

## 10. Responsible-use safeguards

The app includes explicit responsible-use language in the interface, README, and documentation. It states that journal-fit suggestions are decision-support outputs and must be verified through official sources.

Recommended safeguards for wider deployment include:

- A visible disclaimer on every results page.
- A mandatory verification checklist before export.
- Clear separation between journal-fit signals and any ranking context.
- A log of metadata source and update date.
- A role-based workflow for institutional users.
- Versioned metadata updates.
- Periodic review of recommendation language.

---

## 11. Suggested use in academic settings

The tool is suitable for:

- PhD research-methods workshops.
- Faculty development sessions on publication strategy.
- Research mentoring meetings.
- Manuscript pre-submission planning.
- Research-office journal-support services.

It should not be used to decide publication quality, allocate incentives, evaluate faculty performance, or replace domain expert review.

---

## 12. Contribution and recognition

JournalFit Studio was developed by Dr. Alok Tiwari as an independent contribution to responsible research-support infrastructure. The tool is intended to encourage careful journal discovery and transparent manuscript-fit discussions, especially for researchers who may not have access to expensive proprietary journal intelligence systems.

Any institutional or public adaptation should retain appropriate attribution and clearly distinguish local modifications from the original contribution.
