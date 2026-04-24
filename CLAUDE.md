# CLAUDE.md — Agent Rules & Schema for the LLM Wiki

This file governs how Claude Code / Codex / Cowork agents operate on this repository.
Read this file **before** answering any question, ingesting a paper, or editing a wiki page.

---

## 1. Core Principle

The wiki is the **single source of truth** for everything I have read or written.
Answers must be grounded in its contents, not in the agent's parametric memory or the open web.

## 2. Answering Rules

1. Answer **only** from wiki content (`papers/` + `sources/` + `notes/` + `wiki/`). No web search unless the user explicitly asks.
2. Mark each claim's **provenance** explicitly: paper-derived (cite source page) vs. lab-note-derived (cite notes page). These have different epistemic weight.
3. If those four directories are insufficient for the question, look up the canonical PDF in Zotero (`zotero_item_key` in frontmatter) and extract via the `pdf-extract` skill — then update the wiki so the answer is preserved.
4. If there is **no entry** on the topic, say so in one sentence and ask the user for a PDF or note.
5. All factual claims must cite the underlying source with `[[wikilink]]` and PMID/DOI where available.
6. Distinguish correlation from causation. Prefer mechanistic explanation over surface summary.
7. Wiki body is written in **English** (gist rule retained for portability and LLM quality). A `## 한국어 요약` section of one paragraph is permitted at the end of any page.

## 3. Repository Layout

```
{WIKI_FOLDER}/
├── CLAUDE.md              # this file
├── index.md               # full page catalog
├── llm-wiki-gist.md       # methodology reference
├── _templates/            # source / wiki / overview / notes templates
├── _scripts/              # batch_extract, documents_ingest, zotero_feedback, notes_ingest
├── papers/                # text-form artifacts about academic papers (Zotero-managed)
│   ├── {stem}.md          # Zotero integration export — human-curated highlights + abstract
│   └── {stem}.fulltext.md # PDF text extraction — machine-generated, regenerable cache
├── documents/             # non-paper reference materials (NOT Zotero-managed)
│   ├── {stem}.pdf         # books, chapters, reports, manuals, standards — original PDFs live here
│   ├── {stem}.md / .txt   # direct-text sources (already markdown / plain text)
│   └── {stem}.fulltext.md # extraction cache for .pdf inputs only (§5 Stage 1b)
├── sources/               # LLM-generated structured summaries (.md) — covers both papers AND documents
├── notes/                 # Obsidian external-note summaries staged via notes_ingest
└── wiki/
    ├── overviews/         # cross-paper synthesis
    └── {category}/        # 25 categories — see §6
```

**Paper PDFs** remain in their **Zotero storage location** (`{ZOTERO_DIR}\storage\{ItemKey}\file.pdf`) and are never duplicated into this repository. The wiki references them via `zotero_item_key` and reads their content through pre-extracted text in `papers/{stem}.fulltext.md`.

**Document originals** (books, chapters, reports, manuals, standards — anything that is not an academic paper and is therefore not tracked in Zotero) **do live directly inside `documents/`**. This is the intentional exception to the "PDFs live in Zotero" rule and is scoped to non-paper materials only.

## 4. Naming Convention

All artifacts about one paper share a single stem:

```
{first-author-lastname}-{year}-{first-3-non-stopword-title-words}
```

Formally matches the Better BibTeX citation-key formula the user has configured in Zotero:

```
auth.lower + '-' + year + '-' + shorttitle.lower.replace(/\W+/g, '-')
```

Rules, in order of application:

1. Lowercase, ASCII-folded (`Privé` → `prive`, `Müller` → `muller`).
2. First author's surname, internal hyphens preserved (`De Paoli-Iseppi` → `paoli-iseppi`).
3. Year as 4 digits.
4. Title: take the first 3 non-stopword tokens; a hyphenated compound is one token with its internal hyphen stripped (`single-cell` → `singlecell`, `large-scale` → `largescale`).
5. Stopwords: articles, prepositions, conjunctions, copulas (`_stem.py:STOP_WORDS`).

Examples:
- `prive-2018-efficient-analysis-largescale`
- `bhatia-2025-bioinformatics-frameworks-singlecell`
- `paoli-iseppi-2024-long-read-sequencing-reveals` *(if title starts that way; adjust per actual title)*

### Paired artifacts under one stem

The same stem appears as **up to four** files, all referring to the same paper. The agent MUST treat them as a single unit:

