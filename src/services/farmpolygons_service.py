from dataclasses import dataclass

from shapely.geometry import shape
from shapely.ops import transform
from pyproj import CRS, Transformer
from datetime import datetime
import json

from ganabosques_orm.collections.farmpolygons import FarmPolygons
from ganabosques_orm.auxiliaries.log import Log


@dataclass
class FarmGeometry:

    geometry: object

    latitude: float

    longitud: float

    farm_ha: float


class FarmPolygonService:

    @staticmethod
    def validate_geojson(geojson_text: str):
        """
        Valida el GeoJSON y retorna la geometría principal.
        """

        try:
            geojson = json.loads(geojson_text)

        except json.JSONDecodeError:
            raise ValueError(
                "El contenido no es un JSON válido. Por favor, verifica el formato del GeoJSON."
            )

        if geojson.get("type") != "FeatureCollection":
            raise ValueError(
                "El GeoJSON debe ser un FeatureCollection."
            )

        features = geojson.get("features")

        if not features:
            raise ValueError(
                "El GeoJSON no contiene Features."
            )

        geometry = features[0].get("geometry")

        if geometry is None:
            raise ValueError(
                "No se encontró la geometría. Asegúrate de que el GeoJSON contenga al menos un Feature con una geometría válida."
            )

        geom = shape(geometry)

        if geom.geom_type not in (
            "Polygon",
            "MultiPolygon"
        ):
            raise ValueError(
                "Solo se permiten Polygon o MultiPolygon."
            )

        if not geom.is_valid:
            raise ValueError(
                "La geometría es inválida."
            )

        if geom.is_empty:
            raise ValueError(
                "La geometría está vacía."
            )

        if geom.geom_type == "MultiPolygon":
            geom = max(
                geom.geoms,
                key=lambda g: g.area
            )

        return geom

    @staticmethod
    def calculate_geometry(geometry):

        centroid = geometry.centroid

        latitude = centroid.y
        longitud = centroid.x

        utm_zone = int((longitud + 180) / 6) + 1

        epsg = (
            32600 + utm_zone
            if latitude >= 0
            else 32700 + utm_zone
        )

        transformer = Transformer.from_crs(
            CRS.from_epsg(4326),
            CRS.from_epsg(epsg),
            always_xy=True
        )

        projected = transform(
            transformer.transform,
            geometry
        )

        farm_ha = projected.area / 10000

        return FarmGeometry(
            geometry=geometry,
            latitude=latitude,
            longitud=longitud,
            farm_ha=farm_ha
        )

    @staticmethod
    def save_new_version(
        farm,
        geojson_text,
        current
    ):

        if current is None:

            geom = FarmPolygonService.validate_geojson(
                geojson_text
            )

            data = FarmPolygonService.calculate_geometry(
                geom
            )

            FarmPolygons(
                farm_id=farm,
                geojson=geojson_text,
                latitude=data.latitude,
                longitud=data.longitud,
                farm_ha=data.farm_ha,
                log=Log(enable=True)
            ).save()

        else:
            old_geom = FarmPolygonService.validate_geojson(
                current.geojson
            )
    
            new_geom = FarmPolygonService.validate_geojson(
                geojson_text
            )
    
            if old_geom.equals(new_geom):
                return

            data = FarmPolygonService.calculate_geometry(
                new_geom
            )

            current.log.enable = False
            current.log.updated = datetime.now()
            current.save()

            FarmPolygons(
                farm_id=farm,
                geojson=geojson_text,
                latitude=data.latitude,
                longitud=data.longitud,
                farm_ha=data.farm_ha,
                log=Log(enable=True)
            ).save()