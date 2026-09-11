"""Pruebas de los formularios que no estaban cubiertos: Adm2, Adm3, Farm y Enterprise."""

from types import SimpleNamespace

import pytest

import src.forms.adm2_form as adm2_form_module
import src.forms.adm3_form as adm3_form_module
import src.forms.enterprise_form as enterprise_form_module
from src.forms.adm2_form import Adm2Form
from src.forms.adm3_form import Adm3Form
from src.forms.enterprise_form import EnterpriseForm
from src.forms.farm_form import FarmForm
from helpers import FakeObjectsManager, FakeQuerySet


def _fake_documents(*pairs):
    return [SimpleNamespace(id=doc_id, name=name) for doc_id, name in pairs]


# ---------------------------------------------------------------------------
# Adm2Form
# ---------------------------------------------------------------------------

def test_adm2_form_load_adm1_choices(flask_app, monkeypatch):
    documentos = _fake_documents(("a1", "ANTIOQUIA"), ("a2", "CALDAS"))
    monkeypatch.setattr(
        adm2_form_module,
        "Adm1",
        SimpleNamespace(objects=FakeObjectsManager(FakeQuerySet(documentos))),
    )

    with flask_app.test_request_context(method="POST", data={}):
        form = Adm2Form()
        form.load_adm1_choices()

        assert form.adm1_id.choices == [("a1", "ANTIOQUIA"), ("a2", "CALDAS")]


def test_adm2_form_requires_name_and_adm1(flask_app, monkeypatch):
    monkeypatch.setattr(
        adm2_form_module,
        "Adm1",
        SimpleNamespace(objects=FakeObjectsManager(FakeQuerySet([]))),
    )

    with flask_app.test_request_context(method="POST", data={"name": "", "adm1_id": ""}):
        form = Adm2Form()
        form.load_adm1_choices()

        assert form.validate() is False
        assert form.name.errors
        assert form.adm1_id.errors


def test_adm2_form_accepts_valid_payload(flask_app, monkeypatch):
    documentos = _fake_documents(("a1", "ANTIOQUIA"))
    monkeypatch.setattr(
        adm2_form_module,
        "Adm1",
        SimpleNamespace(objects=FakeObjectsManager(FakeQuerySet(documentos))),
    )

    data = {"name": "MEDELLIN", "ext_id": "05001", "adm1_id": "a1", "enable": "y"}
    with flask_app.test_request_context(method="POST", data=data):
        form = Adm2Form()
        form.load_adm1_choices()

        assert form.validate() is True
        assert form.enable.data is True


def test_adm2_form_rejects_name_longer_than_255(flask_app, monkeypatch):
    documentos = _fake_documents(("a1", "ANTIOQUIA"))
    monkeypatch.setattr(
        adm2_form_module,
        "Adm1",
        SimpleNamespace(objects=FakeObjectsManager(FakeQuerySet(documentos))),
    )

    data = {"name": "x" * 256, "adm1_id": "a1"}
    with flask_app.test_request_context(method="POST", data=data):
        form = Adm2Form()
        form.load_adm1_choices()

        assert form.validate() is False
        assert form.name.errors


# ---------------------------------------------------------------------------
# Adm3Form
# ---------------------------------------------------------------------------

def test_adm3_form_load_adm2_choices_ordena_por_nombre(flask_app, monkeypatch):
    queryset = FakeQuerySet(_fake_documents(("m1", "BELLO"), ("m2", "ITAGUI")))
    monkeypatch.setattr(
        adm3_form_module,
        "Adm2",
        SimpleNamespace(objects=FakeObjectsManager(queryset)),
    )

    with flask_app.test_request_context(method="POST", data={}):
        form = Adm3Form()
        form.load_adm2_choices()

        assert form.adm2_id.choices == [("m1", "BELLO"), ("m2", "ITAGUI")]
        assert ("name",) in queryset.order_by_calls


def test_adm3_form_requires_adm2(flask_app, monkeypatch):
    monkeypatch.setattr(
        adm3_form_module,
        "Adm2",
        SimpleNamespace(objects=FakeObjectsManager(FakeQuerySet([]))),
    )

    with flask_app.test_request_context(method="POST", data={"name": "LA VEREDA"}):
        form = Adm3Form()
        form.load_adm2_choices()

        assert form.validate() is False
        assert any("municipio" in msg for msg in form.adm2_id.errors)