| Path | Ownership | Regenerable? |
|---|---|---|
| `papers/{stem}.md` | Human (Zotero Integration export: highlights + abstract) | no — hand-curated |
| `papers/{stem}.fulltext.md` | Machine (batch_extract.py) | yes — cache |
| `sources/{stem}.md` | Agent (structured summary, §7) | yes — regenerable from above |
| `wiki/{category}/{stem}.md` | Agent (interpretive page, §8) | yes — regenerable |

**Pairing rule for the agent:** `{stem}.md` and `{stem}.fulltext.md` are **always the same paper** — two artifacts under one logical identity. The agent reads both together when writing stage 2 output, reconciling the hand-curated highlights with the full extracted text. If only one of the two exists, that is a *partial* state (expected during ingest) but the stem still identifies a single paper; do not create a separate `sources/` entry.

**Naming for documents/ (non-paper reference materials).** Same stem formula as §4. The "first-author-lastname" slot is filled by whichever is most meaningful: personal author, editor, or the organization that produced the material (e.g., `pacbio-2024-pb-cpg-tools-manual`, `oxford-2023-bioinformatics-handbook-ch4`). Year is the document's publication / revision year. Titles follow the 3-non-stopword-token rule. If the document genuinely has no year (e.g., an online manual with rolling updates), use the retrieval year and record the "no fixed year" fact in frontmatter.

When an external Obsidian note is staged into `notes/`, its filename is `notes/{topic-slug}.md` (notes aggregate across papers and thus do not follow paper-stem convention).

## 5. Ingest Pipeline

The pipeline is split into three independently triggerable stages. Stages 1 and 3 are token-free (pure local Python); stage 2 is the only one that consumes LLM tokens.

### Stage 1 — PDF text extraction (no LLM tokens)

Runs `_scripts/batch_extract.py`. For each PDF in Zotero storage:
1. Read paper metadata from Zotero's `zotero.sqlite` using `mode=ro&immutable=1` — this flag lets SQLite bypass lock checks, so Zotero can remain **open** during the run. (If Zotero is actively writing, reads are still safe because `immutable=1` tells SQLite the DB is stable for this connection.)
2. Compute the stem.
3. If `papers/{stem}.fulltext.md` is missing **or older than the PDF's mtime**, run extraction.
4. Use `opendataloader-pdf` (preferred; needs Java) and fall back to `pypdf` on failure.
5. Write `papers/{stem}.fulltext.md` with frontmatter `{title, authors, year, doi, pmid, zotero_item_key, extracted_at, extractor_version}`.

Only papers without a current cache entry are re-extracted, so subsequent runs are cheap.

### Stage 1b — Documents ingest (no LLM tokens)

Runs `_scripts/documents_ingest.py`. For each file in `documents/` that does not yet have a corresponding `sources/{stem}.md`:

1. **Detect file type by extension.**
   - `.pdf` → PDF extraction path.
   - `.md` / `.txt` → direct-text path.
   - Other (`.docx`, `.html`, `.epub`, …) → log as unsupported and skip; convert externally first.
2. **PDF path.**
   - If `documents/{stem}.fulltext.md` is missing or older than the PDF mtime, run the same `opendataloader-pdf` → `pypdf` fallback as Stage 1.
   - Write `documents/{stem}.fulltext.md` with frontmatter `{title, authors, year, source_type: document, document_subtype, original_path, extracted_at, extractor_version}`. Title / authors / year come from (a) an adjacent sidecar `documents/{stem}.yaml` if the user provides one, (b) PDF metadata, or (c) first-page-text heuristics — in that priority order.
3. **Direct-text path (.md / .txt).**
   - No extraction needed.
   - Ensure the file carries a minimal frontmatter block: `{title, year, source_type: document, document_subtype}`. If missing, prepend a stub (do not alter the body).
4. **Signal "ready for Stage 2".** The presence of either `documents/{stem}.fulltext.md` (PDF origin) or `documents/{stem}.md` / `.txt` (direct-text origin) with no corresponding `sources/{stem}.md` is the trigger for Stage 2 (A).

Documents do **not** participate in Stage 3 (Zotero feedback push) — they have no `zotero_item_key`. All other downstream structure (sources, wiki concept pages, overviews, index) treats document-derived `sources/{stem}.md` identically to paper-derived ones; the only differences are the frontmatter variant (`source_type: document`) and certain optional sections in §7.

Only documents without a current cache / source are re-processed, so subsequent runs are cheap and idempotent (mirror of Stage 1 behavior for papers).

### Stage 2 — Wiki construction (LLM tokens, but only on cached text)

Stage 2 has two sub-products:

**(A) For each new paper or document (i.e. `papers/{stem}.fulltext.md` exists OR `documents/{stem}.fulltext.md` / `documents/{stem}.md` / `documents/{stem}.txt` exists, but `sources/{stem}.md` does not):**

