# LLM Wiki — Personal Knowledge Base + Zotero Bridge

A modular system for building a personal knowledge wiki from academic papers and research notes, with bi-directional sync to Zotero. Designed for researchers using Claude for literature synthesis.

---

## Overview

**LLM Wiki** automates the process of:

1. **Extracting** PDF text from Zotero storage (cached for speed)
2. **Mirroring** your Obsidian notes into a unified research archive
3. **Synthesizing** papers and notes via LLM into structured wiki pages
4. **Feeding back** wiki cross-references as Zotero tags and "Related Items"

The system is **modular** — you can use stage 1 (extraction) without stage 2 (synthesis), or stage 2 without the Zotero feedback loop.

---

## Quick Start

### 1. Clone and install

```bash
git clone <repo> llm-wiki
cd llm-wiki
pip install -r _scripts/requirements.txt
```

### 2. Configure

Copy `config.example.yaml` to `config.yaml` and customize, **or** set environment variables:

```bash
export ZOTERO_DIR=~/Zotero
export OBSIDIAN_VAULT=~/Obsidian
export WIKI_ROOT=.
```

### 3. Extract papers from Zotero

Zotero must be **closed**:

```bash
python _scripts/batch_extract.py
```

This creates `papers/{stem}.fulltext.md` for every PDF in your Zotero library.

### 4. Mirror your notes

```bash
python _scripts/notes_ingest.py
```

This creates `notes/{slug}.md` for every `.md` file in your configured scan folders (e.g., External Notes, Lab Notes).

### 5. (Optional) Build the wiki with Claude

Use the Claude Cowork agent to synthesize papers into concept wiki pages:

```
In Cowork:
> Ask Claude: "Build the wiki. For each paper, create a sources/{stem}.md 
  entry and update relevant concept pages in wiki/."
```

### 6. (Optional) Sync back to Zotero

Zotero must be **open**:

```bash
python _scripts/zotero_feedback.py
```

This adds `wiki:cat/{category}` and `wiki:overview/{topic}` tags to papers, plus "Related Items" links based on cross-references in the wiki.

---

## How It Works

### 4-Stage Pipeline

| Stage | Mechanism | LLM tokens | Time |
|-------|-----------|-----------|------|
| **0** | Mirror Obsidian notes into `notes/` with frontmatter | 0 | seconds |
| **1** | Extract PDF text from Zotero → `papers/{stem}.fulltext.md` | 0 | minutes |
| **2** | Build wiki: synthesize papers + notes → `sources/`, `wiki/`, `index.md` | ✓ | varies |
| **3** | Push wiki structure back to Zotero as tags + relations | 0 | seconds |

Each stage is independent and idempotent (safe to re-run).

### Architecture

```
Obsidian vault                     Zotero library
     ↓                                    ↓
notes_ingest.py                   batch_extract.py
     ↓                                    ↓
notes/{slug}.md                   papers/{stem}.fulltext.md
     ↓                                    ↓
     └─────────────────┬──────────────────┘
                       ↓
                  (Claude LLM)
                  Stage 2: Wiki Build
                       ↓
        sources/{stem}.md
        wiki/{category}/{concept}.md
        wiki/overviews/{topic}.md
        index.md
                       ↓
                zotero_feedback.py
                       ↓
                Zotero tags + Related Items
```

---

## File Structure

```
llm-wiki/
├── CLAUDE.md                    # Agent rules & schema (read this first!)
├── config.example.yaml          # Configuration template
├── .gitignore                   # Exclude personal data from git
├── README.md                    # This file
│
├── _scripts/
│   ├── batch_extract.py         # Stage 1: PDF text extraction
│   ├── notes_ingest.py          # Stage 0: Notes mirroring
│   ├── zotero_feedback.py       # Stage 3: Wiki → Zotero sync
│   ├── start_watcher.bat        # Launch dispatch watcher (Windows)
│   ├── requirements.txt         # Python dependencies
│   ├── SETUP.md                 # Detailed setup instructions
│   └── _queue/                  # Dispatch queue (transient)
│
├── _templates/
│   ├── source-template.md       # Template for sources/{stem}.md
│   └── wiki-template.md         # Template for wiki concept pages
│
├── papers/                      # ← Generated: cached PDF extracts
├── sources/                     # ← Generated: LLM-synthesized summaries
├── wiki/                        # ← Generated: concept pages
│   ├── overviews/               # Cross-category synthesis
│   └── {category}/              # 25 fixed categories
├── notes/                       # ← Generated: mirrored Obsidian notes
├── documents/                   # Non-Zotero reference materials
└── index.md                     # ← Generated: catalog
```

---

## Configuration

### Via Environment Variables (recommended for deployment)

```bash
# Essential
export ZOTERO_DIR=/path/to/zotero
export OBSIDIAN_VAULT=/path/to/obsidian
export WIKI_ROOT=/path/to/llm-wiki

# Optional Zotero API
export ZOTERO_API_BASE=http://127.0.0.1:23119/api/users/0

# Optional: Obsidian folders to mirror (pipe-separated)
export SCAN_FOLDERS="External Notes|Lab Notes|Tool Notes|Info|Clippings"
```

### Via config.yaml (recommended for development)

Copy `config.example.yaml` to `config.yaml` and edit:

