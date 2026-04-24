# LLM Wiki: Building a Personal Knowledge Base for Academic Papers with AI Agents

A methodology for using Claude Code + OpenAI Codex CLI to build and maintain a structured, searchable wiki from academic PDFs — designed for researchers who read dozens of papers and want compounding knowledge.

## The Concept

Inspired by [Karpathy's LLM Wiki pattern](https://x.com/karpathy/status/1868287498986348734):

```
Original PDF → LLM markdown summary (sources/) → Structured wiki page (wiki/) → Overview synthesis
```

Each paper goes through a 3-tier pipeline:
1. **papers/**: Original PDF (immutable archive)
2. **sources/**: LLM-generated structured summary (7 standard sections)
3. **wiki/{category}/**: Structured wiki page with cross-references (`[[wikilinks]]`)

Overview pages synthesize across papers — this is where the real knowledge compounding happens.

## Repository Structure

```
llm-wiki/
├── CLAUDE.md               # Schema, workflow, rules for AI agents
├── index.md                # Full page catalog
├── papers/                 # Original PDFs (cp, never symlink)
│   └── {author}-{year}-{title-5-words}.pdf
├── sources/                # PDF summaries (English only)
│   └── {author}-{year}-{title-5-words}.md
└── wiki/                   # Structured wiki pages (English only)
    ├── {category}/         # 25+ categories
    └── overviews/          # Synthesis pages (the real value)
```

## Paper Naming Convention

All files (PDF, source, wiki) share the same name:

```
{first-author-lastname}-{year}-{first-5-title-words}.{ext}
```

Example: `pollard-2006-an-rna-gene-expressed-during.pdf`

## Single Paper Ingest (Claude Code)

### Step 1: Copy PDF and extract text

```bash
# Using opendataloader-pdf (best quality, needs Java)
export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"
python3 -c "
import opendataloader_pdf, tempfile, os, re, sys
pdf = sys.argv[1]
with tempfile.TemporaryDirectory() as d:
    opendataloader_pdf.convert(pdf, output_dir=d, format='markdown',
                               pages='1-15', image_output='off', quiet=True)
    stem = os.path.splitext(os.path.basename(pdf))[0]
    text = open(f'{d}/{stem}.md').read()
lines = [l for l in text.splitlines() if not re.match(r'!\[image \d+\]', l)]
print('\n'.join(lines)[:12000])
" "/path/to/paper.pdf"

# Fallback: pypdf (faster, lower quality)
python3 -c "
import pypdf, sys
reader = pypdf.PdfReader(sys.argv[1])
text = ''
for page in reader.pages[:15]:
    t = page.extract_text()
    if t: text += t + '\n'
    if len(text) > 12000: break
print(text[:12000])
" "/path/to/paper.pdf"
```

### Step 2: Create source file

```yaml
---
title: "Paper Title"
authors: Author List
year: YYYY
doi: DOI
category: category_name
pdf_path: /full/path/to/papers/filename.pdf
pdf_filename: filename.pdf
source_collection: collection_name
---
```

7 standard sections: One-line Summary, Document Information, Key Contributions, Methodology, Key Results, Limitations, Related Work, Glossary.

### Step 3: Create wiki page with `[[wikilinks]]` to related papers

### Step 4: Update `index.md`

## Batch Paper Ingest with Codex CLI (5+ papers)

When processing many papers at once, delegate to OpenAI's Codex CLI to save Claude's context window.

### Prerequisites
- Codex CLI installed: `npm install -g @openai/codex`
- Authenticated: `codex login`

### The Workaround: Korean/Unicode Path Issue

Codex websocket fails with non-ASCII characters in git repo paths. Solution:

```bash
# 1. Claude extracts text to /tmp (ASCII-only path)
mkdir -p /tmp/llm-wiki-ingest
python3 -c "..." paper.pdf > /tmp/llm-wiki-ingest/paper.txt

# 2. Run Codex from /tmp with --skip-git-repo-check
cd /tmp/llm-wiki-ingest
codex exec -m "gpt-5.4" \
  -c 'reasoning_effort="high"' \
  --full-auto \
  --skip-git-repo-check \
  "Read paper.txt and create source.md and wiki.md files..."

# 3. Fix paths and copy results back to project
sed -i '' 's|/short/path/|/full/unicode/path/|g' *.md
cp *-source.md /project/sources/
cp *-wiki.md /project/wiki/category/
```

### Parallel Batch Processing

Run 4-5 Codex instances in parallel with `&` and `wait`:

```bash
cd /tmp/llm-wiki-ingest

codex exec -m "gpt-5.4" -c 'reasoning_effort="high"' \
  --full-auto --skip-git-repo-check \
  "Read paper1.txt. Create paper1-source.md and paper1-wiki.md..." &

codex exec -m "gpt-5.4" -c 'reasoning_effort="high"' \
  --full-auto --skip-git-repo-check \
  "Read paper2.txt. Create paper2-source.md and paper2-wiki.md..." &

wait
echo "Batch complete"
```

### Known Limitations

| Issue | Cause | Workaround |
|---|---|---|
| UTF-8 websocket error | Non-ASCII chars in git repo path | `--skip-git-repo-check` + work from `/tmp` |
| Model `gpt-5.4-high` rejected | Not a valid model name | Use `gpt-5.4` + `-c 'reasoning_effort="high"'` separately |
| ChatGPT account model limits | Some models API-key only | Use default model or authenticate with API key |

### Codex vs Claude Agent: When to Use Which

| | Codex CLI | Claude Agent tool |
|---|---|---|
| **Best for** | Batch processing 5+ papers | Complex tasks needing wiki context |
| **Context** | Fresh per invocation | Shares session context |
| **Parallelism** | Shell `&` + `wait` | Agent tool with `run_in_background` |
| **Path issues** | Needs ASCII path workaround | No path issues |
| **Model** | gpt-5.4 | Claude (same session) |
| **Quality** | Good for structured extraction | Better for synthesis/cross-referencing |

## The Knowledge Tree Method

The most valuable part of this workflow is **knowledge tree expansion** — starting from a topic and branching outward:

```
Root question (e.g., "non-cortical brain cell types")
├── 1st wave: Direct overview pages
│   ├── ARHGAP11B dedicated page
│   ├── Thalamic molecular architecture
│   ├── Cerebellar cell diversity
│   ├── Complement synaptic pruning
│   └── WM vs GM astrocyte biology
├── 2nd wave: Deeper branches from discoveries
│   ├── Dopaminergic neuron diversity (from brainstem section)
│   ├── Human Accelerated Regions (from brain evolution)
│   └── Brain region-specific disease vulnerability
└── 3rd wave: Cross-cutting themes
    ├── Circadian regulation in brain evolution
    ├── Hypothalamus cell type atlas
    └── ... (continues)
```

### How it works in practice:

1. **Ask a question** → Claude searches wiki → answers from existing sources
2. **If wiki is insufficient** → read original PDFs → update wiki
3. **Follow-up questions** → branch into new topics → create new overview pages
4. **Cross-reference** → link new findings to existing pages → knowledge compounds

Each conversation session produces 5-15 new or updated wiki pages. After a few sessions, the wiki becomes a **searchable, cross-referenced knowledge graph** that any future conversation can draw from.

## Rules in CLAUDE.md

Key rules that make this work:

```markdown
# Answer only from wiki content (no web search)
# If wiki is insufficient, read original PDF
# If topic has no papers, say so and ask user for PDF
# All content in English
# PDFs stored as real files in papers/ (never symlink)
# pdf_path always points to papers/ folder
# Consistent YAML frontmatter in every file
```

## Scaling Search with QMD

As recommended by [Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), at small scale (~100 sources), a simple `index.md` suffices. But once the wiki grows past ~500 pages, you need a proper search engine.

**[QMD](https://qmd.ai)** is a local search engine for markdown files with:
- **Hybrid search**: BM25 keyword (lex) + semantic vector (vec) + hypothetical document (hyde)
- **LLM re-ranking**: Results are re-ranked by relevance
- **Fully on-device**: No data leaves your machine

### Setup as Claude Code MCP server

QMD runs as an MCP (Model Context Protocol) server that Claude Code can call directly. Once configured, Claude automatically searches the wiki via QMD instead of basic grep.

### Search example

```json
{
  "searches": [
    {"type": "lex", "query": "\"noncoding\" \"de novo\" autism"},
    {"type": "vec", "query": "how do noncoding variants contribute to ASD risk"},
    {"type": "hyde", "query": "De novo noncoding mutations in regulatory regions such as promoters and enhancers contribute to autism risk by disrupting TF binding sites and enhancer-promoter contacts."}
  ],
  "intent": "de novo noncoding mutations and autism",
  "limit": 100,
  "candidateLimit": 200
}
```

### When to use what

| Scale | Search method |
|---|---|
| < 100 pages | `index.md` + Claude's `Grep` |
| 100-500 pages | `Grep` works, QMD is faster |
| 500+ pages | **QMD is essential** — semantic search finds related pages that keyword search misses |

At our current scale (~2,500 pages), QMD consistently finds related overview pages and cross-category connections that grep-based search misses.

## Stats (as of April 2026)

- Source files: ~1,100
- Wiki pages: ~1,500 across 25 categories
- Overview pages: ~60 synthesis pages
- Papers: ~1,100 PDFs

## Getting Started

1. Create the folder structure
2. Write a `CLAUDE.md` with your schema and rules
3. Start with 5-10 papers in your field
4. Ask Claude Code questions → let it build the wiki
5. Follow curiosity → branch the knowledge tree

The wiki becomes more valuable with every paper added, because new papers connect to existing ones through `[[wikilinks]]` and overview pages.

---

*Built with [Claude Code](https://claude.ai/code) (Anthropic) + [Codex CLI](https://github.com/openai/codex) (OpenAI)*