1. **Read inputs as a paired unit (§4).** For a paper: `papers/{stem}.md` (Zotero-exported highlights, may be absent) **and** `papers/{stem}.fulltext.md` (extracted full text) — these two are the same paper. For a document: either `documents/{stem}.fulltext.md` (if original was PDF) or `documents/{stem}.md` / `.txt` (if original was direct-text); there are no Zotero highlights for documents. Additionally, scan `notes/*.md` for thematic overlap.
2. **Write `sources/{stem}.md`** per the unified §7 schema (Thesis, Context, Contribution, Methodology, Results, Mechanism, Strength of Evidence, Limitations, Open Questions, Related Work, Glossary, 한국어 요약). Reconcile highlights vs. fulltext by preferring fulltext for quantitative claims and highlights as signal of user attention.
3. **Do NOT create per-paper wiki pages.** All interpretive content belongs in `sources/{stem}.md`. Wiki pages exist only at concept level (§8).
4. **Update or create concept wiki pages** that the new source contributes to. Add the source to the "Lines of evidence" section of existing concept pages, or spin up a new concept page if the source opens a new area.
5. **Update `index.md`** with the new source row.
6. **Write `wiki/{category}/{stem}.md`** following the §8 schema, with `[[wikilinks]]` to related pages discovered via `Grep` / QMD.
7. **Consider the overviews:** if the paper materially changes the field synthesis, update the relevant `wiki/overviews/{topic}.md` (do not replace — append to the changelog).

The agent must **never** read a PDF directly. If `papers/{stem}.fulltext.md` is missing, the agent invokes the `pdf-extract` skill to populate it before proceeding.

### Stage 3 — Zotero feedback push (no LLM tokens)

Runs `_scripts/zotero_feedback.py`. For each wiki page modified since the last run:
1. Resolve `zotero_item_key` from frontmatter.
2. Find related wiki pages via QMD (or `Grep` fallback).
3. POST to Zotero local API (`http://{ZOTERO_API_HOST}:{ZOTERO_API_PORT}/api/`, Zotero must be **open**):
   - **Tags:** `wiki:cat/{category}`, `wiki:overview/{topic}` for each linked overview.
   - **Related items:** Zotero "Related" links to other items whose `zotero_item_key` appears in the wiki page's `[[wikilinks]]`.
   - Optional: a Note attachment containing the Obsidian URL of the wiki page.

Stage 3 is purely additive: it never deletes Zotero metadata.

### Stage 0.5 — Normalize highlight filenames (no LLM tokens)

Runs `_scripts/rename_highlights.py --apply`. Scans `papers/*.md` and `papers/*.fulltext.md`, parses each file's metadata (Zotero Integration format or YAML frontmatter), computes the canonical stem per §4, and renames any file not already on the canonical form. Duplicates (multiple files mapping to the same target stem) are resolved by keeping the newest mtime; losers are moved to `papers/_duplicates/{timestamp}__{name}` (never deleted).

Idempotent. Run before stage 1 so that batch_extract sees canonical filenames and doesn't create duplicate caches.

### Stage 0 — External notes mirror (no LLM tokens)

Runs `_scripts/notes_ingest.py`. Walks the designated Obsidian folders (configured in `config.yaml`) and **mirrors** each `.md` into `notes/{slug}.md` with injected frontmatter `{source_type: lab_note, original_path, original_relpath, original_mtime, last_synced, source_hash, truncated, original_size_bytes}`. Files up to 32 KB are copied verbatim; larger notes are head+tail truncated (first 16 KB + last 8 KB) with a truncation marker.

**Drift detection.** Re-mirrors when (a) the destination is absent, (b) source mtime is newer than destination mtime, **or** (c) the destination's stored `source_hash` disagrees with the current source's SHA-256(16-char). The hash check catches edits that do not advance mtime (e.g., `git restore`, archive extracts, filesystem copies). Stage 0 should run before every stage 2 invocation to guarantee mirrors reflect current originals.

Summarization is deferred to stage 2: when the wiki agent writes a `wiki/*` page that draws on notes, it compresses and integrates the relevant portions at that point. Keeping stage 0 token-free makes daily re-sync essentially free.

## 6. Categories

25 fixed top-level categories. Add a new one only with user approval.

