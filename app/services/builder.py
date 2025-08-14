from typing import Any, Dict, List, Optional
import json
import re
from collections import defaultdict

from app.models.store import Store, DocumentHeader, Section, CrossRef, Definition, Span
from app.utils.ids import sha256_str, urn, now_iso
from app.services.parsers import parse_label_title_level, iter_cross_refs, iter_def_terms
from app.services.text import extract_best_text

def _get(obj: Dict[str, Any], path: List[str], default=None):
    cur = obj
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
        if cur is None:
            return default
    return cur

def _bbox_from_points(points: List[List[float]]) -> List[float]:
    xs = [p[0] for p in points if isinstance(p, (list, tuple)) and len(p) >= 2]
    ys = [p[1] for p in points if isinstance(p, (list, tuple)) and len(p) >= 2]
    if not xs or not ys:
        return []
    return [min(xs), min(ys), max(xs), max(ys)]

class StoreBuilder:
    """
    Non-graph, production-ready store builder.

    include_text_in_index: when True, puts full text into topology.section_index[*].text.
      Otherwise (default) stores text_snippet + text_len + text_hash.
    snippet_chars: length of text_snippet.
    """

    def __init__(
        self,
        elements: List[Dict[str, Any]],
        filename: str,
        schema_version: str = "1.0.0",
        extracted_with: str = "unknown",
        include_text_in_index: bool = False,
        snippet_chars: int = 280,
    ):
        self.elements = elements
        self.filename = filename
        self.schema_version = schema_version
        self.extracted_with = extracted_with
        self.include_text_in_index = include_text_in_index
        self.snippet_chars = snippet_chars
        self.created_at = now_iso()

        raw_json = json.dumps(elements, sort_keys=True)
        self.doc_hash = sha256_str(raw_json)
        self.doc_id = urn("doc", self.doc_hash)

        self.sections: List[Section] = []
        self.definitions: List[Definition] = []
        self.cross_refs: List[CrossRef] = []
        self._children_by_parent_element_id: Dict[Optional[str], List[Section]] = defaultdict(list)

    def build(self) -> Store:
        self._pass_sections()
        self._pass_crossrefs()
        self._pass_definitions()

        # children_by_parent map
        children_map = {
            self._sec_id_or_none(pid): [s.section_id for s in sorted(lst, key=lambda x: x.sequence)]
            for pid, lst in self._children_by_parent_element_id.items()
        }

        # section_index map with optional text
        section_index: Dict[str, Dict[str, Any]] = {}
        for s in self.sections:
            entry = {
                "section_id": s.section_id,
                "element_id": s.element_id,
                "sequence": s.sequence,
                "parent_element_id": s.parent_element_id,
                "label": s.label,
                "title": s.title,
                "level": s.level,
                "page_start": s.page_start,
                "page_end": s.page_end,
                "element_type": s.element_type,
            }
            txt = s.text or ""
            entry["text_len"] = len(txt)
            entry["text_hash"] = sha256_str(txt) if txt else None
            if self.include_text_in_index:
                entry["text"] = txt
            else:
                entry["text_snippet"] = (txt[: self.snippet_chars] if txt else None)
            section_index[s.section_id] = entry

        store = Store(
            schema_version=self.schema_version,
            document=DocumentHeader(
                doc_id=self.doc_id,
                title=None,
                filename=self.filename,
                filetype="application/json",
                hash=self.doc_hash,
                extracted_with=self.extracted_with,
                extracted_at=self.created_at,
                version=1,
            ),
            sections=sorted(self.sections, key=lambda s: (s.parent_element_id or "", s.sequence)),
            definitions=self.definitions,
            cross_references=self.cross_refs,
            topology={"children_by_parent": children_map, "section_index": section_index},
            provenance={
                "source": self.extracted_with,
                "built_at": self.created_at,
                "elements_count": len(self.elements),
                "notes": "Non-graph store. Full text lives in `sections[*].text`. Index carries snippet/hash/len (or full text if enabled)."
            }
        )
        return store

    # ---------- passes ----------

    def _pass_sections(self) -> None:
        by_parent: Dict[Optional[str], List[Dict[str, Any]]] = defaultdict(list)
        for el in self.elements:
            pid = _get(el, ["metadata", "parent_id"])
            by_parent[pid].append(el)

        for parent_id, group in by_parent.items():
            def keyfn(e):
                pnum = _get(e, ["metadata", "page_number"], 10**7)
                return (pnum, e.get("element_id") or "")
            for seq, el in enumerate(sorted(group, key=keyfn), start=1):
                md = el.get("metadata") or {}
                element_id = el.get("element_id") or sha256_str(json.dumps(el, sort_keys=True)[:160])
                section_id = urn("sec", self.doc_id, element_id)

                # robust text
                best_text, text_source, all_texts = extract_best_text(el)
                text = best_text

                # labels/titles/level (best-effort)
                label, title, level = None, None, None
                t_lower = (el.get("type") or "").lower()
                if "title" in t_lower or "header" in t_lower:
                    label, title, level = parse_label_title_level(text)
                if not label:
                    l2, t2, lvl2 = parse_label_title_level(text)
                    label, title, level = label or l2, title or t2, level or lvl2

                # pages & spans (support dict coordinates with polygon points)
                pnum = md.get("page_number")
                spans: List[Span] = []
                coords = md.get("coordinates")
                polygon = None
                bbox = None
                if isinstance(coords, dict) and isinstance(coords.get("points"), list):
                    polygon = coords["points"]
                    bb = _bbox_from_points(polygon)
                    bbox = bb if bb else None
                elif isinstance(coords, list):
                    # some extractors give bbox directly
                    bbox = coords
                if pnum is not None:
                    spans.append(Span(page=pnum, bbox=bbox, polygon=polygon))

                sec = Section(
                    section_id=section_id,
                    element_id=element_id,
                    parent_element_id=parent_id,
                    sequence=seq,
                    label=label,
                    title=title,
                    level=level,
                    text=text,
                    page_start=pnum,
                    page_end=pnum,
                    spans=spans,
                    element_type=el.get("type"),
                    confidence=md.get("detection_class_prob"),
                    raw_element=el,
                    text_source=text_source,
                    text_candidates=all_texts,
                    text_length=len(text) if text else 0,
                    missing_text=not bool(text),
                )
                self.sections.append(sec)
                self._children_by_parent_element_id[parent_id].append(sec)

    def _pass_crossrefs(self) -> None:
        label_to_section_id = { (s.label or "").lower(): s.section_id for s in self.sections if s.label }
        for s in self.sections:
            for m in iter_cross_refs(s.text or ""):
                label = m.group(0)
                xref_id = urn("xref", self.doc_id, s.section_id, str(m.start()), label)
                self.cross_refs.append(CrossRef(
                    xref_id=xref_id,
                    source_section_id=s.section_id,
                    target_label=label,
                    offset=m.start(),
                    resolved_section_id=label_to_section_id.get(label.lower())
                ))

    def _pass_definitions(self) -> None:
        for s in self.sections:
            if not s.text:
                continue
            for sent in re.split(r'(?<=[\.\;\:])\s+', s.text):
                if len(sent.split()) < 2:
                    continue
                for m in iter_def_terms(sent):
                    term = m.group(1).strip()
                    if len(term.split()) > 6:
                        continue
                    def_id = urn("def", self.doc_id, s.section_id, term)
                    self.definitions.append(Definition(
                        def_id=def_id,
                        term=term,
                        text=sent.strip(),
                        section_id=s.section_id,
                        scope="global"
                    ))

    def _sec_id_or_none(self, parent_element_id: Optional[str]) -> Optional[str]:
        if parent_element_id is None:
            return None
        return urn("sec", self.doc_id, parent_element_id)
