"""
_config.py — load wiki-root config.yaml into a dotted-access dict.

stdlib-only. Handles a small YAML subset:
  - 2-space indent, max 2 nesting levels
  - scalars: bare / 'single' / "double" quoted
  - integers (digits-only token)
  - booleans: true/false (case-insensitive)
  - lists: lines starting with "- " under a parent key
  - comments: "# ..." trailing or full-line

Usage:
    from _config import CFG
    obsidian = CFG.paths.obsidian_root          # str
    folders  = CFG.notes_ingest.scan_folders    # list[str]
    timeout  = CFG.zotero.http_timeout          # int

The loader is called once at import time. If config.yaml is missing,
ConfigMissingError is raised with a clear message pointing to the wiki root.
"""

# --- 1. Imports + error type ------------------------------------------------

from pathlib import Path
import re
import sys

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


class ConfigMissingError(RuntimeError):
    pass


# --- 2. Mini YAML parser (subset used by config.yaml) -----------------------

_INT_RE = re.compile(r"^-?\d+$")


_DQUOTE_ESCAPES = {
    "\\": "\\", '"': '"', "n": "\n", "t": "\t", "r": "\r", "/": "/",
}


def _unescape_dquoted(s: str) -> str:
    out, i, n = [], 0, len(s)
    while i < n:
        ch = s[i]
        if ch == "\\" and i + 1 < n and s[i + 1] in _DQUOTE_ESCAPES:
            out.append(_DQUOTE_ESCAPES[s[i + 1]])
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _parse_scalar(raw: str):
    s = raw.strip()
    if not s:
        return ""
    # double-quoted: process standard escapes
    if len(s) >= 2 and s[0] == '"' == s[-1]:
        return _unescape_dquoted(s[1:-1])
    # single-quoted: literal except '' → '
    if len(s) >= 2 and s[0] == "'" == s[-1]:
        return s[1:-1].replace("''", "'")
    # booleans
    low = s.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in ("null", "~"):
        return None
    # integers
    if _INT_RE.match(s):
        return int(s)
    # bare string
    return s


def _strip_comment(line: str) -> str:
    # Strip trailing "# ..." comments. We don't try to be clever about #
    # appearing inside quoted strings — config.yaml authors avoid that.
    in_single = in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i].rstrip()
    return line.rstrip()


def parse_yaml(text: str) -> dict:
    out: dict = {}
    section_dict: dict | None = None       # current 2nd-level dict
    list_target: list | None = None        # current list under a key
    list_indent: int | None = None

    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        # List item under an open list
        if stripped.startswith("- ") and list_target is not None and indent >= (list_indent or 0):
            list_target.append(_parse_scalar(stripped[2:]))
            continue
        else:
            list_target = None
            list_indent = None

        if ":" not in stripped:
            continue
        key, _, val = stripped.partition(":")
        key = key.strip()
        val = val.strip()

        if indent == 0:
            # Top-level key
            if val == "":
                section_dict = {}
                out[key] = section_dict
            else:
                out[key] = _parse_scalar(val)
                section_dict = None
        else:
            # Nested key (under most-recent top-level section)
            if section_dict is None:
                continue
            if val == "":
                # Either an empty string or the parent of a list
                section_dict[key] = []
                list_target = section_dict[key]
                list_indent = indent + 2
            else:
                section_dict[key] = _parse_scalar(val)

    return out


# --- 3. Dotted-access wrapper ----------------------------------------------


class _DotDict:
    """Read-only attribute access over a nested dict."""

    __slots__ = ("_d",)

    def __init__(self, d: dict):
        object.__setattr__(self, "_d", d)

    def __getattr__(self, k):
        if k not in self._d:
            raise AttributeError(f"config has no key: {k}")
        v = self._d[k]
        if isinstance(v, dict):
            return _DotDict(v)
        return v

    def __getitem__(self, k):
        return self.__getattr__(k)

    def get(self, k, default=None):
        return self._d.get(k, default)

    def to_dict(self):
        return dict(self._d)


# --- 4. One-shot loader -----------------------------------------------------


def _load() -> _DotDict:
    if not CONFIG_PATH.exists():
        raise ConfigMissingError(
            f"config.yaml not found at {CONFIG_PATH}. "
            f"Copy config.example.yaml to config.yaml and edit paths for your machine."
        )
    text = CONFIG_PATH.read_text(encoding="utf-8")
    return _DotDict(parse_yaml(text))


CFG = _load()


# --- 5. CLI for shell scripts ----------------------------------------------
# Usage:  python _config.py paths.python_exe
# Prints the value of a dotted key. Used by start_watcher.bat and
# cowork_dispatch.sh to read config values from non-Python contexts.

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python _config.py <dotted.key>", file=sys.stderr)
        sys.exit(2)
    cur = CFG
    for part in sys.argv[1].split("."):
        cur = getattr(cur, part)
    if isinstance(cur, list):
        print("\n".join(str(x) for x in cur))
    else:
        print(cur)
