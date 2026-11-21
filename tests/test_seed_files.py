import importlib.util
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from tagwerk.project import Project

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "generate_seed_files.py"


@pytest.fixture(scope="module")
def gen():
    spec = importlib.util.spec_from_file_location("generate_seed_files", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def out(gen, tmp_path_factory):
    d = tmp_path_factory.mktemp("seedfiles")
    return d, gen.generate(d)


def test_schedule_xml_is_p6(out):
    root = ET.parse(out[0] / "schedule.xml").getroot()
    assert root.tag.endswith("APIBusinessObjects")
    acts = [e for e in root.iter() if e.tag.endswith("Activity")]
    assert len(acts) == len(Project.from_seed().activities)


@pytest.mark.parametrize("name, phase", [("boq.x83", "83"), ("boq.x84", "84")])
def test_boq_is_gaeb(out, name, phase):
    root = ET.parse(out[0] / name).getroot()
    assert root.tag.endswith("GAEB") and f"DA{phase}" in root.tag
    items = [e for e in root.iter() if e.tag.endswith("Item")]
    assert len(items) == len(Project.from_seed().boq)
    prices = [e for e in root.iter() if e.tag.endswith("UP")]
    assert bool(prices) == (phase == "84")


def test_output_is_deterministic(gen, out, tmp_path):
    gen.generate(tmp_path)
    for f in ("schedule.xml", "boq.x83", "boq.x84", "auditorium.ifc"):
        if (out[0] / f).exists():
            assert (out[0] / f).read_bytes() == (tmp_path / f).read_bytes(), f


def test_ifc_matches_the_seed(out):
    ifcopenshell = pytest.importorskip("ifcopenshell")
    import ifcopenshell.util.element as ue

    project = Project.from_seed()
    ifc = ifcopenshell.open(str(out[0] / "auditorium.ifc"))
    assert ifc.schema == "IFC4"
    assert ifc.by_type("IfcProject")[0].Name == "Hörsaal Sanierung"

    spaces = {s.Name: s for s in ifc.by_type("IfcSpace")}
    assert set(spaces) == set(project.zones)
    for zid, s in spaces.items():
        assert s.LongName == project.zones[zid]["name_de"]
    assert [s.Name for s in ifc.by_type("IfcBuildingStorey")] == ["EG"]

    for eid, el in project.elements.items():
        prod = ifc.by_guid(el["global_id"])
        assert prod.is_a() == el["ifc_class"], eid
        assert prod.Name == el["name_de"] and prod.Description == el["name_en"]
        container = ue.get_container(prod)
        spaced = container.is_a("IfcSpace") and container.Name == el["zone"]
        referenced = any(r.RelatingStructure.Name == el["zone"] for r in prod.ReferencedInStructures)
        assert spaced or referenced, eid
        pset = ue.get_psets(prod)["Pset_Tagwerk"]
        assert pset["ElementId"] == eid and pset["DIN276"] == el["din276"] and pset["Unit"] == el["unit"]
        assert pset["Quantity"] == pytest.approx(el["qty"])
        assert pset["Aliases"] == "|".join(el["aliases"])
        assert pset.get("MarkerId") == el["marker_id"]
    assert len(ifc.by_type("IfcElement")) == len(project.elements)
