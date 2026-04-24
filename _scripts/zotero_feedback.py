"""
zotero_feedback.py — wiki cross-references → Zotero tags + related items

Pure local Python. Zero LLM tokens.

For every wiki page with a `zotero_item_key` in frontmatter, pushes:
  - tags:    wiki:cat/{category}, wiki:overview/{topic_slug}
  - related: Zotero "Related Items" links to other items whose item_key
             appears as a [[wikilink]] target in this page.

Configuration: Set environment variables or edit config.yaml:
  - ZOTERO_API_BASE: Zotero local API endpoint (default: http://127.0.0.1:23119/api/users/0)
  - WIKI_ROOT: path to wiki root (default: current directory)

Usage (PowerShell/bash):
    python _scripts/zotero_feedback.py            # incremental
    python _scripts/zotero_feedback.py --full     # ignore last-sync marker
    python _scripts/zotero_feedback.py --dry-run  # show what would change

Requires Zotero to be RUNNING (local HTTP API on port 23119).
API is additive: existing user tags are preserved; only `wiki:*` tags are
reconciled. Related items are unioned, never removed.

Requirements:
    pip install requests
"""

# --- 1. Configuration --------------------------------------------------------

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WIKI_ROOT      = Path(os.getenv("WIKI_ROOT", Path.cwd()))
WIKI_PAGES_DIR = WIKI_ROOT / "wiki"
SOURCES_DIR    = WIKI_ROOT / "sources"
LAST_RUN_FILE  = Path(__file__).resolve().parent / ".last_zotero_sync"

ZOTERO_API_BASE = os.getenv("ZOTERO_API_BASE", "http://127.0.0.1:23119/api/users/0")
HTTP_TIMEOUT    = 10

# --- 2. Frontmatter parser (dependency-free, handles YAML subset) ---

FM_BLOCK = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

def parse_frontmatter(text: str) -> dict:
    m = FM_BLOCK.match(text)
    if not m: return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" not in line: continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip().strip("'\"")
    return fm

# --- 3. Wiki scan + backlink discovery ---------------------------------------

WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
STEM_FROM_LINK = re.compile(r"(?:.*/)?([a-z0-9][a-z0-9\-]*)$")

def iter_wiki_pages(mtime_floor: float | None):
    """Yield (path, frontmatter, body) for every relevant wiki md."""
    for p in list(WIKI_PAGES_DIR.rglob("*.md")) + list(SOURCES_DIR.rglob("*.md")):
        if p.name.startswith("_"): continue
        if mtime_floor and p.stat().st_mtime <= mtime_floor: continue
        text = p.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        if not fm.get("zotero_item_key"): continue
        yield p, fm, text

def build_stem_to_key() -> dict[str, str]:
    """Map wiki stem → zotero_item_key by scanning all source pages."""
    out = {}
    for p in SOURCES_DIR.rglob("*.md"):
        fm = parse_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
        key = fm.get("zotero_item_key")
        if key: out[p.stem] = key
    return out

def extract_tags_and_related(fm: dict, body: str,
                             stem_to_key: dict[str, str]) -> tuple[set, set]:
    tags = set()
    if fm.get("category"):
        tags.add(f"wiki:cat/{fm['category']}")
    related_keys = set()
    for link in WIKILINK.findall(body):
        target = link.split("|")[0].strip()
        if target.startswith("wiki/overviews/") or target.startswith("overviews/"):
            topic = target.rsplit("/", 1)[-1]
            tags.add(f"wiki:overview/{topic}")
        m = STEM_FROM_LINK.match(target.rsplit("/", 1)[-1])
        if m:
            stem = m.group(1)
            key = stem_to_key.get(stem)
            if key and key != fm.get("zotero_item_key"):
                related_keys.add(key)
    return tags, related_keys

# --- 4. Zotero local API client ---------------------------------------------

try:
    import requests
except ImportError:
    sys.exit("ERROR: install requests (pip install requests)")

def get_item(item_key: str) -> dict | None:
    try:
        r = requests.get(f"{ZOTERO_API_BASE}/items/{item_key}", timeout=HTTP_TIMEOUT)
        if r.status_code != 200:
            print(f"  GET {item_key}: HTTP {r.status_code}", file=sys.stderr)
            return None
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"  GET {item_key}: {e}", file=sys.stderr)
        return None

def patch_item(item_key: str, new_tags: set, new_related_keys: set,
               version: int, dry_run: bool) -> bool:
    existing = get_item(item_key)
    if not existing: return False
    data = existing["data"]

    # --- tags: preserve non-wiki:, replace wiki:* wholesale ---
    preserved = [t for t in data.get("tags", []) if not t["tag"].startswith("wiki:")]
    merged_tags = preserved + [{"tag": t} for t in sorted(new_tags)]

    # --- relations: union with existing 'dc:relation' links ---
    relations = data.get("relations", {})
    existing_rel = set(relations.get("dc:relation", []) if isinstance(
        relations.get("dc:relation"), list) else [relations.get("dc:relation")] if
        relations.get("dc:relation") else [])
    existing_rel.discard(None)
    new_rel_uris = {f"http://zotero.org/users/0/items/{k}" for k in new_related_keys}
    merged_rel = sorted(existing_rel | new_rel_uris)

    payload = {"tags": merged_tags}
    if merged_rel:
        payload["relations"] = {**relations, "dc:relation": merged_rel}

    if dry_run:
        print(f"  [dry-run] {item_key} would set "
              f"{len(merged_tags)} tags, {len(merged_rel)} relations")
        return True

    try:
        r = requests.patch(
            f"{ZOTERO_API_BASE}/items/{item_key}",
            headers={"If-Unmodified-Since-Version": str(version),
                     "Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=HTTP_TIMEOUT,
        )
        if r.status_code not in (200, 204):
            print(f"  PATCH {item_key}: HTTP {r.status_code} — {r.text[:200]}",
                  file=sys.stderr)
            return False
        return True
    except requests.exceptions.RequestException as e:
        print(f"  PATCH {item_key}: {e}", file=sys.stderr)
        return False

# --- 5. Main loop -----------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Sync wiki pages to Zotero.")
    parser.add_argument("--full", action="store_true", help="Ignore last-sync marker")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change")
    args = parser.parse_args()

    if not WIKI_ROOT.exists():
        print(f"ERROR: Wiki root not found: {WIKI_ROOT}", file=sys.stderr)
        sys.exit(1)
    if not WIKI_PAGES_DIR.exists():
        print(f"ERROR: Wiki pages dir not found: {WIKI_PAGES_DIR}", file=sys.stderr)
        sys.exit(1)

    mtime_floor = None if args.full else (LAST_RUN_FILE.stat().st_mtime if LAST_RUN_FILE.exists() else None)
    stem_to_key = build_stem_to_key()
    updated = 0
    failed = 0

    for p, fm, body in iter_wiki_pages(mtime_floor):
        item_key = fm.get("zotero_item_key")
        if not item_key:
            continue

        tags, related_keys = extract_tags_and_related(fm, body, stem_to_key)
        item = get_item(item_key)
        if not item:
            failed += 1
            continue

        if patch_item(item_key, tags, related_keys, item["library"]["version"], args.dry_run):
            updated += 1
            print(f"Updated {item_key} ({p.name})", file=sys.stderr)
        else:
            failed += 1

    if not args.dry_run:
        LAST_RUN_FILE.touch()

    print(f"Updated: {updated} | Failed: {failed}")

if __name__ == "__main__":
    main()