| Category | Scope |
|---|---|
| molecular-biology | DNA/RNA/protein mechanics, gene regulation |
| immunology | innate/adaptive immunity, autoimmunity |
| bioinformatics | pipelines, algorithms, benchmarks |
| genomics | WGS/WES, variant calling, population genomics |
| transcriptomics | bulk + spatial RNA-seq (not sc) |
| proteomics | MS, interactomes, PTMs |
| cell-biology | organelles, trafficking, cytoskeleton |
| cancer-biology | oncogenesis, tumor immunology, therapy |
| neuroscience | CNS biology, connectomics, disease |
| microbiology | bacteria, archaea, microbiome |
| virology | viral biology, host response |
| structural-biology | cryo-EM, X-ray, AlphaFold-era modeling |
| epigenetics | chromatin, methylation, histone marks |
| single-cell | scRNA-seq, scATAC, multimodal |
| machine-learning | foundation models, classical ML for biology |
| methods | wet-lab protocols, reagents |
| clinical | trials, diagnostics, translational |
| developmental-biology | embryogenesis, morphogens |
| signaling | kinase cascades, receptor biology |
| metabolism | metabolomics, flux, obesity/diabetes |
| drug-discovery | screening, medicinal chem, PK/PD |
| rna-biology | ncRNA, splicing, RNA modifications |
| crispr | editing, screens, base/prime editing |
| reviews | explicit review articles |
| evolution | phylogenetics, molecular evolution |

## 7. Source File Schema (`sources/{stem}.md`) — unified paper-level artifact

`sources/{stem}.md` is the **only** per-paper artifact in the wiki. It combines (a) the extractive summary role of the original source page with (b) the interpretive thesis / context / evidence / open-questions role previously held by per-paper wiki pages. Per-paper wiki pages no longer exist; `wiki/` contains concept pages only (§8).

```yaml
---
title: "Full paper title"
authors: "LastName FN, LastName FN, …"
year: 2024
doi: 10.xxxx/xxxxx
pmid: 12345678
category: immunology
zotero_item_key: ABCD1234
zotero_collection: "Category/Subcategory"
fulltext_path: papers/{stem}.fulltext.md
highlights_path: papers/{stem}.md
source_type: paper
source_collection: reference
---
```

### Frontmatter variant for document-type sources (`source_type: document`)

When the source originates from `documents/` (a non-Zotero reference material), the frontmatter uses this variant:

```yaml
---
title: "Full document title"
authors: "LastName FN, LastName FN, …"   # or editor name, or organization slug
year: 2024                                # publication / revision year; retrieval year if genuinely undated
category: methods                          # same 25-category list as papers
document_subtype: book | chapter | report | manual | standard | other
fulltext_path: documents/{stem}.fulltext.md   # if PDF-origin
# OR
fulltext_path: documents/{stem}.md            # if direct-text origin (.md or .txt)
source_type: document
source_collection: reference               # or a lab-specific collection name
# doi, pmid, zotero_item_key, zotero_collection, highlights_path → omitted (documents are not Zotero-tracked)
---
```

**Section applicability for documents.** The Required Sections in §7 Required Sections still apply by default. Because books and reports lack the journal/cohort/assay structure of an empirical paper, the following substitutions are permitted:

- §7 section 3 "Document Information" — for documents, use **publisher, edition, scope, coverage** in place of journal/study-type/cohort/platform.
- §7 sections 6 "Methodology" and 7 "Key Results" — for non-empirical documents (books, manuals, standards), condense these into a single "Content summary" section listing the main themes, chapters, or specifications. Empirical reports still use the full §7 structure.
- §7 section 9 "Strength of Evidence" — for documents that are reference / educational rather than empirical, this section may be replaced with a brief "Authority / reliability" note (publisher reputation, edition currency, known errata).
- All other sections (Thesis, Context, Key Contributions, Mechanism, Limitations, Open Questions, Related Work, Glossary, 한국어 요약) apply unchanged.

The source_type: document variant is otherwise processed by Stage 2 identically to a paper-type source and participates in the same concept wiki page updates, Lines of evidence citations, and index.md entries.

### Required sections, in order

1. **Thesis** — one interpretive sentence stating what this paper actually demonstrates. Mechanistic when possible.
2. **One-line Summary** — ≤ 30 words extractive gloss covering scope + method + main finding.
3. **Document Information** — journal, study type, cohort/sample, platform, dataset sources.
4. **Context — what was believed before** — 2–4 sentences situating the paper in the prior literature and conceptual landscape.
5. **Key Contributions** — 3–6 bullets; what is new / what the paper adds to the field.
6. **Methodology** — dense description of assays, cohorts, statistics; enough to mentally replicate. Identify controls and replicates explicitly.
7. **Key Results** — report effect sizes (fold change, hazard ratio, AUROC, effect size) and biological significance, not just p-values. Flag weak evidence explicitly.
8. **Mechanism / Model** — the paper's proposed mechanism or model. Walk through the causal chain; mark what is demonstrated vs. inferred.
9. **Strength of Evidence**
   - **Direct:** experiments that bear on the central claim.
   - **Indirect:** correlative or modeling support.
   - **Weak / missing:** gaps the authors did not address.