def test_adm3_form_acepta_adm2_fuera_de_choices(flask_app, monkeypatch):
    """``validate_choice=False`` permite valores cargados dinámicamente por JS."""
    monkeypatch.setattr(
        adm3_form_module,
        "Adm2",
        SimpleNamespace(objects=FakeObjectsManager(FakeQuerySet([]))),
    )

    data = {"name": "LA VEREDA", "ext_id": "05001001", "adm2_id": "id-no-listado"}
    with flask_app.test_request_context(method="POST", data=data):
        form = Adm3Form()
        form.load_adm2_choices()

        assert form.validate() is True
        assert form.adm2_id.data == "id-no-listado"


# ---------------------------------------------------------------------------
# FarmForm
# ---------------------------------------------------------------------------

GEOJSON_MINIMO = (
    '{"type": "FeatureCollection", "features": [{"type": "Feature", '
    '"geometry": {"type": "Polygon", "coordinates": [[[0,0],[0,1],[1,1],[0,0]]]}, '
    '"properties": {}}]}'
)


def _farm_payload(**overrides):
    data = {
        "adm3_id": "vereda-1",
        "ext_id-0-source": "SIT_CODE",
        "ext_id-0-ext_code": "ABC123",
        "farm_source": "SIT",
        "value_chain": "LIVESTOCK",
        "geojson": GEOJSON_MINIMO,
        "enable": "y",
    }
    data.update(overrides)
    return data


def _primer_nombre_de_enum(form_field):
    return form_field.choices[0][0]


def test_farm_form_requires_geojson(flask_app):
    with flask_app.test_request_context(method="POST", data=_farm_payload(geojson="")):
        form = FarmForm()
        form.farm_source.data = _primer_nombre_de_enum(form.farm_source)

        assert form.validate() is False
        assert any("GeoJSON" in msg for msg in form.geojson.errors)


def test_farm_form_requires_adm3(flask_app):
    with flask_app.test_request_context(method="POST", data=_farm_payload(adm3_id="")):
        form = FarmForm()

        assert form.validate() is False
        assert any("vereda" in msg for msg in form.adm3_id.errors)


def test_farm_form_requires_ext_code_en_cada_entrada(flask_app):
    payload = _farm_payload()
    payload["ext_id-0-ext_code"] = ""

    with flask_app.test_request_context(method="POST", data=payload):
        form = FarmForm()

        assert form.validate() is False
        assert form.ext_id.entries[0].form.ext_code.errors


def test_farm_form_admite_varias_entradas_de_ext_id(flask_app):
    source_valido = None
    with flask_app.test_request_context(method="POST", data={}):
        source_valido = FarmForm().ext_id.entries[0].form.source.choices[0][0]

    payload = _farm_payload(**{
        "ext_id-0-source": source_valido,
        "ext_id-1-source": source_valido,
        "ext_id-1-ext_code": "XYZ789",
    })

    with flask_app.test_request_context(method="POST", data=payload):
        form = FarmForm()
        form.farm_source.data = _primer_nombre_de_enum(form.farm_source)

        assert len(form.ext_id.entries) == 2
        assert form.ext_id.entries[1].form.ext_code.data == "XYZ789"


def test_farm_form_rechaza_ext_code_demasiado_largo(flask_app):
    payload = _farm_payload()
    payload["ext_id-0-ext_code"] = "x" * 101

    with flask_app.test_request_context(method="POST", data=payload):
        form = FarmForm()

        assert form.validate() is False
        assert form.ext_id.entries[0].form.ext_code.errors


def test_farm_form_load_adm3_choices(flask_app, monkeypatch):
    import src.forms.farm_form as farm_form_module

    queryset = FakeQuerySet(_fake_documents(("v1", "EL PORVENIR"), ("v2", "LA UNION")))
    monkeypatch.setattr(
        farm_form_module,
        "Adm3",
        SimpleNamespace(objects=FakeObjectsManager(queryset)),
    )

    with flask_app.test_request_context(method="POST", data={}):
        form = FarmForm()
        form.load_adm3_choices()

        assert form.adm3_id.choices == [("v1", "EL PORVENIR"), ("v2", "LA UNION")]


