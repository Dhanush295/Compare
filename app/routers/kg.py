from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from app.services.kg import KGClient
from app.core.config import settings

router = APIRouter(
    prefix="/api/kg",
    tags=["Knowledge Graph"],
)

@router.post("/import", summary="Import a structured store into Neo4j")
def import_store(store: Dict[str, Any]):
    """
    Accepts the normalized store from your builder (same shape returned by /extract/structure endpoints).
    """
    if not settings.neo4j_enabled:
        raise HTTPException(status_code=400, detail="Neo4j is not configured (NEO4J_URI missing).")
    try:
        kg = KGClient()
        kg.ensure_constraints()
        result = kg.import_store(store)
        kg.close()
        return {"status": "ok", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"KG import error: {e}")


@router.post("/ensure-constraints", summary="Create Neo4j constraints (idempotent)")
def ensure_constraints():
    if not settings.neo4j_enabled:
        raise HTTPException(status_code=400, detail="Neo4j is not configured (NEO4J_URI missing).")
    try:
        kg = KGClient()
        kg.ensure_constraints()
        kg.close()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Constraint setup error: {e}")
