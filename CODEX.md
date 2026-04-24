# CODEX.md - Codex Operating Rules for This LLM Wiki

This file records how Codex should work inside this personal LLM Wiki.
It is subordinate to `CLAUDE.md`. If this file and `CLAUDE.md` disagree,
`CLAUDE.md` wins.

Read `CLAUDE.md` first, then this file, before answering questions,
building sources, editing concept pages, or running ingest/update loops.

---

## 1. Precedence

1. `CLAUDE.md`.
2. The user's direct instruction in the current conversation, when consistent
   with `CLAUDE.md`.
3. This `CODEX.md`.
4. Templates, helper skills, old gist notes, and script comments.

When old helper files still describe per-paper wiki pages, follow the newer
`CLAUDE.md` rule: `sources/{stem}.md` is the per-source artifact, and `wiki/`
contains concept pages and overviews only.

## 2. Purpose of the Wiki

This wiki is not a file dump. It is the user's working memory for research.
Codex should preserve three properties:

- Traceability: every factual claim should point to its source.
- Synthesis: concept pages should explain cross-source structure, not repeat
  individual paper summaries.
- Usability: the user should be able to re-enter a research line quickly by
  reading the overview, concept page, source page, and relevant notes.

## 3. Read and Write Scope

- Read broadly when needed, including outside this folder if the user asks for
  vault-wide context.
- Write only inside `🦖 LLM WiKi/` unless the user explicitly authorizes another
  target.
- Do not hand-edit `papers/{stem}.fulltext.md`; it is a regenerable cache.
- Do not overwrite `papers/{stem}.md`; it is human/Zotero-highlight material.
- Do not delete `sources/`, `wiki/`, `notes/`, or paper artifacts. If cleanup is
  needed, report it first or use an explicit, reviewed cleanup script.

## 4. Answering Rules

- Answer from `papers/`, `sources/`, `notes/`, and `wiki/` first.
- Do not use the open web unless the user explicitly asks.
- Mark provenance:
  - `source-derived`: published paper or document; cite `[[sources/stem]]` and
    DOI/PMID when available.
  - `note-derived`: user's mirrored note; cite `[[notes/slug]]` or the original
    vault path when present.
  - `concept-derived`: synthesis from `wiki/`; still cite the source pages that
    support the claim when making factual assertions.
- Distinguish demonstrated results from inference, model, hypothesis, or
  speculation.
- If the wiki has no entry on the topic, say that plainly and ask for the
  relevant PDF, source, or note.
- When speaking to the user in Korean, use polite form and keep the tone direct
  and factual.

## 5. Source Priority

Follow the `CLAUDE.md` priority hierarchy:

1. User notes in `notes/`.
2. User annotations and filled self-notes in `papers/{stem}.md`.
3. Extracted fulltext in `papers/{stem}.fulltext.md`.

Treat fulltext-only claims as lower-confidence until the user has read or
highlighted the paper. If a page relies heavily on Tier C fulltext synthesis,
mark that clearly in the page or changelog.

## 6. Directory Semantics

- `papers/`: Zotero-managed paper artifacts. PDFs stay in Zotero storage.
- `documents/`: non-paper reference materials only.
- `sources/`: the only per-paper/per-document structured artifact.
- `notes/`: mirrored external Obsidian notes; treat as first-person user
  material unless the original explicitly says lab pipeline/code.
- `wiki/overviews/`: parent synthesis pages and research-program maps.
- `wiki/{category}/`: concept pages only.
- `wiki/Box/` or its actual emoji-named folder: meta-pages about the user's
  own research arc. Keep these content-level and source-light, as specified in
  `CLAUDE.md`.

## 7. Creating or Updating `sources/{stem}.md`

Before writing a source page:

1. Confirm the canonical stem.
2. Read the paired paper artifacts together:
   - `papers/{stem}.md`, if present.
   - `papers/{stem}.fulltext.md`, if present.
3. Search `notes/` for thematic overlap.
4. Preserve all bibliographic uncertainty; do not invent DOI, PMID, journal,
   cohort, assay, or tool details.

Required output:

- Valid YAML frontmatter.
- The `CLAUDE.md` source schema sections in order.
- Quantitative claims with units and context.
- Explicit `Strength of Evidence` and `Limitations`, including "Our own".
- `Related Work` links to source pages, concept pages, and relevant notes.
- A `한국어 요약` section when following the current source-page standard.

## 8. Updating Concept Pages and Overviews

Concept pages should contain cross-paper synthesis. Do not create
`wiki/{category}/{stem}.md` for a single paper.

When a new source changes a concept:

1. Update the relevant concept page's current synthesis.
2. Add the source to `Lines of evidence`.
3. Update disagreements and open questions if the new source changes them.
4. Update the parent overview in the same batch.
5. Ensure the overview has a `Related concepts` table and body links to each
   child concept page.
6. Add a changelog entry with the date and concrete change.

If a concept page and a source page disagree on implementation choices for the
user's own project, the concept page wins because it records actual practice.

## 9. Index, Graph, and Batch Hygiene

After source/wiki edits:

- Update `index.md`.
- Update affected overview pages.
- Update the research meta-pages required by `CLAUDE.md` after Day batches.
- Regenerate the graph only after confirming `_scripts/build_graph.py` points to
  the current wiki root or has been made root-relative.
- Keep `_day_plans.md` current when executing Day batches.

## 10. Current Maintenance Backlog

As of 2026-04-24, Codex should watch for these known cleanup targets:

1. `CLAUDE.md`, `_templates/overview-template.md`, `_templates/notes-template.md`,
   and `.claude/skills/run-pipeline/SKILL.md` still contain old references to
   per-paper `wiki/{category}/{stem}.md` pages. Prefer the newer concept-page
   rule until those files are revised.
2. Some `sources/` pages still link to non-existent old per-paper wiki pages.
   Replace those with `[[sources/stem]]` links or with real concept pages.
3. Several paper highlight filenames have non-canonical stems or stem mismatches
   with existing sources. Use `rename_highlights.py --apply` only when the user
   has approved a filename-normalization pass.
4. Some early source pages lack `## 14. 한국어 요약`; add it when revising those
   pages.
5. `_scripts/build_graph.py` currently needs review before use because it may
   contain an environment-specific root path.
6. `index.md` statistics should be checked after each structural change; the
   current concept-page count may not match the visible concept table.

## 11. Editing Discipline

- Prefer small, auditable edits.
- Preserve the user's wording in notes and highlight-derived material.
- Do not rewrite a page just to improve style unless the user asks.
- When changing factual content, cite the source of the change.
- When unsure whether a claim is source-derived or note-derived, mark it as
  uncertain rather than smoothing over the provenance.
- Keep generated content in English by default, with Korean summaries only where
  the schema allows or the user asks.

---

Last updated: 2026-04-24.
