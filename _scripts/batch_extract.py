"""
batch_extract.py — Zotero storage → papers/{stem}.fulltext.md

Pure local Python. Zero LLM tokens. Idempotent.

Reads Zotero SQLite, computes a canonical stem per paper, and writes
extracted PDF text to papers/{stem}.fulltext.md. Skips papers whose cache
is already present and newer than the source PDF.

Configuration: Requires config.yaml with zotero.data_dir and extractor settings.
See config.example.yaml for reference.

Usage (Windows PowerShell):
    cd "path\to\llm-wiki"
    python _scripts\batch_extract.py                    # incremental
    python _scripts\batch_extract.py --force            # re-extract all
    python _scripts\batch_extract.py --limit 5          # smoke test
    python _scripts\batch_extract.py --item-key ABCD12  # single paper

Requirements:
    pip install pypdf
    pip install opendataloader-pdf   # optional, needs Java in PATH

CRITICAL: Zotero must be CLOSED (otherwise zotero.sqlite is locked).
"""

# --- 1. Configuration --------------------------------------------------------

import argparse
import re
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _stem import make_stem      # canonical stem function (CLAUDE.md §4)
from _config import CFG          # personal config (config.yaml)

ZOTERO_DIR    = Path(CFG.paths.zotero_dir)
ZOTERO_DB     = ZOTERO_DIR / "zotero.sqlite"
ZOTERO_STORE  = ZOTERO_DIR / "storage"

WIKI_DIR      = Path(__file__).resolve().parent.parent
PAPERS_DIR    = WIKI_DIR / "papers"

EXTRACTOR_VER = CFG.extractor.version

# --- 3. Zotero metadata reader ----------------------------------------------

def field(conn, item_id, name):
    cur = conn.execute(
        "SELECT v.value FROM itemData d "
        "JOIN itemDataValues v ON d.valueID = v.valueID "
        "JOIN fields f ON d.fieldID = f.fieldID "
        "WHERE d.itemID = ? AND f.fieldName = ?",
        (item_id, name),
    )
    row = cur.fetchone()
    return row[0] if row else None

def first_author(conn, item_id):
    cur = conn.execute(
        "SELECT c.lastName FROM itemCreators ic "
        "JOIN creators c ON ic.creatorID = c.creatorID "
        "JOIN creatorTypes ct ON ic.creatorTypeID = ct.creatorTypeID "
        "WHERE ic.itemID = ? AND ct.creatorType = 'author' "
        "ORDER BY ic.orderIndex LIMIT 1",
        (item_id,),
    )
    row = cur.fetchone()
    return row[0] if row else "anon"

def extract_year(date_str):
    if not date_str: return None
    m = re.match(r"(\d{4})", date_str)
    return m.group(1) if m else None

def extract_pmid(extra: str):
    if not extra: return None
    m = re.search(r"PMID:\s*(\d+)", extra)
    return m.group(1) if m else None

def iter_papers(conn, item_key_filter=None):
    """Yield (item_key, stem, pdf_path, meta) for every PDF in the library.

    `item_key_filter` can be either the **parent** item key (the paper) or the
    **attachment** key (the PDF itself); both are matched. Zotero Integration
    exports tend to embed the attachment key in the `zotero://select/...` link,
    so we must accept both.
    """
    sql = """
        SELECT parent.itemID, parent.key, att.path, att_item.key
        FROM itemAttachments att
        JOIN items att_item ON att.itemID = att_item.itemID
        JOIN items parent   ON att.parentItemID = parent.itemID
        WHERE att.contentType = 'application/pdf'
          AND att.path LIKE 'storage:%'
          AND parent.itemID NOT IN (SELECT itemID FROM deletedItems)
    """
    for parent_id, parent_key, att_path, att_key in conn.execute(sql):
        if item_key_filter and parent_key != item_key_filter and att_key != item_key_filter:
            continue
        filename = att_path.removeprefix("storage:")
        pdf_path = ZOTERO_STORE / att_key / filename
        if not pdf_path.exists():
            continue
        title = field(conn, parent_id, "title") or "untitled"
        year  = extract_year(field(conn, parent_id, "date"))
        doi   = field(conn, parent_id, "DOI")
        pmid  = extract_pmid(field(conn, parent_id, "extra"))
        last  = first_author(conn, parent_id)
        meta = {
            "title": title, "authors_first": last, "year": year,
            "doi": doi, "pmid": pmid, "zotero_item_key": parent_key,
        }
        yield parent_key, make_stem(last, year, title), pdf_path, meta

# --- 4. PDF extraction (opendataloader-pdf primary, pypdf fallback) ---------

