from typing import Any, Dict
from collections import defaultdict

BASIC_TYPES = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    type(None): "null",
}

def _infer_type(value: Any):
    if isinstance(value, list):
        if not value:
            return {"type": "array", "items": {}}
        first = next((x for x in value if x is not None), None)
        if first is None:
            return {"type": "array", "items": {}}
        return {"type": "array", "items": _infer_type(first)}
    if isinstance(value, dict):
        return {"type": "object"}
    return {"type": BASIC_TYPES.get(type(value), "string")}

def build_dynamic_schema(store: Dict[str, Any]) -> Dict[str, Any]:
    root_required = ["schema_version", "document"]

    doc_props = {}
    doc_required = ["doc_id", "filename", "hash", "extracted_with", "extracted_at", "version"]
    for k, v in (store.get("document") or {}).items():
        doc_props[k] = _infer_type(v)

    section_samples = store.get("sections") or []
    sec_props: Dict[str, Any] = defaultdict(dict)
    sec_required = {"section_id", "text"}
    for s in section_samples:
        for k, v in s.items():
            sec_props[k] = _infer_type(v)

    def_samples = store.get("definitions") or []
    def_props: Dict[str, Any] = defaultdict(dict)
    def_required = {"def_id", "term", "text", "section_id"}
    for d in def_samples:
        for k, v in d.items():
            def_props[k] = _infer_type(v)

    xref_samples = store.get("cross_references") or []
    xref_props: Dict[str, Any] = defaultdict(dict)
    xref_required = {"xref_id", "source_section_id", "target_label", "offset"}
    for x in xref_samples:
        for k, v in x.items():
            xref_props[k] = _infer_type(v)

    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "M&A Document Store (Dynamic)",
        "type": "object",
        "required": root_required,
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "string"},
            "document": {
                "type": "object",
                "required": doc_required,
                "properties": doc_props,
                "additionalProperties": True
            },
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": sorted(sec_required),
                    "properties": sec_props,
                    "additionalProperties": True
                }
            },
            "definitions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": sorted(def_required),
                    "properties": def_props,
                    "additionalProperties": True
                }
            },
            "cross_references": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": sorted(xref_required),
                    "properties": xref_props,
                    "additionalProperties": True
                }
            },
            "topology": {"type": "object"},
            "provenance": {"type": "object"}
        }
    }
    return schema
