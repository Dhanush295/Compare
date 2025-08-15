from typing import Any, Dict, List, Tuple
from neo4j import GraphDatabase, basic_auth
from app.core.config import settings

Doc = Dict[str, Any]
Store = Dict[str, Any]

class KGClient:
    def __init__(self):
        if not settings.neo4j_enabled:
            raise RuntimeError("Neo4j is not configured. Set NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD.")
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=basic_auth(settings.neo4j_user, settings.neo4j_password)
        )
        self.database = settings.neo4j_database

    def close(self):
        self._driver.close()

    # ---------- public API ----------

    def ensure_constraints(self) -> None:
        cypher = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Section)  REQUIRE s.section_id IS UNIQUE",
        ]
        with self._driver.session(database=self.database) as s:
            for q in cypher:
                s.run(q)

    def import_store(self, store: Store) -> Dict[str, Any]:
        """
        Accepts a normalized store (your StoreBuilder output) and loads:
          - (:Document {doc_id, ...})
          - (:Section {section_id, ...})
          - Relationships: (:Document)-[:HAS_SECTION]->(:Section),
                           (:Section)-[:PARENT_SECTION]->(:Section),
                           (:Section)-[:NEXT_SECTION]->(:Section)
        """
        # ---- map store → flat props ----
        doc_node, sections, parent_rels, next_rels = self._map_store(store)

        # ---- write to Neo4j in one transaction ----
        query = """
        MERGE (d:Document {doc_id: $doc.doc_id})
        SET d += $doc.props
        WITH d, $sections AS sections, $parent_rels AS parent_rels, $next_rels AS next_rels

        // Sections + HAS_SECTION
        UNWIND sections AS s
        MERGE (sec:Section {section_id: s.section_id})
        SET sec += s.props
        MERGE (d)-[:HAS_SECTION]->(sec)

        WITH d, parent_rels, next_rels
        UNWIND parent_rels AS relP
        MATCH (child:Section {section_id: relP.child}), (parent:Section {section_id: relP.parent})
        MERGE (child)-[:PARENT_SECTION]->(parent)

        WITH d, next_rels
        UNWIND next_rels AS relN
        MATCH (a:Section {section_id: relN.a}), (b:Section {section_id: relN.b})
        MERGE (a)-[:NEXT_SECTION]->(b)
        """
        params = {
            "doc": doc_node,
            "sections": sections,
            "parent_rels": parent_rels,
            "next_rels": next_rels,
        }

        with self._driver.session(database=self.database) as s:
            summary = s.run(query, params).consume()

        return {
            "counters": {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "properties_set": summary.counters.properties_set,
                "relationships_created": summary.counters.relationships_created,
                "constraints_added": summary.counters.constraints_added,
            },
            "counts": {
                "sections": len(sections),
                "parent_rels": len(parent_rels),
                "next_rels": len(next_rels),
            }
        }

    # ---------- internal mapping helpers ----------

    def _map_store(self, store: Store):
        doc = store.get("document") or {}
        schema_version = store.get("schema_version")

        doc_node = {
            "doc_id": doc.get("doc_id"),
            "props": {
                # keep everything Aura-friendly (scalars / lists of scalars)
                "title": doc.get("title"),
                "filename": doc.get("filename"),
                "filetype": doc.get("filetype"),
                "hash": doc.get("hash"),
                "extracted_with": doc.get("extracted_with"),
                "extracted_at": doc.get("extracted_at"),
                "version": doc.get("version"),
                "schema_version": schema_version,
                # optional hints
                "source_url": doc.get("source_url"),
                "governing_law": doc.get("governing_law"),
                "jurisdiction": doc.get("jurisdiction"),
            }
        }

        sections_in = store.get("sections") or []
        # Build parent groups for NEXT_SECTION (ordered chains)
        groups = {}  # parent_element_id -> [section dict]
        for s in sections_in:
            pid = s.get("parent_element_id")
            groups.setdefault(pid, []).append(s)

        # order each group by sequence and prepare NEXT pairs
        next_rels = []
        for pid, arr in groups.items():
            arr_sorted = sorted(arr, key=lambda x: (x.get("sequence") or 0, x.get("section_id") or ""))
            for i in range(len(arr_sorted) - 1):
                a = arr_sorted[i].get("section_id")
                b = arr_sorted[i + 1].get("section_id")
                if a and b:
                    next_rels.append({"a": a, "b": b})

        # Parent rels: compute parent section_id from parent_element_id
        doc_id = doc_node["doc_id"]
        def parent_sec_id_from_el(parent_element_id: str) -> str:
            # mirror StoreBuilder._sec_id_or_none / urn("sec", doc_id, parent_element_id)
            from app.utils.ids import urn
            return urn("sec", doc_id, parent_element_id)

        parent_rels = []
        sections = []
        for s in sections_in:
            sec_id = s.get("section_id")
            if not sec_id:
                continue
            pid = s.get("parent_element_id")
            if pid:
                parent_rels.append({"child": sec_id, "parent": parent_sec_id_from_el(pid)})

            # Keep properties Aura can store (no nested maps)
            props = {
                "element_id": s.get("element_id"),
                "sequence": s.get("sequence"),
                "label": s.get("label"),
                "title": s.get("title"),
                "level": s.get("level"),
                "text": s.get("text"),
                "text_length": s.get("text_length"),
                "missing_text": bool(s.get("missing_text")),
                "page_start": s.get("page_start"),
                "page_end": s.get("page_end"),
                "element_type": s.get("element_type"),
                "confidence": s.get("confidence"),
                # diagnostics
                "text_source": s.get("text_source"),
            }
            sections.append({"section_id": sec_id, "props": props})

        return doc_node, sections, parent_rels, next_rels
