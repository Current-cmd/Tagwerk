"""Reset to the seeded state: delete stored capture results, stage caches and uploads, and wipe the graph.

    python scripts/reset_demo.py            # keeps cache/ (replay of filmed clips stays possible)
    python scripts/reset_demo.py --all      # also deletes cache/
Restart the API afterwards; it re-syncs seed + history into the graph on startup.
"""
import argparse
import shutil
from pathlib import Path

from tagwerk.config import get_settings

ap = argparse.ArgumentParser()
ap.add_argument("--all", action="store_true", help="also delete cached stage outputs")
a = ap.parse_args()
s = get_settings()
for sub in ("results", "captures", "work"):
    shutil.rmtree(Path(s.data_dir) / sub, ignore_errors=True)
if a.all:
    shutil.rmtree(s.cache_dir, ignore_errors=True)
if s.neo4j_uri:
    from neo4j import GraphDatabase

    with GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password)) as d:
        d.execute_query("MATCH (n) DETACH DELETE n")
        for stmt in Path("seed/constraints.cypher").read_text().split(";"):
            lines = [ln for ln in stmt.splitlines() if ln.strip() and not ln.strip().startswith("//")]
            if lines:
                d.execute_query("\n".join(lines))
print("reset done; restart the API")
