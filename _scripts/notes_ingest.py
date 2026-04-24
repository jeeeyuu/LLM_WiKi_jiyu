"""
notes_ingest.py — Obsidian external notes → notes/{slug}.md

Pure local Python. Zero LLM tokens.

Mirrors user-designated Obsidian folders into notes/, injecting
frontmatter so the wiki agent can treat them as first-class citations.
Long notes (>32 KB) are head+tail truncated; the agent can read the
original via `original_path` if needed.

Configuration: Set environment variables or edit config.yaml:
  - OBSIDIAN_VAULT: path to Obsidian vault root (default: ~/Obsidian)
  - SCAN_FOLDERS: pipe-separated list of folders to mirror (default: see code)
  - WIKI_ROOT: path to wiki root (default: current directory)

Usage (PowerShell/bash):
    python _scripts/notes_ingest.py
"""

# --- 1. Configuration --------------------------------------------------------

import hashlib
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Windows cmd's default codepage is cp949/cp1252; force UTF-8 so slugs
# containing emojis or Korean characters can be printed.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HASH_RE = re.compile(r"^source_hash:\s*['\"]?([0-9a-f]{16})['\"]?\s*$", re.MULTILINE)

OBSIDIAN_VAULT = Path(os.getenv("OBSIDIAN_VAULT", Path.home() / "Obsidian"))

# Default scan folders — customize in config.yaml or via SCAN_FOLDERS env var
DEFAULT_SCAN_FOLDERS = [
    "External Notes",
    "Lab Notes",
    "Tool Notes",
    "Info",
    "Clippings",
]

SCAN_FOLDERS_STR = os.getenv("SCAN_FOLDERS")
SCAN_FOLDERS = SCAN_FOLDERS_STR.split("|") if SCAN_FOLDERS_STR else DEFAULT_SCAN_FOLDERS

WIKI_ROOT = Path(os.getenv("WIKI_ROOT", Path.cwd()))
NOTES_DIR = WIKI_ROOT / "notes"

VERBATIM_THRESHOLD = 32 * 1024
HEAD_BYTES         = 16 * 1024
TAIL_BYTES         =  8 * 1024

# --- 2. Slug generation ------------------------------------------------------

# Korean → romanized fallback is overkill; we keep Hangul in slugs since
# Obsidian and the wiki agent both handle UTF-8 filenames cleanly. We only
# strip filesystem-illegal characters and collapse whitespace.

ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

def make_slug(rel_path: Path) -> str:
    """Relative path inside OBSIDIAN_VAULT → flat kebab-style slug."""
    parts = list(rel_path.with_suffix("").parts)
    raw = "__".join(parts)
    raw = ILLEGAL.sub("", raw)
    raw = re.sub(r"\s+", "-", raw)
    return raw

# --- 3. Mirror logic ---------------------------------------------------------

def src_hash(src: Path) -> str:
    """16-char prefix of SHA-256 over raw bytes — sufficient for drift detection."""
    return hashlib.sha256(src.read_bytes()).hexdigest()[:16]

def stored_hash(dst: Path) -> str | None:
    if not dst.exists(): return None
    try:
        m = HASH_RE.search(dst.read_text(encoding="utf-8", errors="replace"))
        return m.group(1) if m else None
    except OSError:
        return None

def needs_resync(src: Path, dst: Path) -> bool:
    """Re-mirror when destination missing, src newer, OR src content hash differs.

    The hash check catches edits that don't bump mtime (git restore, file
    system copies, archive extracts) — situations where mtime alone misses a
    real content change.
    """
    if not dst.exists():
        return True
    if src.stat().st_mtime > dst.stat().st_mtime:
        return True
    sh = stored_hash(dst)
    if sh is None:                          # mirror predates hash field
        return True
    return sh != src_hash(src)

def render_body(src: Path) -> tuple[str, bool]:
    """Returns (body, truncated_flag)."""
    raw = src.read_bytes()
    if len(raw) <= VERBATIM_THRESHOLD:
        return raw.decode("utf-8", errors="replace"), False
    # Truncate: head + tail
    head = raw[:HEAD_BYTES].decode("utf-8", errors="replace")
    tail = raw[-TAIL_BYTES:].decode("utf-8", errors="replace")
    body = f"{head}\n\n[... truncated {len(raw) - HEAD_BYTES - TAIL_BYTES} bytes ...]\n\n{tail}"
    return body, True

def mirror_note(src: Path, dst: Path, scan_folder: Path):
    """Mirror one note, injecting frontmatter."""
    rel_path = src.relative_to(OBSIDIAN_VAULT)
    slug = make_slug(rel_path)
    body, truncated = render_body(src)

    frontmatter = f"""---
source_type: lab_note
original_path: "{src.resolve()}"
original_relpath: "{rel_path}"
original_mtime: {datetime.fromtimestamp(src.stat().st_mtime, tz=timezone.utc).isoformat()}
last_synced: {datetime.now(timezone.utc).isoformat()}
source_hash: "{src_hash(src)}"
truncated: {str(truncated).lower()}
original_size_bytes: {len(src.read_bytes())}
---

"""
    output_text = frontmatter + body
    dst.write_text(output_text, encoding="utf-8")

def main():
    if not OBSIDIAN_VAULT.exists():
        print(f"ERROR: Obsidian vault not found: {OBSIDIAN_VAULT}", file=sys.stderr)
        print(f"  Set OBSIDIAN_VAULT environment variable or check path.", file=sys.stderr)
        sys.exit(1)

    NOTES_DIR.mkdir(parents=True, exist_ok=True)

    total = 0
    synced = 0
    skipped = 0

    for scan_folder_name in SCAN_FOLDERS:
        scan_folder = OBSIDIAN_VAULT / scan_folder_name
        if not scan_folder.exists():
            print(f"[warning] Scan folder not found: {scan_folder}", file=sys.stderr)
            continue

        for src in scan_folder.rglob("*.md"):
            if src.name.startswith("_"):
                continue
            total += 1
            rel_path = src.relative_to(OBSIDIAN_VAULT)
            slug = make_slug(rel_path)
            dst = NOTES_DIR / f"{slug}.md"

            if not needs_resync(src, dst):
                skipped += 1
                continue

            try:
                mirror_note(src, dst, scan_folder)
                synced += 1
                print(f"Synced: {slug}", file=sys.stderr)
            except Exception as e:
                print(f"Error mirroring {src}: {e}", file=sys.stderr)

    print(f"Total: {total} | Synced: {synced} | Skipped: {skipped}")

if __name__ == "__main__":
    main()
