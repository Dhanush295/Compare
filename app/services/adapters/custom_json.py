from typing import Any, Dict, List

# Map your block.tag -> our element.type
_TAG_TO_TYPE = {
    "header": "Title",
    "para": "NarrativeText",
    "list_item": "ListItem",
    "table": "Table",
    # keep unknowns but don't drop them
}

def _join_sentences(block: Dict[str, Any]) -> str:
    sents = block.get("sentences")
    if isinstance(sents, list):
        return " ".join([str(x).strip() for x in sents if isinstance(x, str) and x.strip()])
    # Fallbacks: sometimes a table cell carries text we can use
    name = block.get("name")
    return str(name).strip() if isinstance(name, str) else ""

def _table_to_text(block: Dict[str, Any]) -> str:
    """Flatten table_rows to readable lines."""
    rows = block.get("table_rows") or []
    lines: List[str] = []
    for row in rows:
        if row.get("type") == "full_row":
            val = row.get("cell_value")
            if isinstance(val, str) and val.strip():
                lines.append(val.strip())
            continue
        cells = row.get("cells") or []
        vals = [c.get("cell_value") for c in cells if isinstance(c, dict)]
        vals = [str(v).strip() for v in vals if isinstance(v, (str, int, float))]
        if vals:
            lines.append(" • ".join(vals))
    base = _join_sentences(block)
    if base:
        lines.insert(0, base)
    return "\n".join(lines).strip()

def _block_text(block: Dict[str, Any]) -> str:
    if block.get("tag") == "table":
        return _table_to_text(block)
    return _join_sentences(block)

def _coords(block: Dict[str, Any]):
    bb = block.get("bbox")
    return bb if isinstance(bb, list) else None

def _page_number(block: Dict[str, Any]) -> int:
    # incoming is 0-based
    idx = block.get("page_idx")
    return int(idx) + 1 if isinstance(idx, int) else None

def _element_id(block: Dict[str, Any]) -> str:
    # stable ID from page/block indexes
    p = block.get("page_idx")
    b = block.get("block_idx")
    tag = block.get("tag") or "blk"
    return f"{tag}-{p}-{b}"

def adapt_blocks_to_elements(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Accepts your uploaded shape:
      { "return_dict": { "result": { "blocks": [...] }, ... }, ... }
    Produces our generic `elements` list with:
      type, text, element_id, metadata.{page_number, coordinates, parent_id, level}
    Also infers parent-child from the 'level' and heading/list structure.
    """
    rd = (raw or {}).get("return_dict") or {}
    result = rd.get("result") or {}
    blocks = result.get("blocks") or []
    if not isinstance(blocks, list):
        return []

    # Sort for deterministic parent inference
    def _key(b):
        p = b.get("page_idx")
        i = b.get("block_idx")
        return ((p if isinstance(p, int) else 10**9), (i if isinstance(i, int) else 10**9))
    blocks_sorted = sorted(blocks, key=_key)

    elements: List[Dict[str, Any]] = []
    # Heading stack holds (level_index, element_id) for headers/list parents
    stack: List[tuple] = []

    for b in blocks_sorted:
        tag = b.get("tag") or "para"
        etype = _TAG_TO_TYPE.get(tag, "NarrativeText")
        text = _block_text(b)
        eid = _element_id(b)

        # Pick an integer "structural level" (lower is higher in the tree)
        # Your JSON uses small ints already (0,1,2...). If missing, infer from tag.
        raw_level = b.get("level")
        lvl = int(raw_level) if isinstance(raw_level, int) else (0 if tag == "header" else 1)

        # Parent inference:
        parent_id = None
        # Pop deeper stack levels until we fit
        while stack and stack[-1][0] >= lvl:
            stack.pop()
        if stack:
            parent_id = stack[-1][1]
        # If this looks like a header or a list subheading, push onto the stack
        if tag in ("header",):
            stack.append((lvl, eid))
        elif tag == "list_item":
            # treat list items as children of the current parent level
            # but do not push them as parents unless they look like subheaders
            pass
        elif tag == "para":
            # paragraphs belong to the current parent if any
            pass
        elif tag == "table":
            # table often belongs to nearest header/paragraph parent
            pass

        el = {
            "type": etype,
            "text": text,
            "element_id": eid,
            "metadata": {
                "page_number": _page_number(b),
                "coordinates": _coords(b),
                "parent_id": parent_id,
                "level": lvl,
                "tag": tag,
                "block_class": b.get("block_class"),
            }
        }
        elements.append(el)

    return elements

def looks_like_custom_blocks(raw: Any) -> bool:
    try:
        return isinstance(raw, dict) and "return_dict" in raw and "result" in raw["return_dict"] and isinstance(raw["return_dict"]["result"].get("blocks"), list)
    except Exception:
        return False