10. **Limitations** — **Author-stated** bullets + **Our own** bullets (things we notice that the authors did not flag).
11. **Open Questions** — forward-looking research questions the paper raises but does not answer.
12. **Related Work** — linked sources + concept wiki pages + notes. Link conventions in §7.1.
13. **Glossary** — terms a non-specialist reader might not know.
14. **한국어 요약** — see §7.2.

### 7.0.1 Source-content priority hierarchy

When constructing `sources/{stem}.md` or any concept page, content is drawn from three sources of evidence with **explicit priority**:

| Tier | Source | Weight |
|---|---|---|
| **A** | `notes/{slug}.md` — the user's own external notes referencing the paper | **highest** (the user has already curated meaning) |
| **B** | `papers/{stem}.md` — Zotero Integration export with the user's highlights | **high** (the user has already marked importance) |
| **C** | `papers/{stem}.fulltext.md` — full text the agent reads and interprets | **fallback only** |

**Ordering rule:** **A ≥ B ≫ C.**

Operational consequences:
- If A and/or B exist, the agent must build the source/concept page primarily from A and B. Tier C is used to fill gaps and to retrieve quantitative numbers (effect sizes, sample counts) the user did not capture.
- If A and B are absent, build from C alone — but mark this clearly in the page changelog (`built from fulltext only`) so it's obvious which pages need user revision later.
- The agent must **never** elevate fulltext-derived interpretations above the user's highlights or notes. If fulltext seems to contradict highlights, the agent flags the discrepancy in `Open Questions` rather than silently overriding.
- This hierarchy applies equally to source pages and to the citations within concept pages.

### 7.0.2 Attribution of external notes

External notes (`notes/{slug}.md`) are by default **the user's own research output**, not "the lab's." The agent must therefore:

- **Not** prefix references to notes with "lab's" / "the lab's" / "lab's own" framing.
- Use first-person framing ("my pipeline", "my project", "this project's pipeline", "my variant calling step") or neutral framing ("the ASD methylation long-read project") when describing note content.
- The exception: when the note itself is **explicitly tagged** as 연구실 코드 / 연구실 파이프라인 / lab pipeline / lab code (i.e., shared infrastructure received from the lab), then "lab's pipeline" / "lab's code" is the correct framing.
- Section header in source pages: use `Linked notes:` (not `Linked notes:`).
- Body references: `Note:` (not `Lab note:`); `my X note` (not `the lab's X note`).
- This rule applies retroactively — when editing any existing page, the agent fixes "lab's" → user-voice framing in the same edit.

### 7.1 Link conventions

| Target | Convention | Reason |
|---|---|---|
| Links to other sources | `[[sources/{stem}]]` | intra-repo, paper-level references |
| Links to concept wiki pages | `[[wiki/{category}/{concept}]]` or `[[wiki/overviews/{concept}]]` | primary intra-repo knowledge graph |
| Links to user's external notes | **`[[{original_relpath without .md}]]`** (original vault path) optionally followed by `([[notes/{slug}\|copynote]])` | clicking opens user's real Obsidian note; `copynote` is the mirror |

The original vault path must be read from the mirror's `original_relpath` frontmatter field — slugs do not round-trip reliably.

### 7.2 한국어 요약 section

≥ 200 Korean words (약 5–8 문장) covering:
1. 문제 제기 (what was limiting before the paper)
2. 핵심 기여 (what the paper added)
3. 메커니즘 (one or two concrete methods / models / algorithms)
4. 정량 근거 (effect sizes, benchmark numbers, key statistics)
5. 제약 (author-stated + our own)
6. 맥락 (connection to my project, related concept pages, relevant external notes)

## 8. Wiki Page Schema — **concept-based only** (`wiki/{category}/{concept}.md`, `wiki/overviews/{topic}.md`)

The wiki's primary unit is a **concept**, not a paper. Wiki pages organize knowledge around domain topics, project workstreams, or methodological questions. Each concept page synthesizes across multiple sources and/or notes. There are no per-paper wiki pages — paper-level content lives entirely in `sources/{stem}.md`.

Two location conventions, functionally identical except for scope:

- `wiki/{category}/{concept-slug}.md` — concept scoped to one of the 25 categories (§6). Use when the concept cleanly belongs to one category.
- `wiki/overviews/{concept-slug}.md` — concept spanning multiple categories, or top-level synthesis, or the topic of a whole project workstream that transcends categories.

