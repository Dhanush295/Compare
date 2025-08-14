from typing import Any, Dict, List, Optional, Tuple

_PRIMARY_TEXT_KEYS = [
    "text", "content", "value", "body", "raw_text", "ocr_text", "paragraph",
    "string", "title", "name", "description"
]
_SECONDARY_CANDIDATE_KEYS = [
    "lines", "spans", "sentences", "paragraphs", "tokens", "fragments"
]
_NESTED_TEXT_PATHS = [
    "metadata.text",
    "metadata.title",
    "metadata.name",
    "data.text",
    "attributes.text",
]

def _get_path(obj: Dict[str, Any], path: str) -> Optional[Any]:
    cur: Any = obj
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
        if cur is None:
            return None
    return cur

def _normalize_text(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return " ".join(x.split())
    if isinstance(x, (list, tuple)):
        parts: List[str] = []
        for item in x:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if "text" in item and isinstance(item["text"], str):
                    parts.append(item["text"])
        return " ".join(" ".join(parts).split())
    if isinstance(x, dict):
        if "text" in x and isinstance(x["text"], str):
            return " ".join(x["text"].split())
    return ""

def extract_text_candidates(el: Dict[str, Any]) -> List[Tuple[str, str]]:
    found: List[Tuple[str, str]] = []

    for k in _PRIMARY_TEXT_KEYS:
        if k in el:
            t = _normalize_text(el.get(k))
            if t:
                found.append((k, t))

    for path in _NESTED_TEXT_PATHS:
        v = _get_path(el, path)
        t = _normalize_text(v)
        if t:
            found.append((path, t))

    for k in _SECONDARY_CANDIDATE_KEYS:
        if k in el:
            t = _normalize_text(el.get(k))
            if t:
                found.append((k, t))

    md = el.get("metadata")
    if isinstance(md, dict):
        for k in _PRIMARY_TEXT_KEYS + _SECONDARY_CANDIDATE_KEYS:
            if k in md:
                t = _normalize_text(md.get(k))
                if t:
                    found.append((f"metadata.{k}", t))

    seen = set()
    uniq: List[Tuple[str, str]] = []
    for src, txt in found:
        key = (src, txt)
        if key not in seen:
            seen.add(key)
            uniq.append((src, txt))
    return uniq

def extract_best_text(el: Dict[str, Any]) -> Tuple[str, Optional[str], List[str]]:
    cands = extract_text_candidates(el)
    if not cands:
        return "", None, []
    best_source, best_text = cands[0]
    all_texts = [t for _, t in cands]
    return best_text, best_source, all_texts
