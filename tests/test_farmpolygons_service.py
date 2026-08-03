import importlib
import json
import sys
import types

import pytest

pytest.importorskip("shapely")
pytest.importorskip("pyproj")


def _import_farmpolygon_module_with_stubs(monkeypatch):
    gbo_stub = types.ModuleType("ganabosques_orm")
    collections_stub = types.ModuleType("ganabosques_orm.collections")
    fp_stub = types.ModuleType("ganabosques_orm.collections.farmpolygons")
    auxiliaries_stub = types.ModuleType("ganabosques_orm.auxiliaries")
    log_stub = types.ModuleType("ganabosques_orm.auxiliaries.log")

    class FakeLog:
        def __init__(self, enable=True):
            self.enable = enable
            self.updated = None

    class FakeFarmPolygonDoc:
        created_docs = []

        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def save(self):
            FakeFarmPolygonDoc.created_docs.append(self)
            return self

    fp_stub.FarmPolygons = FakeFarmPolygonDoc
    log_stub.Log = FakeLog

    monkeypatch.setitem(sys.modules, "ganabosques_orm", gbo_stub)
    monkeypatch.setitem(sys.modules, "ganabosques_orm.collections", collections_stub)
    monkeypatch.setitem(sys.modules, "ganabosques_orm.collections.farmpolygons", fp_stub)
    monkeypatch.setitem(sys.modules, "ganabosques_orm.auxiliaries", auxiliaries_stub)
    monkeypatch.setitem(sys.modules, "ganabosques_orm.auxiliaries.log", log_stub)

    sys.modules.pop("src.services.farmpolygons_service", None)
    module = importlib.import_module("src.services.farmpolygons_service")
    return module, FakeFarmPolygonDoc


def _build_geojson(coords):
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [coords],
                    },
                    "properties": {},
                }
            ],
        }
    )


def test_validate_geojson_rejects_invalid_json(monkeypatch):
    module, _ = _import_farmpolygon_module_with_stubs(monkeypatch)

    with pytest.raises(ValueError, match="JSON válido"):
        module.FarmPolygonService.validate_geojson("not-json")


def test_validate_geojson_accepts_polygon(monkeypatch):
    module, _ = _import_farmpolygon_module_with_stubs(monkeypatch)

    geojson = _build_geojson([
        [0.0, 0.0],
        [0.0, 0.01],
        [0.01, 0.01],
        [0.01, 0.0],
        [0.0, 0.0],
    ])

    geometry = module.FarmPolygonService.validate_geojson(geojson)

    assert geometry.geom_type == "Polygon"


def test_calculate_geometry_returns_expected_fields(monkeypatch):
    module, _ = _import_farmpolygon_module_with_stubs(monkeypatch)

    geojson = _build_geojson([
        [-74.0, 4.0],
        [-74.0, 4.01],
        [-73.99, 4.01],
        [-73.99, 4.0],
        [-74.0, 4.0],
    ])
    geometry = module.FarmPolygonService.validate_geojson(geojson)

    result = module.FarmPolygonService.calculate_geometry(geometry)

    assert result.latitude == pytest.approx(4.005, rel=1e-3)
    assert result.longitud == pytest.approx(-73.995, rel=1e-3)
    assert result.farm_ha > 0


def test_save_new_version_creates_when_no_current(monkeypatch):
    module, fake_doc_cls = _import_farmpolygon_module_with_stubs(monkeypatch)
    fake_doc_cls.created_docs.clear()

    geojson = _build_geojson([
        [0.0, 0.0],
        [0.0, 0.01],
        [0.01, 0.01],
        [0.01, 0.0],
        [0.0, 0.0],
    ])

    module.FarmPolygonService.save_new_version("farm-1", geojson, current=None)

    assert len(fake_doc_cls.created_docs) == 1
    assert fake_doc_cls.created_docs[0].kwargs["farm_id"] == "farm-1"


def test_save_new_version_skips_when_geometry_unchanged(monkeypatch):
    module, fake_doc_cls = _import_farmpolygon_module_with_stubs(monkeypatch)
    fake_doc_cls.created_docs.clear()

    geojson = _build_geojson([
        [0.0, 0.0],
        [0.0, 0.01],
        [0.01, 0.01],
        [0.01, 0.0],
        [0.0, 0.0],
    ])

    class CurrentDoc:
        def __init__(self, geojson_text):
            self.geojson = geojson_text
            self.log = types.SimpleNamespace(enable=True, updated=None)
            self.saved = False

        def save(self):
            self.saved = True

    current = CurrentDoc(geojson)

    module.FarmPolygonService.save_new_version("farm-1", geojson, current=current)

    assert len(fake_doc_cls.created_docs) == 0
    assert current.saved is False


def test_save_new_version_disables_old_and_creates_new(monkeypatch):
    module, fake_doc_cls = _import_farmpolygon_module_with_stubs(monkeypatch)
    fake_doc_cls.created_docs.clear()

    original_geojson = _build_geojson([
        [0.0, 0.0],
        [0.0, 0.01],
        [0.01, 0.01],
        [0.01, 0.0],
        [0.0, 0.0],
    ])
    new_geojson = _build_geojson([
        [0.0, 0.0],
        [0.0, 0.02],
        [0.02, 0.02],
        [0.02, 0.0],
        [0.0, 0.0],
    ])

    class CurrentDoc:
        def __init__(self, geojson_text):
            self.geojson = geojson_text
            self.log = types.SimpleNamespace(enable=True, updated=None)
            self.saved = False

        def save(self):
            self.saved = True

    current = CurrentDoc(original_geojson)

    module.FarmPolygonService.save_new_version("farm-2", new_geojson, current=current)

    assert current.log.enable is False
    assert current.saved is True
    assert len(fake_doc_cls.created_docs) == 1
    assert fake_doc_cls.created_docs[0].kwargs["farm_id"] == "farm-2"
