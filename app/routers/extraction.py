from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import Any, Dict
import json

from app.services import pdf_processor
from app.services.loaders import load_any_shape
from app.services.builder import StoreBuilder
from app.schemas.json_schema import build_dynamic_schema
from app.core.config import settings
# NEW:
from app.services.kg import KGClient

router = APIRouter(
    prefix="/api/extraction",
    tags=["PDF Extraction", "structure"],
)

@router.post("/pymupdf", summary="Extract text with PyMuPDF")
async def extract_pymupdf_endpoint(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(400, "File must be a PDF.")
    try:
        contents = await file.read()
        data = await pdf_processor.process_with_pymupdf(contents)
        return {"filename": file.filename, "library": "PyMuPDF", "data": data}
    except Exception as e:
        raise HTTPException(500, f"PyMuPDF processing error: {e}")

@router.post("/unstructured", summary="Extract elements with Unstructured")
async def extract_unstructured_endpoint(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(400, "File must be a PDF.")
    try:
        contents = await file.read()
        data = await pdf_processor.process_with_unstructured(contents, file.filename)
        return {"filename": file.filename, "library": "unstructured", "data": data}
    except Exception as e:
        raise HTTPException(500, f"Unstructured processing error: {e}")
    
_SAMPLE_INPUT = [
    {"type":"Title","text":"ARTICLE I Merger","metadata":{"page_number":1}},
    {"type":"NarrativeText","text":"At the Effective Time, the Merger...","metadata":{"page_number":2}}
]

_SAMPLE_INPUT = [
    {"type": "Title", "text": "ARTICLE I Merger", "metadata": {"page_number": 1}},
    {"type": "NarrativeText", "text": "At the Effective Time, the Merger...", "metadata": {"page_number": 2}},
]




@router.post("/structure", summary="Normalize an uploaded JSON file to the M&A store format")
async def structure_file(
    file: UploadFile = File(...),
    include_schema: bool = True,
    index_text: bool = Query(False, description="Include full text in topology.section_index"),
    snippet_chars: int = Query(280, ge=0, le=10000),
    auto_load_to_kg: bool = Query(False, description="If true, load the structured store into Neo4j Aura"),
):
    try:
        contents = await file.read()
        raw = json.loads(contents.decode("utf-8", errors="ignore"))
        elements = load_any_shape(raw)
        builder = StoreBuilder(
            elements,
            filename=file.filename,
            schema_version=settings.default_schema_version,
            extracted_with="unstructured.io",
            include_text_in_index=index_text,
            snippet_chars=snippet_chars,
        )
        store = builder.build().model_dump(exclude_none=False)
        resp: Dict[str, Any] = {"store": store}
        if include_schema:
            resp["schema"] = build_dynamic_schema(store)

        if auto_load_to_kg:
            if not settings.neo4j_enabled:
                raise HTTPException(400, "auto_load_to_kg=True but Neo4j is not configured.")
            kg = KGClient()
            kg.ensure_constraints()
            resp["kg_result"] = kg.import_store(store)
            kg.close()

        return resp
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/rawjson", summary="Normalize an inline JSON payload to the M&A store format")
async def structure_rawjson(
    raw: Dict[str, Any],
    include_schema: bool = True,
    index_text: bool = Query(False, description="Include full text in topology.section_index"),
    snippet_chars: int = Query(280, ge=0, le=10000),
    auto_load_to_kg: bool = Query(False, description="If true, load the structured store into Neo4j Aura"),
):
    try:
        elements = load_any_shape(raw)
        builder = StoreBuilder(
            elements,
            filename="payload.json",
            schema_version=settings.default_schema_version,
            extracted_with="unknown",
            include_text_in_index=index_text,
            snippet_chars=snippet_chars,
        )
        store = builder.build().model_dump(exclude_none=False)
        resp: Dict[str, Any] = {"store": store}
        if include_schema:
            resp["schema"] = build_dynamic_schema(store)

        if auto_load_to_kg:
            if not settings.neo4j_enabled:
                raise HTTPException(400, "auto_load_to_kg=True but Neo4j is not configured.")
            kg = KGClient()
            kg.ensure_constraints()
            resp["kg_result"] = kg.import_store(store)
            kg.close()

        return resp
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))