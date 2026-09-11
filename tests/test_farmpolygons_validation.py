"""Pruebas de validación y cálculo geométrico del servicio de polígonos de finca."""

import json

import pytest

pytest.importorskip("shapely")
pytest.importorskip("pyproj")

from src.services.farmpolygons_service import FarmPolygonService  # noqa: E402


def _feature_collection(geometria):
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "geometry": geometria, "properties": {}}],
        }
    )


def _poligono(coords):
    return {"type": "Polygon", "coordinates": [coords]}


CUADRADO = [[0.0, 0.0], [0.0, 0.01], [0.01, 0.01], [0.01, 0.0], [0.0, 0.0]]


# ---------------------------------------------------------------------------
# validate_geojson: rechazos
# ---------------------------------------------------------------------------

def test_rechaza_json_malformado():
    with pytest.raises(ValueError, match="no es un JSON válido"):
        FarmPolygonService.validate_geojson("{esto no cierra")


def test_rechaza_si_no_es_feature_collection():
    payload = json.dumps({"type": "Feature", "geometry": _poligono(CUADRADO)})

    with pytest.raises(ValueError, match="FeatureCollection"):
        FarmPolygonService.validate_geojson(payload)


def test_rechaza_feature_collection_sin_features():
    payload = json.dumps({"type": "FeatureCollection", "features": []})

    with pytest.raises(ValueError, match="no contiene Features"):
        FarmPolygonService.validate_geojson(payload)


def test_rechaza_feature_sin_geometria():
    payload = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "geometry": None, "properties": {}}],
        }
    )

    with pytest.raises(ValueError, match="No se encontró la geometría"):
        FarmPolygonService.validate_geojson(payload)


@pytest.mark.parametrize(
    "geometria",
    [
        {"type": "Point", "coordinates": [0.0, 0.0]},
        {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
        {"type": "MultiPoint", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
    ],
)
def test_rechaza_geometrias_que_no_son_poligonos(geometria):
    with pytest.raises(ValueError, match="Solo se permiten Polygon o MultiPolygon"):
        FarmPolygonService.validate_geojson(_feature_collection(geometria))


def test_rechaza_poligono_autointersectado():
    """Un 'moño' es topológicamente inválido y debe rechazarse."""
    lazo = [[0.0, 0.0], [1.0, 1.0], [1.0, 0.0], [0.0, 1.0], [0.0, 0.0]]

    with pytest.raises(ValueError, match="geometría es inválida"):
        FarmPolygonService.validate_geojson(_feature_collection(_poligono(lazo)))


def test_rechaza_poligono_vacio():
    payload = _feature_collection({"type": "Polygon", "coordinates": []})

    with pytest.raises(ValueError, match="geometría está vacía"):
        FarmPolygonService.validate_geojson(payload)


# ---------------------------------------------------------------------------
# validate_geojson: aceptaciones
# ---------------------------------------------------------------------------

def test_acepta_poligono_simple():
    geometria = FarmPolygonService.validate_geojson(_feature_collection(_poligono(CUADRADO)))

    assert geometria.geom_type == "Polygon"


def test_toma_solo_el_primer_feature():
    payload = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": _poligono(CUADRADO), "properties": {}},
                {"type": "Feature", "geometry": _poligono(
                    [[5.0, 5.0], [5.0, 5.1], [5.1, 5.1], [5.1, 5.0], [5.0, 5.0]]
                ), "properties": {}},
            ],
        }
    )

    geometria = FarmPolygonService.validate_geojson(payload)

    assert geometria.bounds[0] == pytest.approx(0.0)


def test_multipolygon_conserva_la_parte_de_mayor_area():
    pequeno = [[0.0, 0.0], [0.0, 0.01], [0.01, 0.01], [0.01, 0.0], [0.0, 0.0]]
    grande = [[1.0, 1.0], [1.0, 1.5], [1.5, 1.5], [1.5, 1.0], [1.0, 1.0]]
    geometria_json = {"type": "MultiPolygon", "coordinates": [[pequeno], [grande]]}

    geometria = FarmPolygonService.validate_geojson(_feature_collection(geometria_json))

    assert geometria.geom_type == "Polygon"
    assert geometria.bounds[0] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# calculate_geometry
# ---------------------------------------------------------------------------

def test_calcula_centroide_y_area_en_hemisferio_norte():
    coords = [[-74.0, 4.0], [-74.0, 4.01], [-73.99, 4.01], [-73.99, 4.0], [-74.0, 4.0]]
    geometria = FarmPolygonService.validate_geojson(_feature_collection(_poligono(coords)))

    resultado = FarmPolygonService.calculate_geometry(geometria)

    assert resultado.latitude == pytest.approx(4.005, rel=1e-3)
    assert resultado.longitud == pytest.approx(-73.995, rel=1e-3)
    # Un cuadrado de 0.01° de lado en el ecuador ronda 1,23 km² ≈ 123 ha.
    assert resultado.farm_ha == pytest.approx(123, rel=0.05)


def test_calcula_area_en_hemisferio_sur():
    """Debajo del ecuador el servicio debe usar la zona UTM sur (EPSG 327xx)."""
    coords = [[-74.0, -4.0], [-74.0, -3.99], [-73.99, -3.99], [-73.99, -4.0], [-74.0, -4.0]]
    geometria = FarmPolygonService.validate_geojson(_feature_collection(_poligono(coords)))

    resultado = FarmPolygonService.calculate_geometry(geometria)

    assert resultado.latitude < 0
    assert resultado.farm_ha == pytest.approx(123, rel=0.05)


def test_area_crece_con_el_tamano_del_poligono():
    pequeno = FarmPolygonService.validate_geojson(_feature_collection(_poligono(CUADRADO)))
    grande = FarmPolygonService.validate_geojson(
        _feature_collection(_poligono(
            [[0.0, 0.0], [0.0, 0.02], [0.02, 0.02], [0.02, 0.0], [0.0, 0.0]]
        ))
    )

    area_pequena = FarmPolygonService.calculate_geometry(pequeno).farm_ha
    area_grande = FarmPolygonService.calculate_geometry(grande).farm_ha

    assert area_grande == pytest.approx(area_pequena * 4, rel=0.05)


def test_calculate_geometry_devuelve_la_geometria_original():
    geometria = FarmPolygonService.validate_geojson(_feature_collection(_poligono(CUADRADO)))

    resultado = FarmPolygonService.calculate_geometry(geometria)

    assert resultado.geometry is geometria


# ---------------------------------------------------------------------------
# save_new_version: propagación de errores de validación
# ---------------------------------------------------------------------------

def test_save_new_version_propaga_error_de_geojson_invalido():
    with pytest.raises(ValueError):
        FarmPolygonService.save_new_version("finca-1", "no soy json", current=None)


def test_save_new_version_valida_tambien_la_version_guardada():
    """Si el polígono almacenado quedó corrupto, el error debe salir a la luz."""
    nuevo = _feature_collection(_poligono(CUADRADO))

    class PoligonoCorrupto:
        geojson = "{roto"

    with pytest.raises(ValueError):
        FarmPolygonService.save_new_version("finca-1", nuevo, current=PoligonoCorrupto())
