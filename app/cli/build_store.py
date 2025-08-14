import argparse
import json
import os
from app.services.loaders import load_from_path
from app.services.builder import StoreBuilder
from app.schemas.json_schema import build_dynamic_schema

def main():
    p = argparse.ArgumentParser(description="Normalize raw JSON into M&A store (non-graph).")
    p.add_argument("--in", dest="in_path", required=True, help="Path to raw JSON")
    p.add_argument("--out", dest="out_path", default="mna_store.json", help="Output store JSON")
    p.add_argument("--schema", dest="schema_path", default="mna_store.schema.json", help="Output dynamic JSON Schema")
    p.add_argument("--extracted-with", dest="extracted_with", default="unknown")
    p.add_argument("--schema-version", dest="schema_version", default="1.0.0")
    p.add_argument("--index-text", dest="index_text", action="store_true", help="Include full text in topology.section_index")
    p.add_argument("--snippet-chars", dest="snippet_chars", type=int, default=280)
    args = p.parse_args()

    elements = load_from_path(args.in_path)
    filename = os.path.basename(args.in_path)

    builder = StoreBuilder(
        elements,
        filename=filename,
        schema_version=args.schema_version,
        extracted_with=args.extracted_with,
        include_text_in_index=args.index_text,
        snippet_chars=args.snippet_chars,
    )
    store = builder.build().model_dump(exclude_none=False)

    with open(args.out_path, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)

    schema = build_dynamic_schema(store)
    with open(args.schema_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)

    print(f"Store → {args.out_path}")
    print(f"Dynamic schema → {args.schema_path}")

if __name__ == "__main__":
    main()