### Frontmatter

```yaml
---
type: concept                # or "overview" if in wiki/overviews/
topic: "Topic name"
category: transcriptomics    # or the most-relevant category (for navigation; omit if in overviews/)
last_updated: 2026-04-21
sources_cited: 4             # number of sources/ pages linked (for navigation)
notes_cited: 3               # number of notes linked
---
```

### Required sections (flexible by topic, but this is the default template)

1. **Current synthesis** — 3–5 sentences stating what the wiki collectively concludes about this concept as of today. Update this paragraph whenever a new source or note materially changes the picture.
2. **Why this matters** — one paragraph locating the concept in the research program. If it's an infrastructure/tool concept, explain when it would be used.
3. **Core content** — the actual concept explanation. Structure as fits the topic: mechanistic walk-through, comparison table, historical progression, methodological recipe, etc. Cite sources and notes inline with `[[links]]`.
4. **Lines of evidence / Primary references** — grouped citations of the sources that support the synthesis. Disagreements between sources must be disclosed explicitly.
5. **Open questions / What we still don't know** — gaps that neither the literature nor the notes have resolved.
6. **Related concepts** — other wiki pages (concept or overview) worth visiting next.
7. **Changelog** — append-only log of material updates (which source or note addition changed which part of the synthesis).

### Korean summary in concept pages

Concept pages MAY include a `## 한국어 요약` section using the same structure as source pages (§7.2). For concept pages aimed at Korean-primary workflow, this is strongly encouraged.

### Concept page examples

- `wiki/transcriptomics/long-read-isoform-annotation.md` — methodological concept citing multiple sources and notes on SQANTI3/Pigeon.
- `wiki/neuroscience/genetic-architecture-disorder.md` — multi-source synthesis.
- `wiki/overviews/long-read-genomics-research.md` — cross-category overview of a research focus.
- `wiki/genomics/population-reference-resources.md` — concept citing methodological notes.

### Principles for concept pages

- **A concept page's subject can be a lab project, a method, a biological phenomenon, or a question — not a paper.** Papers are cited; they are not the subject.
- **Update in place.** Do not create `wiki/.../foo-v2.md` — edit `foo.md` and append to its changelog.
- **Disclose disagreements.** If two cited sources conflict, say so and say which side (if any) the current synthesis favors and why.
- **Page length is topic-driven, not paper-count-driven.** A concept with one primary source is a short page; one with many can grow. Do not pad.

## 9. Overview Pages (`wiki/overviews/{topic}.md`)

Overview pages are a subset of concept pages (§8): scope spans multiple categories, or they represent the conceptual top of a research program. Same schema as §8; located under `wiki/overviews/` for navigation rather than substantive difference.

## 10. External Notes (`notes/{slug}.md`)

Notes are produced by `_scripts/notes_ingest.py` (stage 0, token-free mirror) from the scan folders defined in configuration. Frontmatter shape:

```yaml
---
source_type: lab_note
original_path: "{OBSIDIAN_VAULT_ROOT}/example-folder/file.md"
original_relpath: "example-folder/file.md"
original_mtime: 2026-04-15T00:00:00+00:00
last_synced: 2026-04-21T00:00:00+00:00
truncated: false
original_size_bytes: 1234
---
```

Notes are first-class citations but must be marked as such in any wiki body that draws on them. They represent unpublished observation and have weaker epistemic weight than peer-reviewed sources. When a note's frontmatter has `truncated: true`, the agent may consult `original_path` for the full text if the truncated portion is inadequate.

**Efficient note usage (do this, not pre-summarization):** For each paper in stage 2, `Grep` the notes directory for keywords drawn from the paper's title, authors, and method domain. Only read in full the notes whose filenames or grep matches suggest thematic overlap. Do **not** preemptively summarize all notes — the mirror is deliberately verbatim to preserve fidelity; bulk summarization trades token cost upfront for lossy content. The exception is a `truncated: true` note whose excerpt is inadequate for the current task: in that case, read the original from `original_path` (Bash `cat` via the bridge if necessary) rather than relying on the head+tail stub.

## 11. Search

| Scale | Method |
|---|---|
| < 100 pages | `index.md` + `Grep` |
| 100–500 | `Grep` still adequate; QMD optional |
| 500+ | QMD (BM25 + vector + HyDE) configured as MCP server |

## 12. Batch Ingest with Codex CLI

Use only for 5+ papers at once. For single-paper or synthesis tasks, the Claude/Cowork agent is better.

