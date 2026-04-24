---
source_type: lab_note
original_path: "{absolute path to original note in Obsidian vault}"
original_relpath: "{relative path from vault root}"
original_mtime: YYYY-MM-DDTHH:MM:SS+00:00
last_synced: YYYY-MM-DDTHH:MM:SS+00:00
source_hash: "0123456789abcdef"
truncated: false
original_size_bytes: 1234
---

# Note Title

This is a template for manually-created notes that will be embedded in the wiki.
The frontmatter above is injected automatically by `notes_ingest.py` when mirroring
from your Obsidian vault.

## Purpose

Lab notes in this wiki represent **unpublished observations and working thoughts**.
They have weaker epistemic weight than peer-reviewed sources (`sources/`) but are
**first-class citations** in concept wiki pages (`wiki/`).

You should reference them in two ways:

1. **In wiki pages:** Use your original Obsidian path link (not the mirror slug):
   ```
   [[vault/My Folder/My Note]] ([[notes/my-folder-my-note|copynote]])
   ```
   Clicking the first link opens your real Obsidian note (vault path).
   The second link is the mirror in the wiki for archival.

2. **In sources/ pages:** Reference notes that overlap with a paper's topic:
   ```
   Linked notes:
   - [[vault/My Folder/My Note|note title]] ([[notes/slug|copynote]]) — relevance
   ```

## What to include in notes

- **Lab observations:** Experimental results, troubleshooting, assay development
- **Project status:** Current focus, next steps, blockers
- **Tool evaluation:** Comparisons of methods, benchmarks you've run
- **Literature summary:** Quick takes on papers before full sources/ synthesis
- **Learning notes:** Concepts you're studying, key definitions, mental models
- **Pipeline documentation:** Your actual workflow, parameters, scripts

## What not to include

- Sensitive personal information (health, financial, credentials)
- Unpublished raw data (move to `documents/` or external storage)
- Private correspondence or confidential lab business

## Size limits

Notes are mirrored as-is up to 32 KB. Larger notes are **head+tail truncated**:
- First 16 KB preserved
- Last 8 KB preserved
- Middle truncated with a `[... truncated ... bytes ...]` marker

If the agent needs the full text during stage 2, it will read from `original_path`.

## Drift detection

The frontmatter includes `source_hash` (SHA256 first 16 chars) to detect changes
that don't update mtime (e.g., `git restore`, file copies, archive extracts).
Re-sync is triggered when source mtime is newer **OR** hash differs.

## Example: Project Status Note

---

---
source_type: lab_note
original_path: "C:/Users/username/Obsidian/Project X/2026-04-status.md"
original_relpath: "Project X/2026-04-status.md"
original_mtime: 2026-04-24T15:30:00+00:00
last_synced: 2026-04-24T15:35:00+00:00
source_hash: "abc123def456789"
truncated: false
original_size_bytes: 2450
---

# Project X — April 2026 Status

## Current Phase

Running methylation calling step (step 5 in pipeline). Comparing 3 tools:
- MethylDackel (baseline, slow but accurate)
- Nanopolish (faster, slightly lower precision)
- PacBio's SMRT Link (newest, untested in our workflow)

## Results

- MethylDackel: 85 min for sample 1, 95% sites covered
- Nanopolish: 12 min for sample 1, 91% sites covered
- SMRT Link: 8 min for sample 1, 94% sites covered [PENDING: validation]

**Decision:** Leaning toward SMRT Link + Nanopolish comparison in next batch.

## Blockers

- SMRT Link outputs .h5 format; need custom parser for our downstream (TODO)
- Sample 2 methylation data shows unexpected heterogeneity (investigating)

## Next Steps

1. Validate SMRT Link results against MethylDackel truth set
2. Complete pipeline steps 6–7 (phasing + ASM annotation)
3. Write up methodology section by May 15

## Related Papers

- [[sources/bhatia-2025-pacbio-methylation]]
- [[sources/cheung-2023-hypermethylation-outliers]]

---

(End of example.)

---

## Integration with the wiki

When you finish this note, the wiki agent will:

1. **Find it during stage 0** (notes_ingest.py mirrors it into `notes/{slug}.md`)
2. **Grep related papers in stage 2** (agent searches `papers/` and `sources/` for mentions of "methylation", "step 5", etc.)
3. **Cite it in concept pages** (e.g., `[[wiki/methods/methylation-calling]]` includes this note as supporting evidence)

Your notes thus become **integrated research artifacts**, cited alongside peer-reviewed literature.
