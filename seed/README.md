# Seed data

To produce (see docs/PLAN.md, Workstream B):

| File | Source | Tool |
| --- | --- | --- |
| `elements.csv` | Auditorium measurements and photos | hand-written; master list |
| `auditorium.ifc` | generated from `elements.csv` | IfcOpenShell (box geometry) |
| `schedule.xml` | "Hörsaal Sanierung", ~10 activities, 3 WBS levels, baseline ending Thu 26 Nov | MPXJ (P6 XML) |
| `boq.x83`, `boq.x84` | 12–15 positions in lots Ausbau / TGA / AV | pyGAEB |
| `mapping.csv` | `oz, activity_id, element_id, share` | hand-written |
| `glossary.txt` | German/English site terms for Whisper and aliases | hand-written |
| `load.py` | constraints → zones → elements → BoQ → activities → links → actors → history | neo4j driver |

`elements.csv` columns: element_id, global_id, ifc_class, name_de, name_en, zone, x, y, z, dx, dy, dz,
qty, unit, din276 (3-digit, mark `verify`), marker_id, type (seat_row|wall|stage|lighting|av|floor|default), aliases.

Optional BIM-mode slice: [Schependomlaan archive](https://github.com/openBIMstandards/Archive-DataSetSchependomlaan)
— design IFC in `Design model IFC/`, schedule as MS Project XML in `Planning/XML/`. Academic use only.
