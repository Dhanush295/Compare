from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

class Span(BaseModel):
    page: Optional[int] = None
    bbox: Optional[List[float]] = None           # [x1,y1,x2,y2]
    polygon: Optional[List[List[float]]] = None  # original polygon if present

class Section(BaseModel):
    model_config = ConfigDict(extra="allow")

    section_id: str
    element_id: str
    parent_element_id: Optional[str] = None
    sequence: int = 0
    label: Optional[str] = None
    title: Optional[str] = None
    level: Optional[int] = None

    text: str  # canonical text

    page_start: Optional[int] = None
    page_end: Optional[int] = None
    spans: List[Span] = Field(default_factory=list)
    element_type: Optional[str] = None
    confidence: Optional[float] = None
    raw_element: Dict[str, Any] = Field(default_factory=dict)

    # diagnostics
    text_source: Optional[str] = None
    text_candidates: List[str] = Field(default_factory=list)
    text_length: Optional[int] = None
    missing_text: Optional[bool] = None

class Definition(BaseModel):
    model_config = ConfigDict(extra="allow")
    def_id: str
    term: str
    text: str
    section_id: str
    scope: str = "global"

class CrossRef(BaseModel):
    model_config = ConfigDict(extra="allow")
    xref_id: str
    source_section_id: str
    target_label: str
    offset: int
    resolved_section_id: Optional[str] = None

class DocumentHeader(BaseModel):
    model_config = ConfigDict(extra="allow")
    doc_id: str
    title: Optional[str] = None
    filename: str
    filetype: str = "application/json"
    hash: str
    extracted_with: str = "unknown"
    extracted_at: str
    version: int = 1
    governing_law: Optional[str] = None
    jurisdiction: Optional[str] = None
    source_url: Optional[str] = None

class Store(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: str
    document: DocumentHeader
    sections: List[Section] = Field(default_factory=list)
    definitions: List[Definition] = Field(default_factory=list)
    cross_references: List[CrossRef] = Field(default_factory=list)
    topology: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)

# >>> This is the response model used by the router
class StoreBundle(BaseModel):
    store: Dict[str, Any]
    schema: Optional[Dict[str, Any]] = None
