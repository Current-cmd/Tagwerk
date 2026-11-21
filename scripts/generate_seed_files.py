"""Generate the derived seed files from the CSV master data in seed/.

    python scripts/generate_seed_files.py [--out seed] [--seed seed]

Writes into --out:
  auditorium.ifc  IFC4: project > site > building > storey 'EG' > one IfcSpace per zone, every element as a
                  box (extruded rectangle dx*dy, height dz) at x,y,z with its GlobalId, contained in its
                  zone's IfcSpace, plus a Pset_Tagwerk property set
  schedule.xml    P6 XML, baseline only (p6_xml(progress=False))
  boq.x83         GAEB DA XML 3.3 tender (no prices)
  boq.x84         GAEB DA XML 3.3 priced bid

Deterministic: same CSVs -> byte-identical files (all GlobalIds are derived from names, the header timestamp
is fixed).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from tagwerk.pipeline.export import gaeb_xml, p6_xml
from tagwerk.project import SEED_DIR, Project, ifc_guid

FALLBACK_CLASS = "IfcBuildingElementProxy"
IFC_TIMESTAMP = "2026-11-01T00:00:00"


def _valid_ifc4_product(ifc_class: str) -> bool:
    import ifcopenshell.ifcopenshell_wrapper as w

    try:
        decl = w.schema_by_name("IFC4").declaration_by_name(ifc_class)
    except Exception:  # noqa: BLE001 - unknown name
        return False
    if decl.is_abstract():
        return False
    parent = decl
    while parent is not None:
        if parent.name() == "IfcProduct":
            return True
        parent = parent.supertype()
    return False


def _box(ifc, body_ctx, dx: float, dy: float, dz: float):
    """Representation of a box with its corner at the local origin (profile centred at dx/2, dy/2)."""
    profile = ifc.create_entity(
        "IfcRectangleProfileDef", ProfileType="AREA", XDim=dx, YDim=dy,
        Position=ifc.create_entity("IfcAxis2Placement2D", Location=ifc.create_entity("IfcCartesianPoint",
                                                                                     Coordinates=(dx / 2, dy / 2))))
    solid = ifc.create_entity(
        "IfcExtrudedAreaSolid", SweptArea=profile,
        Position=ifc.create_entity("IfcAxis2Placement3D", Location=ifc.create_entity("IfcCartesianPoint",
                                                                                     Coordinates=(0.0, 0.0, 0.0))),
        ExtrudedDirection=ifc.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)), Depth=dz)
    rep = ifc.create_entity("IfcShapeRepresentation", ContextOfItems=body_ctx, RepresentationIdentifier="Body",
                            RepresentationType="SweptSolid", Items=[solid])
    return ifc.create_entity("IfcProductDefinitionShape", Representations=[rep])


def build_ifc(project: Project, path: Path) -> dict:
    import ifcopenshell
    import ifcopenshell.api

    api = ifcopenshell.api
    ifc = ifcopenshell.file(schema="IFC4")
    ifc_project = api.run("root.create_entity", ifc, ifc_class="IfcProject", name="Hörsaal Sanierung")
    api.run("unit.assign_unit", ifc)
    model = api.run("context.add_context", ifc, context_type="Model")
    body = api.run("context.add_context", ifc, context_type="Model", context_identifier="Body",
                   target_view="MODEL_VIEW", parent=model)
    site = api.run("root.create_entity", ifc, ifc_class="IfcSite", name="Hörsaal Sanierung")
    building = api.run("root.create_entity", ifc, ifc_class="IfcBuilding", name="Auditorium")
    storey = api.run("root.create_entity", ifc, ifc_class="IfcBuildingStorey", name="EG")
    api.run("aggregate.assign_object", ifc, products=[site], relating_object=ifc_project)
    api.run("aggregate.assign_object", ifc, products=[building], relating_object=site)
    api.run("aggregate.assign_object", ifc, products=[storey], relating_object=building)

    spaces = {}
    for zid, z in project.zones.items():
        space = api.run("root.create_entity", ifc, ifc_class="IfcSpace", name=zid)
        space.LongName = z["name_de"]
        space.Description = z["name_en"]
        api.run("aggregate.assign_object", ifc, products=[space], relating_object=storey)
        spaces[zid] = space

    element_ids: set[int] = set()
    fallbacks: list[str] = []
    in_space = 0
    for eid, el in project.elements.items():
        cls = el["ifc_class"] if _valid_ifc4_product(el["ifc_class"]) else FALLBACK_CLASS
        if cls != el["ifc_class"]:
            fallbacks.append(f"{eid}: {el['ifc_class']} -> {cls}")
        prod = api.run("root.create_entity", ifc, ifc_class=cls, name=el["name_de"])
        prod.GlobalId = el["global_id"]
        prod.Description = el["name_en"]
        x, y, z, dx, dy, dz = el["geom"]
        prod.ObjectPlacement = ifc.create_entity(
            "IfcLocalPlacement", PlacementRelTo=None,
            RelativePlacement=ifc.create_entity("IfcAxis2Placement3D",
                                                Location=ifc.create_entity("IfcCartesianPoint", Coordinates=(x, y, z))))
        prod.Representation = _box(ifc, body, dx, dy, dz)
        space = spaces[el["zone"]]
        try:
            api.run("spatial.assign_container", ifc, products=[prod], relating_structure=space)
            in_space += 1
        except Exception:  # noqa: BLE001 - class not allowed in a space: storey + reference to the space
            api.run("spatial.assign_container", ifc, products=[prod], relating_structure=storey)
            api.run("spatial.reference_structure", ifc, products=[prod], relating_structure=space)
        pset = api.run("pset.add_pset", ifc, product=prod, name="Pset_Tagwerk")
        props = {"ElementId": eid, "DIN276": el["din276"], "Quantity": float(el["qty"]), "Unit": el["unit"],
                 "ElementType": el["type"], "Aliases": "|".join(el["aliases"])}
        if el["marker_id"] is not None:
            props["MarkerId"] = int(el["marker_id"])
        api.run("pset.edit_pset", ifc, pset=pset, properties=props)
        element_ids.add(prod.id())

    # deterministic ids for everything else that has a GlobalId (creation order is deterministic)
    for n, ent in enumerate(ifc.by_type("IfcRoot")):
        if ent.id() not in element_ids and not ent.is_a("IfcProject"):
            ent.GlobalId = ifc_guid(f"ifc:{n}:{ent.is_a()}:{getattr(ent, 'Name', None)}")
    ifc_project.GlobalId = ifc_guid("ifc:project")
    # relationship members come out of Python sets (memory-address order): sort them by entity id
    for rel in ifc.by_type("IfcRelationship"):
        for i in range(len(rel)):
            val = rel[i]
            entities = isinstance(val, tuple) and all(isinstance(v, ifcopenshell.entity_instance) for v in val)
            if entities and len(val) > 1:
                rel[i] = tuple(sorted(val, key=lambda e: e.id()))
    header = ifc.header
    header.file_name.time_stamp = IFC_TIMESTAMP
    header.file_name.name = path.name
    path.parent.mkdir(parents=True, exist_ok=True)
    ifc.write(str(path))
    return {"elements": len(project.elements), "spaces": len(spaces), "in_space": in_space, "fallbacks": fallbacks}


def generate(out_dir: Path, seed_dir: Path = SEED_DIR) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    project = Project.from_seed(seed_dir)
    files = {
        "ifc": out_dir / "auditorium.ifc",
        "p6": out_dir / "schedule.xml",
        "x83": out_dir / "boq.x83",
        "x84": out_dir / "boq.x84",
    }
    try:
        build_ifc(project, files["ifc"])
    except ImportError:
        files.pop("ifc")  # ifcopenshell missing: the other three files are still produced
    files["p6"].write_text(p6_xml(project, progress=False), encoding="utf-8")
    files["x83"].write_text(gaeb_xml(project, 83), encoding="utf-8")
    files["x84"].write_text(gaeb_xml(project, 84), encoding="utf-8")
    return files


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=SEED_DIR, help="output directory (default: seed/)")
    ap.add_argument("--seed", type=Path, default=SEED_DIR, help="directory with the CSV master data")
    args = ap.parse_args()
    for name, path in generate(args.out, args.seed).items():
        print(f"{name}: {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