def extract_with_opendataloader(pdf_path: Path) -> str | None:
    try:
        import opendataloader_pdf
    except ImportError:
        return None
    if shutil.which("java") is None:
        return None
    try:
        with tempfile.TemporaryDirectory() as d:
            opendataloader_pdf.convert(
                str(pdf_path), output_dir=d, format="markdown",
                image_output="off", quiet=True,
            )
            stem = pdf_path.stem
            out = Path(d) / f"{stem}.md"
            if not out.exists():
                return None
            text = out.read_text(encoding="utf-8")
            # drop image placeholders
            return "\n".join(
                l for l in text.splitlines() if not re.match(r"!\[image \d+\]", l)
            )
    except Exception as e:
        print(f"  opendataloader failed: {e}", file=sys.stderr)
        return None

def extract_with_pypdf(pdf_path: Path) -> str | None:
    try:
        import pypdf
    except ImportError:
        print("ERROR: install pypdf (pip install pypdf)", file=sys.stderr)
        sys.exit(2)
    try:
        reader = pypdf.PdfReader(str(pdf_path))
        chunks = []
        for page in reader.pages:
            t = page.extract_text()
            if t: chunks.append(t)
        return "\n\n".join(chunks)
    except Exception as e:
        print(f"  pypdf failed: {e}", file=sys.stderr)
        return None

def extract_text(pdf_path: Path) -> tuple[str, str] | None:
    """Returns (text, extractor_name) or None."""
    text = extract_with_opendataloader(pdf_path)
    if text and text.strip():
        return text, "opendataloader-pdf"
    text = extract_with_pypdf(pdf_path)
    if text and text.strip():
        return text, "pypdf"
    return None

# --- 5. Cache + write --------------------------------------------------------

def is_stale(pdf_path: Path, cache_path: Path, force: bool) -> bool:
    if force or not cache_path.exists():
        return True
    return pdf_path.stat().st_mtime > cache_path.stat().st_mtime

def write_cache(cache_path: Path, text: str, meta: dict, extractor: str):
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    fm = (
        "---\n"
        f"title: {meta['title']!r}\n"
        f"authors_first: {meta['authors_first']!r}\n"
        f"year: {meta['year'] or 'null'}\n"
        f"doi: {meta['doi'] or 'null'}\n"
        f"pmid: {meta['pmid'] or 'null'}\n"
        f"zotero_item_key: {meta['zotero_item_key']}\n"
        f"extracted_at: {datetime.now(timezone.utc).isoformat()}\n"
        f"extractor: {extractor}\n"
        f"extractor_version: {EXTRACTOR_VER}\n"
        "source_type: paper_fulltext\n"
        "---\n\n"
    )
    cache_path.write_text(fm + text, encoding="utf-8")

# --- 6. Main loop ------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-extract everything")
    ap.add_argument("--limit", type=int, help="process only N papers")
    ap.add_argument("--item-key", help="single Zotero item key")
    ap.add_argument("--prioritize-paired", action="store_true",
                    help="process papers matching existing highlight stems first")
    args = ap.parse_args()

    if not ZOTERO_DB.exists():
        sys.exit(f"ERROR: {ZOTERO_DB} not found. Adjust ZOTERO_DIR.")
    PAPERS_DIR.mkdir(exist_ok=True)

    # immutable=1: read-only mode tolerates Zotero's WAL but not an active write lock
    conn = sqlite3.connect(f"file:{ZOTERO_DB}?mode=ro&immutable=1", uri=True)

    # --- Optional: prioritize papers whose stem matches an existing highlight file
    paired_stems = set()
    if args.prioritize_paired:
        for f in PAPERS_DIR.glob("*.md"):
            if f.name.startswith("_") or f.name.endswith(".fulltext.md"):
                continue
            paired_stems.add(f.stem)
        print(f"Prioritizing {len(paired_stems)} stems with existing highlights",
              file=sys.stderr)

    all_items = list(iter_papers(conn, args.item_key))
    if paired_stems:
        paired = [p for p in all_items if p[1] in paired_stems]
        others = [p for p in all_items if p[1] not in paired_stems]
        ordered = paired + others
    else:
        ordered = all_items

    n_total = n_extracted = n_skipped = n_failed = 0
    for item_key, stem, pdf_path, meta in ordered:
        if args.limit and n_total >= args.limit: break
        n_total += 1
        cache_path = PAPERS_DIR / f"{stem}.fulltext.md"
        if not is_stale(pdf_path, cache_path, args.force):
            n_skipped += 1
            continue
        print(f"[{n_total}] {stem}")
        result = extract_text(pdf_path)
        if not result:
            print("  FAILED", file=sys.stderr)
            n_failed += 1
            continue
        text, extractor = result
        write_cache(cache_path, text, meta, extractor)
        n_extracted += 1

    conn.close()
    print(f"\nTotal: {n_total} | Extracted: {n_extracted} | "
          f"Cached(skip): {n_skipped} | Failed: {n_failed}")

if __name__ == "__main__":
    main()
