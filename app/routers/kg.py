from fastapi import APIRouter, HTTPException
from app.services.kg import KGClient

router = APIRouter(prefix="/api/kg", tags=["Knowledge Graph"])

@router.post("/ensure-constraints", summary="Create Neo4j constraints (idempotent)")
def ensure_constraints():
    try:
        KGClient().ensure_constraints()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/setup-search", summary="Create a full-text index for Section text/title/label (idempotent)")
def setup_search():
    try:
        KGClient().ensure_fulltext_index()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/import", summary="Import a structured store into Neo4j")
def import_store(store: dict):
    try:
        return KGClient().import_store(store)
    except Exception as e:
        raise HTTPException(400, str(e))
