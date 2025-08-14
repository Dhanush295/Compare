from fastapi import APIRouter, UploadFile, File, HTTPException, Query  
from app.services import pdf_processor

from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional
import json
from app.services.loaders import load_any_shape
from app.services.builder import StoreBuilder
from app.schemas.json_schema import build_dynamic_schema
from app.core.config import settings
from app.models.store import StoreBundle


router = APIRouter(
    prefix="/extract",
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

@router.post(
    "/structure",
    response_model=StoreBundle,
    summary="Normalize an uploaded JSON file to the M&A store format",
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string", "format": "binary"},
                            "include_schema": {"type": "boolean", "default": True},
                            "index_text": {"type": "boolean", "default": False},
                            "snippet_chars": {"type": "integer", "default": 280},
                        },
                        "required": ["file"],
                    }
                }
            }
        }
    },
)
async def structure_file(
    file: UploadFile = File(...),
    include_schema: bool = True,
    index_text: bool = Query(False, description="Include full text in topology.section_index"),
    snippet_chars: int = Query(
        280, ge=0, le=10000, description="Chars for topology.section_index.text_snippet when index_text=false"
    ),
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
        return resp
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post(
    "/structure/rawjson",
    response_model=StoreBundle,
    summary="Normalize an inline JSON payload to the M&A store format",
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": {
                        "minimal": {"summary": "Minimal Unstructured-like array", "value": _SAMPLE_INPUT},
                        "with-elements-key": {"summary": "Wrapped in {'elements': [...]}","value": {"elements": _SAMPLE_INPUT}},
                    }
                }
            }
        }
    },
)
async def structure_rawjson(
    raw: Dict[str, Any],
    include_schema: bool = True,
    index_text: bool = Query(False, description="Include full text in topology.section_index"),
    snippet_chars: int = Query(
        280, ge=0, le=10000, description="Chars for topology.section_index.text_snippet when index_text=false"
    ),
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
        return resp
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))