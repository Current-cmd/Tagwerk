// Run once against Neo4j (Browser or cypher-shell). Unique ids make every MERGE idempotent.
CREATE CONSTRAINT element_id IF NOT EXISTS FOR (n:Element) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT boq_id IF NOT EXISTS FOR (n:BoQPosition) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT activity_id IF NOT EXISTS FOR (n:Activity) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT capture_id IF NOT EXISTS FOR (n:Capture) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT marker_id IF NOT EXISTS FOR (n:Marker) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT zone_id IF NOT EXISTS FOR (n:Zone) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT observation_id IF NOT EXISTS FOR (n:Observation) REQUIRE n.id IS UNIQUE;
CREATE INDEX element_aliases IF NOT EXISTS FOR (n:Element) ON (n.aliases);
CREATE INDEX activity_name IF NOT EXISTS FOR (n:Activity) ON (n.name);
CREATE CONSTRAINT tw_id IF NOT EXISTS FOR (n:Tw) REQUIRE n.id IS UNIQUE;