- Work from a temporary directory with ASCII paths only.
- Standard Codex invocation with appropriate model selection.
- Run ≤ 5 instances in parallel via `&` + `wait`.
- After Codex finishes, move results into `sources/` and `wiki/{category}/`.

Note: stage 1 (PDF extraction) does not use Codex — pure Python is faster and free.

## 13. Orchestration (Cowork ↔ Windows bridge)

The Cowork sandbox cannot invoke Windows binaries directly. Stages 0, 1, 3 execute on the user's Windows host through a file-based bridge:

```
Cowork sandbox                                Windows host
├── _scripts/cowork_dispatch.sh ─┐    ┌── _scripts/watcher.py (Python env)
│   writes JSON to inbox/         │    │   polls inbox/, runs script via env's python
│   polls outbox/ for result      │    │   writes JSON to outbox/
└── _scripts/_queue/inbox/ <──── bridge ────> outbox/
                                       └── heartbeat file (touched every 2 s)
```

The agent invokes `bash _scripts/cowork_dispatch.sh <script> [args...]`. The call blocks until Windows finishes, then returns the script's stdout/stderr/exit code. If `_scripts/_queue/watcher.heartbeat` is missing or > 15 s old, the dispatch refuses to enqueue and asks the user to start the watcher.

The agent's role per stage:

| Stage | Mechanism |
|---|---|
| 0 — notes mirror | `cowork_dispatch.sh _scripts/notes_ingest.py` |
| 1 — PDF extract  | `cowork_dispatch.sh _scripts/batch_extract.py` |
| 2 — wiki build   | LLM agent reads `papers/*.fulltext.md` + `notes/*.md`, writes `sources/`, `wiki/`, `index.md` |
| 3 — Zotero push  | `cowork_dispatch.sh _scripts/zotero_feedback.py` |

End-to-end loop is documented in skill documentation. The agent should follow that playbook when requested.

### Graph view — Obsidian built-in is primary

Day-to-day knowledge-graph exploration uses **Obsidian's native Graph View** (`Ctrl+G` global, `Ctrl+Shift+G` local). Filters for the wiki folder can be configured to group pages by category. This is force-directed, zoomable, interactive.

`wiki/overviews/knowledge-graph.md` (Mermaid) is a **static snapshot** for version control, commit-diff review, or sharing outside Obsidian. Not for daily exploration. Regenerate via `python3 _scripts/build_graph.py` whenever sources/wiki changes materially.

## 14. Batch ingest cadence + priority selection

Full-library one-shot ingest is not viable at scale. Instead:

**Cadence.** Process new papers in batches of 10–20 per session. Each batch is selected based on relevance to the current research focus.

**Priority ranking rubric** (agent applies this when selecting batches):

1. **Tier 1 — direct methodology for active pipeline.** Methods, tools, benchmarks directly related to current work.
2. **Tier 2 — biology axis of active project.** Domain knowledge papers related to current research directions.
3. **Tier 3 — adjacent methodology.** Related methods and tools from nearby domains.
4. **Tier 4 — historical context.** Foundational papers providing background for overview pages.
5. **Tier 5 — peripheral.** Papers of general interest but not immediately applicable.

**Day-batch composition rule:** mix ~60% Tier 1+2, ~30% Tier 3, ~10% Tier 4+5. Pure-tier days produce less cross-linked output.

**Between-batch actions.** After each batch:
- Update relevant concept wiki pages (add citations to Lines of evidence).
- If a natural new concept emerges from the batch, create a new concept wiki page.
- Regenerate `wiki/overviews/knowledge-graph.md` via `python3 _scripts/build_graph.py`.
- Update `index.md` with new source rows.

**When selecting next batch:** agent lists un-sourced papers, groups by tier and topic, proposes a batch with rationale, waits for user confirmation before extracting.

## 15. Source writing style guide (by paper type)

The unified §7 schema applies to all papers, but emphasis shifts by paper type:

