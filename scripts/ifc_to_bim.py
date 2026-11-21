"""Tessellate an IFC model into a compact mesh pair for the /app BIM viewer (three.js, no IFC parsing in the browser).

    python scripts/ifc_to_bim.py "<path>/IFC Schependomlaan.ifc" seed/projects/schependomlaan

Writes <out>/bim.bin (float32 positions, then uint32 triangle indices, local per element) and <out>/bim.json:
{"source", "elements": [{"gid", "cls", "name", "v": [first_vertex, n_vertices], "i": [first_index, n_indices]}],
 "bbox": [[minx, miny, minz], [maxx, maxy, maxz]], "vertices", "triangles"}. Coordinates are Y-up metres (IFC Z-up
is turned), so three.js shows the building upright. GlobalIds match elements.csv (`global_id`) of the import.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
from array import array
from pathlib import Path

SKIP = ("IfcOpeningElement", "IfcSpace", "IfcAnnotation", "IfcSite", "IfcVirtualElement", "IfcGrid")


def convert(ifc_path: Path, out: Path) -> dict:
    import ifcopenshell
    import ifcopenshell.geom

    model = ifcopenshell.open(str(ifc_path))
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    products = [p for p in model.by_type("IfcProduct") if p.Representation and p.is_a() not in SKIP
                and not any(p.is_a(s) for s in SKIP)]
    it = ifcopenshell.geom.iterator(settings, model, multiprocessing.cpu_count(), include=products)
    pos, idx, elements = array("f"), array("I"), []
    lo, hi = [float("inf")] * 3, [float("-inf")] * 3
    if it.initialize():
        while True:
            shape = it.get()
            v, f = shape.geometry.verts, shape.geometry.faces
            if v and f:
                first_v, first_i = len(pos) // 3, len(idx)
                for k in range(0, len(v), 3):
                    x, y, z = v[k], v[k + 2], -v[k + 1]  # IFC Z-up -> Y-up
                    pos.extend((x, y, z))
                    for a, c in enumerate((x, y, z)):
                        lo[a], hi[a] = min(lo[a], c), max(hi[a], c)
                idx.extend(f)
                el = model.by_guid(shape.guid)
                elements.append({"gid": shape.guid, "cls": el.is_a(), "name": el.Name or "",
                                 "v": [first_v, len(v) // 3], "i": [first_i, len(f)]})
            if not it.next():
                break
    out.mkdir(parents=True, exist_ok=True)
    with (out / "bim.bin").open("wb") as fh:
        pos.tofile(fh)
        idx.tofile(fh)
    meta = {"source": ifc_path.name, "elements": elements, "bbox": [lo, hi], "vertices": len(pos) // 3,
            "triangles": len(idx) // 3}
    (out / "bim.json").write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("ifc", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    m = convert(a.ifc, a.out)
    print(f"{len(m['elements'])} elements, {m['vertices']} vertices, {m['triangles']} triangles -> {a.out}")
