import importlib
import sys
import types
from datetime import date

import pytest


def _import_geoserver_module_with_stubs(monkeypatch):
    mongoengine_stub = types.ModuleType("mongoengine")
    mongoengine_stub.connect = lambda *args, **kwargs: None

    geoserver_stub = types.ModuleType("geoserver")
    geoserver_catalog_stub = types.ModuleType("geoserver.catalog")
    geoserver_support_stub = types.ModuleType("geoserver.support")

    class FakeCatalog:
        def __init__(self, *args, **kwargs):
            pass

    class FakeDimensionInfo:
        def __init__(self, *args, **kwargs):
            pass

    geoserver_catalog_stub.Catalog = FakeCatalog
    geoserver_support_stub.DimensionInfo = FakeDimensionInfo

    gbo_stub = types.ModuleType("ganabosques_orm")
    collections_stub = types.ModuleType("ganabosques_orm.collections")
    deforestation_stub = types.ModuleType("ganabosques_orm.collections.deforestation")
    enums_stub = types.ModuleType("ganabosques_orm.enums")
    deftype_stub = types.ModuleType("ganabosques_orm.enums.deforestationtype")
    defsource_stub = types.ModuleType("ganabosques_orm.enums.deforestationsource")
    auxiliaries_stub = types.ModuleType("ganabosques_orm.auxiliaries")
    log_stub = types.ModuleType("ganabosques_orm.auxiliaries.log")

    class FakeDeforestation:
        objects = lambda *args, **kwargs: []

    class FakeEnum:
        ANNUAL = "ANNUAL"
        CUMULATIVE = "CUMULATIVE"
        NAD = "NAD"
        ATD = "ATD"
        SMBYC = "SMBYC"

        def __getitem__(self, item):
            return item

    class FakeLog:
        def __init__(self, *args, **kwargs):
            pass

    deforestation_stub.Deforestation = FakeDeforestation
    deftype_stub.DeforestationType = FakeEnum
    defsource_stub.DeforestationSource = {"SMBYC": "SMBYC", "NAD": "NAD", "ATD": "ATD"}
    log_stub.Log = FakeLog

    monkeypatch.setitem(sys.modules, "mongoengine", mongoengine_stub)
    monkeypatch.setitem(sys.modules, "geoserver", geoserver_stub)
    monkeypatch.setitem(sys.modules, "geoserver.catalog", geoserver_catalog_stub)
    monkeypatch.setitem(sys.modules, "geoserver.support", geoserver_support_stub)
    monkeypatch.setitem(sys.modules, "ganabosques_orm", gbo_stub)
    monkeypatch.setitem(sys.modules, "ganabosques_orm.collections", collections_stub)
    monkeypatch.setitem(sys.modules, "ganabosques_orm.collections.deforestation", deforestation_stub)
    monkeypatch.setitem(sys.modules, "ganabosques_orm.enums", enums_stub)
    monkeypatch.setitem(sys.modules, "ganabosques_orm.enums.deforestationtype", deftype_stub)
    monkeypatch.setitem(sys.modules, "ganabosques_orm.enums.deforestationsource", defsource_stub)
    monkeypatch.setitem(sys.modules, "ganabosques_orm.auxiliaries", auxiliaries_stub)
    monkeypatch.setitem(sys.modules, "ganabosques_orm.auxiliaries.log", log_stub)

    sys.modules.pop("src.geoserver_import", None)
    return importlib.import_module("src.geoserver_import")


def test_ensure_rest_url_variants(monkeypatch):
    module = _import_geoserver_module_with_stubs(monkeypatch)

    assert module._ensure_rest_url("https://host/geoserver") == "https://host/geoserver/rest/"
    assert module._ensure_rest_url("https://host/geoserver/rest") == "https://host/geoserver/rest/"
    assert module._ensure_rest_url("https://host/rest") == "https://host/rest/"
    assert module._ensure_rest_url("") == ""


def test_parse_period_quarter_format(monkeypatch):
    module = _import_geoserver_module_with_stubs(monkeypatch)

    start_dt, end_dt = module._parse_period_from_filename("nad_deforestation_201701.tif")

    assert start_dt == date(2017, 1, 1)
    assert end_dt == date(2017, 3, 31)


def test_parse_period_annual_range(monkeypatch):
    module = _import_geoserver_module_with_stubs(monkeypatch)

    start_dt, end_dt = module._parse_period_from_filename("smbyc_deforestation_annual_2010-2012.tif")

    assert start_dt == date(2010, 1, 1)
    assert end_dt == date(2012, 12, 31)


def test_parse_period_raises_for_invalid_filename(monkeypatch):
    module = _import_geoserver_module_with_stubs(monkeypatch)

    with pytest.raises(ValueError):
        module._parse_period_from_filename("archivo_sin_fecha.tif")


def test_list_tifs_returns_sorted_tiffs(monkeypatch, tmp_path):
    module = _import_geoserver_module_with_stubs(monkeypatch)

    (tmp_path / "b.tif").write_bytes(b"b")
    (tmp_path / "a.tif").write_bytes(b"a")
    (tmp_path / "ignore.txt").write_text("x", encoding="utf-8")

    result = module._list_tifs(str(tmp_path))

    assert result == [str(tmp_path / "a.tif"), str(tmp_path / "b.tif")]
