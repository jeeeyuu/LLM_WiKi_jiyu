"""
batch_extract.py — Zotero storage → papers/{stem}.fulltext.md

Pure local Python. Zero LLM tokens. Idempotent.

Reads Zotero SQLite, computes a canonical stem per paper, and writes
extracted PDF text to papers/{stem}.fulltext.md. Skips papers whose cache
is already present and newer than the source PDF.

Configuration: Set environment variables or edit config.yaml:
  - ZOTERO_DIR: path to Zotero data directory (default: ~/Zotero)
  - WIKI_ROOT: path to wiki root (default: current directory)

Usage (PowerShell/bash):
    python _scripts/batch_extract.py                    # incremental
    python _scripts/batch_extract.py --force            # re-extract all
    python _scripts/batch_extract.py --limit 5          # smoke test
    python _scripts/batch_extract.py --item-key ABCD12  # single paper

Requirements:
    pip install pypdf
    pip install opendataloader-pdf   # optional, needs Java in PATH
"""

# --- 1. Configuration --------------------------------------------------------

import argparse
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _stem import make_stem      # canonical stem function (CLAUDE.md §4)

# Environment-based configuration (with sensible defaults)
ZOTERO_DIR    = Path(os.getenv("ZOTERO_DIR", Path.home() / "Zotero"))
ZOTERO_DB     = ZOTERO_DIR / "zotero.sqlite"
ZOTERO_STORE  = ZOTERO_DIR / "storage"

WIKI_ROOT     = Path(os.getenv("WIKI_ROOT", Path.cwd()))
PAPERS_DIR    = WIKI_ROOT / "papers"

EXTRACTOR_VER = "1.0.0"

# --- 2. Initialization & Validation -----------------------------------------

def validate_config():
    """Check that paths exist and are accessible."""
    if not ZOTERO_DB.exists():
        print(f"ERROR: Zotero database not found: {ZOTERO_DB}", file=sys.stderr)
        print(f"  Set ZOTERO_DIR environment variable or check path.", file=sys.stderr)
        sys.exit(1)
    if not ZOTERO_STORE.exists():
        print(f"ERROR: Zotero storage not found: {ZOTERO_STORE}", file=sys.stderr)
        sys.exit(1)
    if not WIKI_ROOT.exists():
        print(f"ERROR: Wiki root not found: {WIKI_ROOT}", file=sys.stderr)
        sys.exit(1)
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)

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
    **attachment** key (the PDF itself); both are matched.
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
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            return "".join(page.extract_text() for page in reader.pages)
    except Exception as e:
        print(f"  pypdf failed: {e}", file=sys.stderr)
        return None

def extract_pdf(pdf_path: Path) -> str | None:
    """Try opendataloader first, fall back to pypdf."""
    text = extract_with_opendataloader(pdf_path)
    if text is not None:
        return text
    return extract_with_pypdf(pdf_path)

# --- 5. Main extraction logic -----------------------------------------------

def should_extract(stem: str, pdf_path: Path, force: bool) -> bool:
    """Check if fulltext cache is missing or stale."""
    cache_path = PAPERS_DIR / f"{stem}.fulltext.md"
    if force:
        return True
    if not cache_path.exists():
        return True
    return cache_path.stat().st_mtime < pdf_path.stat().st_mtime

def write_fulltext(stem: str, text: str, meta: dict):
    """Write papers/{stem}.fulltext.md with frontmatter."""
    frontmatter = f"""---
title: "{meta['title']}"
authors: "{meta['authors_first']}, ..."
year: {meta['year']}
doi: {meta['doi'] or 'N/A'}
pmid: {meta['pmid'] or 'N/A'}
zotero_item_key: {meta['zotero_item_key']}
source_type: paper
extracted_at: {datetime.now(timezone.utc).isoformat()}
extractor_version: {EXTRACTOR_VER}
---
"""
    output_path = PAPERS_DIR / f"{stem}.fulltext.md"
    output_path.write_text(frontmatter + text, encoding="utf-8")
    return output_path

def main():
    parser = argparse.ArgumentParser(description="Extract PDFs from Zotero storage.")
    parser.add_argument("--force", action="store_true", help="Re-extract all papers")
    parser.add_argument("--limit", type=int, default=None, help="Process only N papers")
    parser.add_argument("--item-key", type=str, default=None, help="Extract single paper by item key")
    args = parser.parse_args()

    validate_config()

    try:
        conn = sqlite3.connect(str(ZOTERO_DB), uri=False, timeout=5)
        conn.execute("PRAGMA query_only=true")
    except sqlite3.DatabaseError as e:
        print(f"ERROR: Could not open Zotero database (is it locked?): {e}", file=sys.stderr)
        sys.exit(1)

    total = 0
    extracted = 0
    failed = 0

    try:
        for i, (item_key, stem, pdf_path, meta) in enumerate(iter_papers(conn, args.item_key)):
            if args.limit and i >= args.limit:
                break
            total += 1
            if not should_extract(stem, pdf_path, args.force):
                continue

            print(f"[{i+1}] Extracting {stem}...", file=sys.stderr)
            text = extract_pdf(pdf_path)
            if text:
                write_fulltext(stem, text, meta)
                extracted += 1
                print(f"      ✓ {len(text)} chars", file=sys.stderr)
            else:
                failed += 1
                print(f"      ✗ extraction failed", file=sys.stderr)
    finally:
        conn.close()

    print(f"Total: {total} | Extracted: {extracted} | Failed: {failed} | Skipped: {total - extracted - failed}")

if __name__ == "__main__":
    main()
