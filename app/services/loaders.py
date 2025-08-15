from typing import Any, Dict, List
import json

POSSIBLE_LIST_KEYS = ("elements", "data", "pages", "items")

# NEW: import the adapter
try:
    from app.services.adapters.custom_json import looks_like_custom_blocks, adapt_blocks_to_elements
except Exception:
    looks_like_custom_blocks = lambda _x: False  # noqa
    adapt_blocks_to_elements = lambda _x: []     # noqa

def load_any_shape(json_obj: Any) -> List[Dict[str, Any]]:
    # 1) Handle your custom shape first
    if looks_like_custom_blocks(json_obj):
        return adapt_blocks_to_elements(json_obj)

    # 2) Generic shapes
    if isinstance(json_obj, list):
        return json_obj
    if isinstance(json_obj, dict):
        for k in POSSIBLE_LIST_KEYS:
            v = json_obj.get(k)
            if isinstance(v, list):
                return v
        # best-effort: single dict as one element
        return [json_obj]
    raise ValueError("Unsupported JSON shape; expected list, dict, or custom blocks under return_dict.result.blocks.")

def load_from_path(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    return load_any_shape(obj)
