"""
_stem.py — Canonical stem generation for papers

Produces a deterministic stem from paper metadata (author, year, title).
Used by batch_extract.py and other scripts to ensure consistent naming.

Stem format:
    {first-author-lastname}-{year}-{first-3-non-stopword-title-words}

Examples:
    smith-2024-cryo-em-structure
    bhatia-2025-bioinformatics-framework-singlecell
    paoli-iseppi-2024-long-read-sequencing

See CLAUDE.md §4 for full specification.
"""

import re
import unicodedata

# Stopwords to skip in title (articles, prepositions, conjunctions, copulas)
STOP_WORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'do', 'for', 'from',
    'in', 'is', 'it', 'of', 'on', 'or', 'the', 'to', 'with', 'was', 'were',
    'that', 'this', 'these', 'those', 'can', 'could', 'should', 'would',
}

def ascii_fold(text: str) -> str:
    """Fold accented characters to ASCII equivalents."""
    if not text:
        return text
    # Decompose accented chars, drop accents
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')

def make_stem(author_lastname: str, year: str | int, title: str) -> str:
    """
    Generate canonical stem from paper metadata.

    Args:
        author_lastname: First author's last name (e.g., 'Smith', 'De Paoli-Iseppi')
        year: Publication year (int or str, e.g., 2024)
        title: Paper title (e.g., 'Cryo-EM structure of X protein')

    Returns:
        Stem string (e.g., 'smith-2024-cryo-em-structure')
    """
    # Sanitize author name
    author = ascii_fold(author_lastname).lower() if author_lastname else 'anon'
    # Preserve internal hyphens, strip leading/trailing
    author = re.sub(r'^[\W_]+|[\W_]+$', '', author)
    # Collapse internal non-alphanumeric sequences to single hyphen
    author = re.sub(r'[\W_]+', '-', author)

    # Year (4 digits)
    year_str = str(year).strip()
    if not year_str or not year_str.isdigit():
        year_str = 'xxxx'

    # Title processing: extract first 3 non-stopword tokens
    title_lower = ascii_fold(title).lower() if title else 'untitled'
    # Tokenize on whitespace and hyphens
    tokens = re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)*', title_lower)

    title_words = []
    for token in tokens:
        # Check if this token (or its component) is a stopword
        components = token.split('-')
        components = [c for c in components if c not in STOP_WORDS]
        if components:
            # Join components back, treating hyphenated compound as one token
            title_words.append(''.join(components))  # Remove hyphens within compounds
        if len(title_words) >= 3:
            break

    # Fallback if title has no non-stopword tokens
    if not title_words:
        title_words = tokens[:3]

    # Assemble stem
    stem_parts = [author, year_str] + title_words[:3]
    stem = '-'.join(p for p in stem_parts if p)

    return stem

# Test cases
if __name__ == '__main__':
    tests = [
        ('Smith', 2024, 'Cryo-EM structure of the large-scale ribosome complex'),
        ('Bhatia', 2025, 'Bioinformatics frameworks for single-cell analysis'),
        ('De Paoli-Iseppi', 2024, 'Long-read sequencing reveals complex isoforms'),
        ('Müller', 2023, 'The structure and function of X protein'),
    ]

    for author, year, title in tests:
        stem = make_stem(author, year, title)
        print(f"{author}, {year}: {title}")
        print(f"  → {stem}\n")
