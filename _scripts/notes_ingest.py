"""
notes_ingest.py — Obsidian external notes → notes/{slug}.md

Pure local Python. Zero LLM tokens.

Mirrors the user-designated Obsidian folders into notes/, injecting
frontmatter so the wiki agent can treat them as first-class citations.
Long notes (>32 KB) are head+tail truncated; the agent can read the
original via `original_path` if it needs more.

Configuration: Requires config.yaml with paths.obsidian_root and notes_ingest settings.
See config.example.yaml for reference.

Usage (Windows PowerShell):
    cd "path\to\repo"
    python _scripts\notes_ingest.py
"""

# --- 1. Configuration --------------------------------------------------------

import hashlib
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import CFG

OBSIDIAN_ROOT = Path(CFG.paths.obsidian_root)
SCAN_FOLDERS  = list(CFG.notes_ingest.scan_folders)

WIKI_DIR  = Path(__file__).resolve().parent.parent
NOTES_DIR = WIKI_DIR / "notes"

VERBATIM_THRESHOLD = CFG.notes_ingest.verbatim_threshold_kb * 1024
HEAD_BYTES         = CFG.notes_ingest.head_bytes_kb * 1024
TAIL_BYTES         = CFG.notes_ingest.tail_bytes_kb * 1024

# --- 2. Slug generation ------------------------------------------------------

# Korean → romanized fallback is overkill; we keep Hangul in slugs since
# Obsidian and the wiki agent both handle UTF-8 filenames cleanly. We only
# strip filesystem-illegal characters and collapse whitespace.

ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

def make_slug(rel_path: Path) -> str:
    """Relative path inside OBSIDIAN_ROOT → flat kebab-style slug."""
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
    head = raw[:HEAD_BYTES].decode("utf-8", errors="replace")
    tail = raw[-TAIL_BYTES:].decode("utf-8", errors="replace")
    sep = (
        f"\n\n---\n"
        f"_[TRUNCATED — original is {len(raw):,} bytes; "
        f"see frontmatter `original_path` for full text]_\n"
        f"---\n\n"
    )
    return head + sep + tail, True

def write_mirror(src: Path, dst: Path):
    body, truncated = render_body(src)
    rel = src.relative_to(OBSIDIAN_ROOT)
    h = src_hash(src)
    fm = (
        "---\n"
        "source_type: lab_note\n"
        f"original_path: {str(src).replace(chr(92), '/')!r}\n"
        f"original_relpath: {str(rel).replace(chr(92), '/')!r}\n"
        f"original_mtime: {datetime.fromtimestamp(src.stat().st_mtime, timezone.utc).isoformat()}\n"
        f"last_synced: {datetime.now(timezone.utc).isoformat()}\n"
        f"source_hash: '{h}'\n"
        f"truncated: {str(truncated).lower()}\n"
        f"original_size_bytes: {src.stat().st_size}\n"
        "---\n\n"
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(fm + body, encoding="utf-8")

def main():
    if not OBSIDIAN_ROOT.exists():
        sys.exit(f"ERROR: {OBSIDIAN_ROOT} not found.")
    NOTES_DIR.mkdir(exist_ok=True)

    n_total = n_synced = n_skipped = 0
    for folder in SCAN_FOLDERS:
        root = OBSIDIAN_ROOT / folder
        if not root.exists():
            print(f"WARN: missing folder {root}", file=sys.stderr)
            continue
        for src in root.rglob("*.md"):
            n_total += 1
            slug = make_slug(src.relative_to(OBSIDIAN_ROOT))
            dst = NOTES_DIR / f"{slug}.md"
            if not needs_resync(src, dst):
                n_skipped += 1
                continue
            write_mirror(src, dst)
            n_synced += 1
            print(f"  + {slug}")

    print(f"\nScanned: {n_total} | Mirrored: {n_synced} | "
          f"Up-to-date(skip): {n_skipped}")

if __name__ == "__main__":
    main()
