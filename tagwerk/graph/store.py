"""Graph writes. Neo4j when NEO4J_URI is set and reachable, otherwise an in-memory store
(so tests and laptop demos run without Docker). All writes are idempotent MERGEs."""
import logging
import re

from tagwerk.config import get_settings

log = logging.getLogger(__name__)
_LABEL = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _safe(label: str) -> str:
    if not _LABEL.match(label):
        raise ValueError(f"bad label/type: {label!r}")
    return label


class MemoryStore:
    def __init__(self) -> None:
        self.nodes: dict[tuple[str, str], dict] = {}
        self.edges: dict[tuple[str, str, str], dict] = {}

    def merge_node(self, label: str, node_id: str, props: dict | None = None) -> None:
        self.nodes.setdefault((_safe(label), node_id), {}).update(props or {})

    def merge_edge(self, src: str, rel: str, dst: str, props: dict | None = None) -> None:
        self.edges.setdefault((src, _safe(rel), dst), {}).update(props or {})

    def snapshot(self) -> dict:
        return {
            "nodes": [{"label": lb, "id": i, "props": p} for (lb, i), p in self.nodes.items()],
            "edges": [{"src": s, "rel": r, "dst": d, "props": p} for (s, r, d), p in self.edges.items()],
        }

    def close(self) -> None:
        pass


class Neo4jStore:
    def __init__(self, uri: str, user: str, password: str) -> None:
        from neo4j import GraphDatabase

        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._driver.verify_connectivity()
        # every node also carries :Tw so edge MATCHes hit one unique index instead of scanning all labels
        self._driver.execute_query("CREATE CONSTRAINT tw_id IF NOT EXISTS FOR (n:Tw) REQUIRE n.id IS UNIQUE")

    def merge_node(self, label: str, node_id: str, props: dict | None = None) -> None:
        q = f"MERGE (n:Tw {{id: $id}}) SET n:{_safe(label)} SET n += $props"
        self._driver.execute_query(q, id=node_id, props=props or {})

    def merge_edge(self, src: str, rel: str, dst: str, props: dict | None = None) -> None:
        q = f"MATCH (a:Tw {{id: $src}}), (b:Tw {{id: $dst}}) MERGE (a)-[r:{_safe(rel)}]->(b) SET r += $props"
        self._driver.execute_query(q, src=src, dst=dst, props=props or {})

    def snapshot(self) -> dict:
        nodes, _, _ = self._driver.execute_query(
            "MATCH (n:Tw) RETURN [l IN labels(n) WHERE l <> 'Tw'][0] AS label, n.id AS id, properties(n) AS props LIMIT 2000")
        edges, _, _ = self._driver.execute_query(
            "MATCH (a)-[r]->(b) RETURN a.id AS src, type(r) AS rel, b.id AS dst, properties(r) AS props LIMIT 5000")
        return {"nodes": [dict(r) for r in nodes], "edges": [dict(r) for r in edges]}

    def close(self) -> None:
        self._driver.close()


_store = None


def get_store():
    global _store
    if _store is None:
        s = get_settings()
        if s.neo4j_uri:
            try:
                _store = Neo4jStore(s.neo4j_uri, s.neo4j_user, s.neo4j_password)
                log.info("graph: Neo4j at %s", s.neo4j_uri)
            except Exception as exc:  # fall back so the demo never dies on a missing DB
                log.warning("graph: Neo4j unavailable (%s), using in-memory store", exc)
        if _store is None:
            _store = MemoryStore()
    return _store
