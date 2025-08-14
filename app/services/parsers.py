import re
from typing import Optional, Tuple, Iterable

ARTICLE_LABEL_RE = re.compile(r'^(ARTICLE\s+(?:[IVXLC]+|\d+))\s+(.+)$', re.I)
SECTION_LABEL_RE = re.compile(r'^((\d+(?:\.\d+)*)(?:\([a-z]\))?)\s+(.+)$')
EXHIBIT_LABEL_RE = re.compile(r'^(Exhibit\s+[A-Z0-9\-]+)\s*(.*)$', re.I)
CROSSREF_RE = re.compile(r'\b(Section\s+\d+(?:\.\d+)*(?:\([a-z]\))?|Exhibit\s+[A-Z0-9\-]+|Article\s+[IVXLC]+)\b')
DEF_RE = re.compile(r'\b(?:the|a|an)\s*[“"\'‘]?([A-Z][A-Za-z0-9 \-\/&]{1,100}?)["”’\']\s*\)?')

def parse_label_title_level(text: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    t = (text or "").strip()
    if not t:
        return None, None, None
    m = ARTICLE_LABEL_RE.match(t)
    if m:
        return m.group(1).strip(), m.group(2).strip(), 0
    m = SECTION_LABEL_RE.match(t)
    if m:
        label = m.group(1).strip()
        title = m.group(3).strip()
        level = label.count(".") + (1 if "(" in label else 0) + 1
        return label, title, level
    m = EXHIBIT_LABEL_RE.match(t)
    if m:
        return m.group(1).strip(), (m.group(2) or None), 0
    return None, None, None

def iter_cross_refs(text: str) -> Iterable[re.Match]:
    if not text:
        return []
    return CROSSREF_RE.finditer(text)

def iter_def_terms(sentence: str):
    return DEF_RE.finditer(sentence)
