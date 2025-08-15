import re
from typing import Optional, Tuple, Iterable

ARTICLE_LABEL_RE = re.compile(r'^(ARTICLE\s+(?:[IVXLC]+|\d+))\s+(.+)$', re.I)
SECTION_LABEL_RE = re.compile(r'^((\d+(?:\.\d+)*)(?:\([a-z]\))?)\s+(.+)$')
EXHIBIT_LABEL_RE = re.compile(r'^(Exhibit\s+[A-Z0-9\-]+)\s*(.*)$', re.I)
CROSSREF_RE = re.compile(r'\b(Section\s+\d+(?:\.\d+)*(?:\([a-z]\))?|Exhibit\s+[A-Z0-9\-]+|Article\s+[IVXLC]+)\b')
DEF_RE = re.compile(r'\b(?:the|a|an)\s*[“"\'‘]?([A-Z][A-Za-z0-9 \-\/&]{1,100}?)["”’\']\s*\)?')

def parse_label_title_level(text: str, explicit_level: Optional[int] = None) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """
    Extract label, title, and level from heading-like text.
    If explicit_level is provided (e.g., from metadata.level), it takes priority.
    """
    t = (text or "").strip()
    if not t:
        # nothing to parse
        return None, None, (int(explicit_level) if explicit_level is not None else None)

    label: Optional[str] = None
    title: Optional[str] = None
    level: Optional[int] = None

    # Respect explicit level if caller provided one
    if explicit_level is not None:
        try:
            level = int(explicit_level)
        except (ValueError, TypeError):
            level = None

    m = ARTICLE_LABEL_RE.match(t)
    if m:
        label = m.group(1).strip()
        title = m.group(2).strip()
        # Articles are top-level unless caller already set a level
        if level is None:
            level = 0
        return label, title, level

    m = SECTION_LABEL_RE.match(t)
    if m:
        label = m.group(1).strip()
        title = m.group(3).strip()
        if level is None:
            # infer depth: count dots + parentheses indicator
            level = label.count(".") + (1 if "(" in label else 0) + 1
        return label, title, level

    m = EXHIBIT_LABEL_RE.match(t)
    if m:
        label = m.group(1).strip()
        t2 = (m.group(2) or "").strip()
        title = t2 if t2 else None
        if level is None:
            level = 0
        return label, title, level

    # No label pattern; keep explicit level if provided, otherwise None
    return None, None, level

def iter_cross_refs(text: str) -> Iterable[re.Match]:
    if not text:
        return []
    return CROSSREF_RE.finditer(text)

def iter_def_terms(sentence: str):
    return DEF_RE.finditer(sentence)
