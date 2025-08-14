from typing import Any, Dict, List
import json

POSSIBLE_LIST_KEYS = ("elements", "data", "pages", "items")

def load_any_shape(json_obj: Any) -> List[Dict[str, Any]]:
    if isinstance(json_obj, list):
        return json_obj
    if isinstance(json_obj, dict):
        for k in POSSIBLE_LIST_KEYS:
            v = json_obj.get(k)
            if isinstance(v, list):
                return v
    if isinstance(json_obj, dict):
        return [json_obj]
    raise ValueError("Unsupported JSON shape; expected list or dict with a list under 'elements'/'data'/'pages'/'items'.")

def load_from_path(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    return load_any_shape(obj)