def test_farm_form_value_chain_incluye_las_tres_cadenas(flask_app):
    with flask_app.test_request_context(method="POST", data={}):
        form = FarmForm()
        valores = [value for value, _ in form.value_chain.choices]

        assert {"CACAO", "LIVESTOCK", "COFFEE"}.issubset(set(valores))


# ---------------------------------------------------------------------------
# EnterpriseForm
# ---------------------------------------------------------------------------

def _cargar_enterprise_form(monkeypatch, adm2_docs=None):
    queryset = FakeQuerySet(adm2_docs if adm2_docs is not None else _fake_documents(("m1", "BELLO")))
    monkeypatch.setattr(
        enterprise_form_module,
        "Adm2",
        SimpleNamespace(objects=FakeObjectsManager(queryset)),
    )

    form = EnterpriseForm()
    form.load_adm2_choices()
    form.load_label_choices()
    form.load_type_enterprise_choices()
    form.load_value_chain_choices()
    return form


def _enterprise_payload(form, **overrides):
    data = {
        "name": "Frigorífico del Norte",
        "ext_code": "900123456",
        "label": form.label.choices[1][0],
        "adm2_id": "m1",
        "type_enterprise": form.type_enterprise.choices[1][0],
        "value_chain": form.value_chain.choices[1][0],
        "latitude": "6.25",
        "longitud": "-75.56",
        "enable": "y",
    }
    data.update(overrides)
    return data


def test_enterprise_form_carga_todas_las_opciones(flask_app, monkeypatch):
    with flask_app.test_request_context(method="POST", data={}):
        form = _cargar_enterprise_form(monkeypatch)

        assert form.adm2_id.choices[0] == ("", "--- Selecciona un municipio ---")
        assert form.label.choices[0] == ("", "--- Selecciona un tipo de código ---")
        assert form.type_enterprise.choices[0] == ("", "--- Selecciona un tipo de empresa ---")
        assert form.value_chain.choices[0] == ("", "--- Selecciona una cadena de valor ---")
        assert len(form.label.choices) > 1


def test_enterprise_form_traduce_cadenas_de_valor(flask_app, monkeypatch):
    with flask_app.test_request_context(method="POST", data={}):
        form = _cargar_enterprise_form(monkeypatch)
        etiquetas = dict(form.value_chain.choices)

        if "CACAO" in etiquetas:
            assert etiquetas["CACAO"] == "Cacao"
        if "LIVESTOCK" in etiquetas:
            assert etiquetas["LIVESTOCK"] == "Ganadería"


def test_enterprise_form_acepta_payload_valido(flask_app, monkeypatch):
    with flask_app.test_request_context(method="POST", data={}):
        plantilla = _cargar_enterprise_form(monkeypatch)
        payload = _enterprise_payload(plantilla)

    with flask_app.test_request_context(method="POST", data=payload):
        form = _cargar_enterprise_form(monkeypatch)

        assert form.validate() is True, form.errors
        assert form.latitude.data == pytest.approx(6.25)


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("latitude", "95"),
        ("latitude", "-95"),
        ("longitud", "200"),
        ("longitud", "-200"),
    ],
)
def test_enterprise_form_valida_rangos_geograficos(flask_app, monkeypatch, campo, valor):
    with flask_app.test_request_context(method="POST", data={}):
        plantilla = _cargar_enterprise_form(monkeypatch)
        payload = _enterprise_payload(plantilla, **{campo: valor})

    with flask_app.test_request_context(method="POST", data=payload):
        form = _cargar_enterprise_form(monkeypatch)

        assert form.validate() is False
        assert getattr(form, campo).errors


def test_enterprise_form_requiere_municipio(flask_app, monkeypatch):
    with flask_app.test_request_context(method="POST", data={}):
        plantilla = _cargar_enterprise_form(monkeypatch)
        payload = _enterprise_payload(plantilla, adm2_id="")

    with flask_app.test_request_context(method="POST", data=payload):
        form = _cargar_enterprise_form(monkeypatch)

        assert form.validate() is False
        assert any("municipio" in msg for msg in form.adm2_id.errors)
