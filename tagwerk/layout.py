"""Room layout from a phone scan (AR / photogrammetry apps: Polycam, Scaniverse, 3D Scanner App ...).

import_layout(src, out_dir) reads GLB/glTF/OBJ/PLY (mesh or point cloud), keeps the app's metric, y-up frame (glTF
convention), puts the floor (3rd percentile of the vertex heights) at y = 0, centres x/z on the bounding box and writes
out_dir/layout.glb + layout.json (faces, vertices, size, units "m"). The browser loads the GLB directly.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

FORMATS = (".glb", ".gltf", ".obj", ".ply")


def import_layout(src: Path, out_dir: Path, name: str | None = None) -> dict:
    import trimesh

    src = Path(src)
    try:
        scene = trimesh.load(src, force="scene")
        geoms = [g for g in scene.dump() if hasattr(g, "vertices") and len(g.vertices)]  # transforms applied
    except Exception as exc:  # noqa: BLE001 - any parser error is a bad file for the user
        raise ValueError(f"Datei nicht lesbar ({type(exc).__name__})") from exc
    if not geoms:
        raise ValueError("Keine Geometrie in der Datei")
    allv = np.vstack([np.asarray(g.vertices, float) for g in geoms])
    floor = float(np.percentile(allv[:, 1], 3))
    lo, hi = allv.min(axis=0), allv.max(axis=0)
    shift = -np.array([(lo[0] + hi[0]) / 2, floor, (lo[2] + hi[2]) / 2])
    out = trimesh.Scene()
    faces = 0
    for g in geoms:
        g = g.copy()
        g.apply_translation(shift)
        faces += len(getattr(g, "faces", []))
        out.add_geometry(g)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out.export(out_dir / "layout.glb")
    v = allv + shift
    meta = {"source": name or src.name, "faces": int(faces), "vertices": int(len(v)), "units": "m",
            "size": [round(float(x), 3) for x in v.max(axis=0) - v.min(axis=0)],
            "bounds": [[round(float(x), 3) for x in v.min(axis=0)], [round(float(x), 3) for x in v.max(axis=0)]]}
    (out_dir / "layout.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return meta


def load_meta(cache_dir: Path, cid: str) -> dict | None:
    try:
        return json.loads((Path(cache_dir) / cid / "layout.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
