---
type: setup-guide
last_updated: 2026-04-24
---

# LLM Wiki — Initial Setup (one-time)

End-to-end procedure for getting the 4-stage loop operational from a clean machine. After completing these steps, daily operation is "start watcher, then ask Cowork to run the loop."

---

## 0. Prerequisites you should already have

- **Windows 10/11** with Python package manager installed (Miniforge, Anaconda, or venv).
- **Zotero desktop** installed with data directory configured.
- **Obsidian vault** with folders you want to mirror into the wiki.
- **Cowork desktop app** with your wiki folder selected as the workspace.

---

## 1. Clone or download this repository

```bash
git clone <repo-url> llm-wiki
cd llm-wiki
```

Or download as ZIP and extract.

---

## 2. Install Python dependencies

### Option A: Using Miniforge/Conda (recommended)

```bash
conda create -n llmwiki python=3.11
conda activate llmwiki
pip install -r _scripts/requirements.txt
conda install -c conda-forge openjdk  # For opendataloader-pdf (optional)
```

### Option B: Using venv

```bash
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS/Linux
pip install -r _scripts/requirements.txt
```

### Option C: System Python

```bash
pip install -r _scripts/requirements.txt
```

Verify installation:

```bash
python -c "import pypdf, requests; print('✓ Dependencies installed')"
```

---

## 3. Configure environment variables

Create a file named `.env` in the wiki root (or set in your shell):

```bash
# .env or Windows System Properties → Environment Variables

ZOTERO_DIR=C:\Users\{your-username}\Zotero
OBSIDIAN_VAULT=C:\Users\{your-username}\Obsidian
WIKI_ROOT=C:\path\to\llm-wiki
SCAN_FOLDERS=External Notes|Lab Notes|Tool Notes|Info|Clippings
ZOTERO_API_BASE=http://127.0.0.1:23119/api/users/0
```

Or edit `config.yaml` (see `config.example.yaml`).

**Windows users:** Set via System Properties → Environment Variables, or in PowerShell:

```powershell
$env:ZOTERO_DIR = "$env:USERPROFILE\Zotero"
$env:OBSIDIAN_VAULT = "$env:USERPROFILE\Obsidian"
```

---

## 4. Create the necessary directory structure

```bash
mkdir papers
mkdir sources
mkdir wiki\overviews
mkdir notes
mkdir documents
mkdir _scripts\_queue\{inbox,outbox,dead}
```

The wiki uses these folders for:
- `papers/` — extracted full-text caches from Zotero PDFs
- `sources/` — LLM-generated structured summaries
- `wiki/` — concept-level pages
- `notes/` — mirrored Obsidian notes
- `documents/` — non-Zotero reference materials (books, reports, etc.)

---

## 5. Smoke test: Extract one paper

Make sure Zotero is **closed**, then run:

```bash
python _scripts/batch_extract.py --limit 1
```

Expected output:
```
[1] Extracting smith-2024-example-paper...
      ✓ 45230 chars
Total: 1 | Extracted: 1 | Failed: 0 | Skipped: 0
```

If you see errors:
- **"database is locked"** → Zotero is still open; close it first.
- **"opendataloader failed"** → Java not in PATH; either install OpenJDK or accept pypdf fallback.
- **"zotero.sqlite not found"** → Check `ZOTERO_DIR` environment variable.

---

## 6. Smoke test: Mirror one note

```bash
python _scripts/notes_ingest.py
```

Expected output:
```
Synced: External-Notes__example-note
Total: N | Synced: M | Skipped: K
```

---

## 7. Smoke test: Test Zotero feedback

Make sure Zotero is **open** (local API must be running), then:

```bash
python _scripts/zotero_feedback.py --dry-run
```

Expected output:
```
[dry-run] ABCD1234 would set 2 tags, 1 relations
Updated: N | Failed: K
```

---

## 8. (Optional) Launch the watcher for Cowork integration

If using Cowork with the dispatch bridge:

```bash
cd _scripts
python watcher.py
```

Or on Windows:

```bash
_scripts\start_watcher.bat
```

The console should show:
```
[2026-04-24T...] watcher started; polling inbox/ every 2s
[2026-04-24T...] heartbeat written to _queue/watcher.heartbeat
```

Leave this running while you work in Cowork.

---

## 9. First full ingest (optional)

If you have many papers to ingest:

1. Make sure Zotero is **closed**.
2. Run stages in order:

```bash
# Stage 0: Mirror Obsidian notes
python _scripts/notes_ingest.py

# Stage 1: Extract PDFs
python _scripts/batch_extract.py

# Stage 2: Build wiki (use Cowork for this — it uses LLM)
# Ask Cowork agent: "Build the wiki from extracted papers"

# Stage 3: Feedback to Zotero (Zotero must be OPEN)
python _scripts/zotero_feedback.py
```

---

## 10. Daily usage

1. **Start the watcher:**
   ```bash
   _scripts\start_watcher.bat
   ```

2. **Add new papers to Zotero** (desktop app).

3. **Close Zotero**, then ask Cowork:
   > "Run the pipeline. Process new papers."

4. **Zotero opens automatically** (stage 3 feeds results back).

5. When done: `Ctrl+C` the watcher console (or just leave it running).

---

## 11. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `zotero.sqlite not found` | `ZOTERO_DIR` environment variable is wrong or Zotero is not installed | Check the path, reinstall Zotero, or update `ZOTERO_DIR` |
| `database is locked` | Zotero is open during stage 1 | Close Zotero, try again |
| `Zotero local API unreachable` | Zotero is closed during stage 3 | Open Zotero, try again |
| `No module named 'pypdf'` | Dependencies not installed | Run `pip install -r _scripts/requirements.txt` |
| `opendataloader-pdf: Java not found` | Java not in PATH | Install OpenJDK or accept pypdf fallback |
| Garbled extracted text | PDF is a scanned image | OCR not implemented; skip or pre-OCR externally |
| Watcher hangs | Long-running script | `Ctrl+C` watcher, check `_queue/watcher.log`, restart |

---

## 12. What to do with this repo

**For public distribution:**
- ✅ Keep `_scripts/`, `_templates/`, `CLAUDE.md`, `config.example.yaml`, `README.md`
- ❌ Remove or exclude: `papers/`, `sources/`, `wiki/`, `notes/`, `documents/`, `index.md`
- ❌ Add to `.gitignore`: personal notes, research data, credentials

**For private use:**
- ✅ All of the above, plus your research data (`wiki/`, `sources/`, `notes/`)

---

## Next Steps

- Read `CLAUDE.md` to understand the wiki structure and agent rules.
- Explore `_templates/` for document templates.
- Consult `config.example.yaml` for advanced configuration options.
- Ask your Cowork agent: "Build the wiki from papers in stage 2."

Enjoy your personal knowledge wiki!