| Paper type | Emphasize | De-emphasize |
|---|---|---|
| **Primary research (novel finding)** | Key Results (effect sizes, quantitative claims), Strength of Evidence, Limitations-"our own" | Methodology detail beyond what's needed to judge claims |
| **Methods / tool paper** | Mechanism/Model (how the tool works), Methodology (benchmarks, training data), tool adoption context | Biological interpretation beyond the tool's test case |
| **Review** | Context (synthesis state-of-field before this review), taxonomic framing, open questions | Methodology (there's no primary data) |
| **Resource / data paper** | Document Information (data scope, release terms), Key Contributions (what's in the release) | Mechanism (there may not be one) |
| **Critical-assessment candidate** | Limitations-"our own" (flag potential issues), Strength-of-Evidence "Weak / missing" | Uncritical paraphrasing of author claims |

**한국어 요약 section** uses a consistent 6-label bold structure: **문제 제기** → **핵심 기여** → **메커니즘** → **정량 근거** → **제약** → **맥락**. 200+ Korean words. This consistency makes the summaries scannable across papers.

**"Our own" limitations.** The author-stated limitations section of a paper typically understates problems. The agent must explicitly add methodologically substantive concerns the author didn't flag — data leakage, cohort representativeness, platform/chemistry obsolescence, missing replication, etc.

## 16. Concept wiki page patterns

The 3-pillar pattern (emerging from active use):

- **Technology-side overview** (`wiki/overviews/<topic>`) — what methodological platform enables the research, what prior approaches missed, tool landscape.
- **Biology-side concept** (`wiki/{category}/<topic>`) — what the field currently believes about the biology, where it agrees/disagrees.
- **Pipeline/workflow concept** (`wiki/methods/<project-name>-workflow`) — sequential pipeline externalized, each step mapped to source papers and notes.

All three pillars cite the same core sources but frame them differently. Reading all three together tells the whole story of a research direction. New research directions should generate a matching 3-pillar set when they become central.

**Concept page vs. source page boundary.** If a claim is paper-specific (novel finding, single-study methodology), it goes in the source page. If a claim is cross-paper (synthesis, disagreements, field-level framing), it goes in a concept page. The concept page cites the sources that support each claim.

## 17. Immutable Rules

- **PDFs live in Zotero**, not in this repository. `zotero_item_key` is mandatory in frontmatter for any paper-derived page.
- **`{stem}.md` and `{stem}.fulltext.md` always denote the same paper.** One logical identity, two artifacts. The agent reads them together (§4, §5 Stage 2) and never creates two `sources/` pages for one stem.
- **`papers/{stem}.fulltext.md` is a cache.** Regenerable from the PDF + extractor. Do not hand-edit; edit `sources/{stem}.md` instead.
- **`papers/{stem}.md` is human-touched.** Preserve user highlights verbatim; do not auto-overwrite.
- The agent **never reads PDF binaries directly.** All PDF access goes through stage 1 cache. If the cache is missing, invoke `pdf-extract` skill first.
- Frontmatter is **mandatory** and must parse as valid YAML.
- No fabricated citations, DOIs, PMIDs, author names, or journal titles. If uncertain, mark as unverified.
- Do not delete `sources/`, `wiki/`, or `notes/` files. Edit in place.
- Stage 3 (Zotero feedback) is **additive only.** Never delete Zotero tags or items.
- **Source-content priority is A ≥ B ≫ C** (notes ≥ highlights ≫ fulltext). The agent MUST build pages primarily from notes (`notes/`) and highlights (`papers/{stem}.md`); `papers/{stem}.fulltext.md` is fallback-only. See §7.0.1.
- **External notes default to first-person attribution.** Never use "lab's" / "the lab's" / "lab note" framing for `notes/` content unless the original note is explicitly tagged as lab-infrastructure. See §7.0.2.
- **`documents/` is for non-Zotero reference materials only** (books, chapters, reports, manuals, standards). Original files (PDF, .md, .txt) live directly in the folder — unlike papers/ whose PDFs remain in Zotero storage. A `documents/{stem}.fulltext.md` extraction cache is produced only when the origin is PDF. Documents have no `zotero_item_key`, do **not** participate in Stage 3 Zotero feedback, and use the `source_type: document` frontmatter variant (see §7). Otherwise they flow through Stage 2 identically to paper-type sources and can be cited from concept wiki pages on equal footing.

---

## 18. Lab-wide research conventions (factual, cross-project)

These are **factual, content-level decisions** that apply across all active research tracks. They are not wiki-structure rules; they are content defaults the agent must assume unless a specific concept page overrides them.

- **Reference genome policy:** Document your lab's standard reference genome choice and rationale. Update when the standard changes.
- **Sample type conventions:** Document standard cohort / sample specifications for your research program.
- **Cohort scale:** Document typical cohort sizes and statistical frameworks used.
- **Concurrent research tracks:** List active research directions and their status.
- **Tool-choice discipline:** For methodological stages with multiple viable tool options, document the comparative benchmarking framework and current selection.
- **Precedence rule:** When wiki concept pages and published sources disagree on an implementation choice, the **concept page wins** — it encodes actual implementation; `sources/` encode published methodology.

---

*Revised: 2026-04-24 — deployment version with environment variables and configuration-based paths. All personal information, project details, and hardcoded paths removed. Template-ready for public distribution.*