```yaml
zotero:
  data_dir: ~/Zotero
  api_base: http://127.0.0.1:23119/api/users/0

obsidian:
  vault_root: ~/Obsidian
  scan_folders:
    - External Notes
    - Lab Notes
    - Tool Notes

wiki:
  root: .
```

Environment variables override config.yaml values.

---

## Usage

### Extract papers (stage 1)

```bash
# Incremental (skip papers already cached)
python _scripts/batch_extract.py

# Force re-extract all
python _scripts/batch_extract.py --force

# Test with 1 paper
python _scripts/batch_extract.py --limit 1

# Extract single paper by Zotero item key
python _scripts/batch_extract.py --item-key ABCD1234
```

**Requirements:**
- Zotero **must be closed** (database is locked while Zotero is open)
- `ZOTERO_DIR` environment variable or `zotero.data_dir` in config.yaml

### Mirror notes (stage 0)

```bash
python _scripts/notes_ingest.py
```

**Features:**
- Scans configured Obsidian folders recursively
- Large notes (>32 KB) are head+tail truncated to preserve bandwidth
- Hash-based drift detection (catches edits that don't bump mtime)
- Safe to re-run multiple times per day

### Synthesize with Claude (stage 2)

Use the Cowork agent (requires Claude subscription):

```
> Build the wiki from all papers in papers/ and notes in notes/.
> For each paper, write sources/{stem}.md with the schema from CLAUDE.md §7.
> Update or create concept wiki pages in wiki/{category}/ for each topic.
```

Or with Claude Code:

```bash
claude ask "Build the wiki from papers/ and notes/"
```

### Sync back to Zotero (stage 3)

```bash
# Incremental (since last run)
python _scripts/zotero_feedback.py

# Full scan
python _scripts/zotero_feedback.py --full

# Dry run (show what would change)
python _scripts/zotero_feedback.py --dry-run
```

**Requirements:**
- Zotero **must be open** (local API runs on http://127.0.0.1:23119)
- `ZOTERO_API_BASE` environment variable or `zotero.api_base` in config.yaml

---

## Integration with Cowork (Claude Desktop)

If you're using the Cowork research app:

1. **Start the watcher:**
   ```bash
   _scripts/start_watcher.bat  # Windows
   python _scripts/watcher.py  # or directly
   ```

2. **Ask Claude in Cowork:**
   ```
   > Run the pipeline. Process new papers.
   ```

   This invokes stages 0, 1, 2, 3 in sequence using the dispatch bridge.

See `_scripts/SETUP.md` for detailed integration instructions.

---

## Key Concepts

### Stem

All artifacts about one paper share a single **stem**:

```
{first-author-lastname}-{year}-{first-3-non-stopword-title-words}
```

Examples: `smith-2024-cryo-em-structure`, `bhatia-2025-bioinformatics-framework`

Papers with different stems are treated as different papers, even if they share authors.

### Categories (25 fixed)

Wiki concept pages are scoped to one of 25 categories or marked as overviews:

molecular-biology, immunology, bioinformatics, genomics, transcriptomics, proteomics, cell-biology, cancer-biology, neuroscience, microbiology, virology, structural-biology, epigenetics, single-cell, machine-learning, methods, clinical, developmental-biology, signaling, metabolism, drug-discovery, rna-biology, crispr, reviews, evolution

Add new categories only with approval.

### Content Priority Hierarchy

When writing wiki pages, source content is drawn from three tiers:

1. **Tier A (highest):** Your own Obsidian notes — you've already curated meaning
2. **Tier B:** Zotero highlights — you've marked what's important
3. **Tier C (fallback):** Full PDF text — agent interprets

Agents **must** prefer A and B over C.

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| `zotero.sqlite not found` | Wrong ZOTERO_DIR | Check environment variable or config.yaml |
| `database is locked` | Zotero is open during extraction | Close Zotero, retry |
| `Zotero API unreachable` | Zotero is closed during feedback | Open Zotero, retry |
| `No module named 'pypdf'` | Dependencies not installed | `pip install -r _scripts/requirements.txt` |
| `opendataloader-pdf` fails | Java not in PATH | Install OpenJDK or accept pypdf fallback |
| Watcher hangs | Long-running script | Ctrl+C, check `_queue/watcher.log` |

---

## For Public Distribution

**Include in repo:**
- `_scripts/`, `_templates/`, `CLAUDE.md`, `config.example.yaml`, `README.md`, `.gitignore`

**Exclude from repo:**
- `papers/`, `sources/`, `wiki/`, `notes/`, `documents/` (your research data)
- `config.yaml` (your local paths)
- `.env` (credentials)
- `_scripts/_queue/` (transient)

See `.gitignore` for the default exclusion list.

---

## References

- **CLAUDE.md** — Full agent rules, schema, and workflow. Read before using the system.
- **config.example.yaml** — All configuration options with descriptions.
- **_scripts/SETUP.md** — Step-by-step setup for Windows, macOS, Linux.
- **_templates/** — Document templates for sources and wiki pages.

---

## License

This repository is provided as-is. Modify and distribute as needed for your research.

---

## Questions?

- Check `CLAUDE.md` for the system design and agent rules.
- Check `_scripts/SETUP.md` for installation issues.
- Check individual script docstrings for usage and parameters.
- Use environment variables or `config.yaml` to customize paths and API endpoints.

Happy researching!
