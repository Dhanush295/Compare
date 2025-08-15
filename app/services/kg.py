from typing import Any, Dict, List
from neo4j import GraphDatabase, basic_auth
from app.core.config import settings

class KGClient:
    def __init__(self):
        if not settings.neo4j_uri:
            raise RuntimeError("Neo4j is not configured.")
        self.database = settings.neo4j_database
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=basic_auth(settings.neo4j_user, settings.neo4j_password),
            connection_timeout=30,
            max_connection_lifetime=600,
            connection_acquisition_timeout=60,
            max_transaction_retry_time=60,
        )

    def close(self):
        self._driver.close()

    def ensure_constraints(self):
        stmts = [
            "CREATE CONSTRAINT doc_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE",
            "CREATE CONSTRAINT sec_id_unique IF NOT EXISTS FOR (s:Section) REQUIRE s.section_id IS UNIQUE",
            "CREATE CONSTRAINT def_id_unique IF NOT EXISTS FOR (d:Definition) REQUIRE d.def_id IS UNIQUE",
        ]
        with self._driver.session(database=self.database) as s:
            for q in stmts:
                s.run(q).consume()

    # NEW: full-text index for search
    def ensure_fulltext_index(self):
        q = """
        CREATE FULLTEXT INDEX sectionTextIdx IF NOT EXISTS
        FOR (s:Section) ON EACH [s.text, s.title, s.label]
        """
        with self._driver.session(database=self.database) as s:
            s.run(q).consume()

    def import_store(self, store: Dict[str, Any]) -> Dict[str, Any]:
        doc = store.get("document") or {}
        sections = store.get("sections") or []
        definitions = store.get("definitions") or []
        xrefs = store.get("cross_references") or []
        topo = (store.get("topology") or {})
        children_by_parent = topo.get("children_by_parent") or {}
        # Build NEXT relationships by sequence per parent
        next_rels: List[Dict[str, str]] = []
        by_parent_to_secs = {k: v for k, v in children_by_parent.items()}
        for _parent, sec_ids in by_parent_to_secs.items():
            for a, b in zip(sec_ids, sec_ids[1:]):
                next_rels.append({"a": a, "b": b})

        params = {
            "doc": {
                "doc_id": doc.get("doc_id"),
                "props": {k: v for k, v in doc.items() if k != "doc_id"},
            },
            "sections": [
                {"section_id": s["section_id"], "props": {
                    "element_id": s.get("element_id"),
                    "title": s.get("title"),
                    "label": s.get("label"),
                    "level": s.get("level"),
                    "text": s.get("text"),
                    "page_start": s.get("page_start"),
                    "page_end": s.get("page_end"),
                    "element_type": s.get("element_type"),
                    "text_length": s.get("text_length"),
                    "missing_text": s.get("missing_text"),
                }} for s in sections
            ],
            "parent_rels": [
                {"child": cid, "parent": pid}
                for pid, child_list in children_by_parent.items()
                if isinstance(child_list, list) and pid is not None
                for cid in child_list
            ],
            "next_rels": next_rels,
            "definitions": [
                {"def_id": d["def_id"], "term": d.get("term"), "text": d.get("text"), "section_id": d.get("section_id")}
                for d in definitions
            ],
            "xrefs": [
                {"source": x.get("source_section_id"), "target": x.get("resolved_section_id")}
                for x in xrefs if x.get("resolved_section_id")
            ],
        }

        query = """
        MERGE (d:Document {doc_id: $doc.doc_id})
        SET d += $doc.props
        WITH d, $sections AS sections, $parent_rels AS parent_rels, $next_rels AS next_rels,
             $definitions AS definitions, $xrefs AS xrefs

        // Sections + HAS_SECTION (batched)
        CALL {
          WITH d, sections
          UNWIND sections AS s
          MERGE (sec:Section {section_id: s.section_id})
          SET sec += s.props
          MERGE (d)-[:HAS_SECTION]->(sec)
          RETURN count(*) AS _
        }

        WITH d, parent_rels, next_rels, definitions, xrefs

        // Parent relationships
        UNWIND parent_rels AS relP
        MATCH (child:Section {section_id: relP.child}), (parent:Section {section_id: relP.parent})
        MERGE (child)-[:PARENT_SECTION]->(parent)

        WITH d, next_rels, definitions, xrefs

        // NEXT relationships
        UNWIND next_rels AS relN
        MATCH (a:Section {section_id: relN.a}), (b:Section {section_id: relN.b})
        MERGE (a)-[:NEXT_SECTION]->(b)

        WITH d, definitions, xrefs

        // Definitions (nodes) + DEFINES
        UNWIND definitions AS def
        MERGE (df:Definition {def_id: def.def_id})
        SET df.term = def.term, df.text = def.text
        WITH d, xrefs, def
        MATCH (sec:Section {section_id: def.section_id})
        MERGE (sec)-[:DEFINES]->(:Definition {def_id: def.def_id})

        WITH d, xrefs

        // Cross-refs (resolved only)
        UNWIND xrefs AS xr
        MATCH (s:Section {section_id: xr.source}), (t:Section {section_id: xr.target})
        MERGE (s)-[:REFERS_TO]->(t)
        RETURN d.doc_id AS doc_id
        """

        with self._driver.session(database=self.database) as s:
            summary = s.run(query, params).consume()
        return {"status": "ok", "doc_id": params["doc"]["doc_id"]}
