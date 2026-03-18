import unittest

import mongomock
from mongoengine import connect, disconnect
from bson import ObjectId

from ganabosques_orm.collections.adm1 import Adm1
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.collections.adm3 import Adm3
from ganabosques_orm.collections.farm import Farm
from ganabosques_orm.collections.farmpolygons import FarmPolygons
from ganabosques_orm.collections.analysis import Analysis
from ganabosques_orm.collections.protectedareas import ProtectedAreas
from ganabosques_orm.collections.farmingareas import FarmingAreas
from ganabosques_orm.collections.deforestation import Deforestation
from ganabosques_orm.collections.farmrisk import FarmRisk

from ganabosques_orm.auxiliaries.attributes import Attributes
from ganabosques_orm.auxiliaries.extidfarm import ExtIdFarm
from ganabosques_orm.auxiliaries.bufferpolygon import BufferPolygon
from ganabosques_orm.auxiliaries.typeanalysis import TypeAnalysis

from ganabosques_orm.enums.farmsource import FarmSource
from ganabosques_orm.enums.valuechain import ValueChain
from ganabosques_orm.enums.deforestationtype import DeforestationType
from ganabosques_orm.enums.deforestationsource import DeforestationSource


class TestFarmRisk(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        connect(
            db='mongoenginetest',
            host='mongodb://localhost',
            mongo_client_class=mongomock.MongoClient
        )

    @classmethod
    def tearDownClass(cls):
        disconnect()

    def tearDown(self):
        FarmRisk.drop_collection()
        FarmPolygons.drop_collection()
        Farm.drop_collection()
        Analysis.drop_collection()
        Deforestation.drop_collection()
        FarmingAreas.drop_collection()
        ProtectedAreas.drop_collection()
        Adm3.drop_collection()
        Adm2.drop_collection()
        Adm1.drop_collection()

    def _get_farm_source(self):
        return list(FarmSource)[0]

    def _get_value_chain(self):
        return list(ValueChain)[0]

    def _get_deforestation_source(self):
        return list(DeforestationSource)[0]

    def _get_deforestation_type(self):
        return list(DeforestationType)[0]

    def _create_adm3(self):
        adm1 = Adm1(
            name='Cundinamarca',
            ext_id='ADM1-001',
            ugg_size=100.0
        )
        adm1.save()

        adm2 = Adm2(
            adm1_id=adm1,
            name='Bogota',
            ext_id='ADM2-001'
        )
        adm2.save()

        adm3 = Adm3(
            adm2_id=adm2,
            name='Usaquen',
            ext_id='ADM3-001',
            label='Localidad'
        )
        adm3.save()

        return adm3

    def _create_farm(self):
        farm = Farm(
            adm3_id=self._create_adm3(),
            ext_id=[ExtIdFarm()],
            farm_source=self._get_farm_source()
        )
        farm.save()
        return farm

    def _create_farm_polygon(self, farm):
        farm_polygon = FarmPolygons(
            farm_id=farm,
            geojson='{"type":"Polygon","coordinates":[]}',
            latitude=4.7110,
            longitud=-74.0721,
            farm_ha=10.5,
            radio=50.0,
            buffer_inputs=[BufferPolygon()]
        )
        farm_polygon.save()
        return farm_polygon

    def _create_analysis(self):
        protected_area = ProtectedAreas(
            name='Parque Natural',
            path='/data/protected/parque.geojson'
        )
        protected_area.save()

        farming_area = FarmingAreas(
            name='Zona Agricola',
            path='/data/farming/zona.geojson'
        )
        farming_area.save()

        deforestation = Deforestation(
            deforestation_source=self._get_deforestation_source(),
            deforestation_type=self._get_deforestation_type(),
            name='Deforestacion 2024',
            path='/data/deforestation/2024.geojson'
        )
        deforestation.save()

        analysis = Analysis(
            protected_areas_id=protected_area,
            farming_areas_id=farming_area,
            deforestation_id=deforestation,
            user_id=ObjectId(),
            type_analysis=TypeAnalysis(),
            value_chain=self._get_value_chain()
        )
        analysis.save()
        return analysis

    def _build_attributes(self):
        return Attributes()

    def test_create_instance(self):
        instance = FarmRisk()
        self.assertIsInstance(instance, FarmRisk)

    def test_collection_name_is_farmrisk(self):
        self.assertEqual(FarmRisk._get_collection_name(), 'farmrisk')

    def test_create_instance_with_valid_data(self):
        farm = self._create_farm()
        analysis = self._create_analysis()
        farm_polygon = self._create_farm_polygon(farm)

        instance = FarmRisk(
            farm_id=farm,
            analysis_id=analysis,
            farm_polygons_id=farm_polygon,
            deforestation=self._build_attributes(),
            protected=self._build_attributes(),
            farming_in=self._build_attributes(),
            farming_out=self._build_attributes(),
            risk_direct=True,
            risk_input=False,
            risk_output=True
        )

        self.assertEqual(instance.farm_id, farm)
        self.assertEqual(instance.analysis_id, analysis)
        self.assertEqual(instance.farm_polygons_id, farm_polygon)
        self.assertIsInstance(instance.deforestation, Attributes)
        self.assertIsInstance(instance.protected, Attributes)
        self.assertIsInstance(instance.farming_in, Attributes)
        self.assertIsInstance(instance.farming_out, Attributes)
        self.assertTrue(instance.risk_direct)
        self.assertFalse(instance.risk_input)
        self.assertTrue(instance.risk_output)

    def test_save_instance_with_valid_data(self):
        farm = self._create_farm()
        analysis = self._create_analysis()
        farm_polygon = self._create_farm_polygon(farm)

        instance = FarmRisk(
            farm_id=farm,
            analysis_id=analysis,
            farm_polygons_id=farm_polygon,
            deforestation=self._build_attributes(),
            protected=self._build_attributes(),
            farming_in=self._build_attributes(),
            farming_out=self._build_attributes(),
            risk_direct=True,
            risk_input=True,
            risk_output=False
        )
        instance.save()

        saved = FarmRisk.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.farm_id.id, farm.id)
        self.assertEqual(saved.analysis_id.id, analysis.id)
        self.assertEqual(saved.farm_polygons_id.id, farm_polygon.id)
        self.assertIsInstance(saved.deforestation, Attributes)
        self.assertIsInstance(saved.protected, Attributes)
        self.assertIsInstance(saved.farming_in, Attributes)
        self.assertIsInstance(saved.farming_out, Attributes)
        self.assertTrue(saved.risk_direct)
        self.assertTrue(saved.risk_input)
        self.assertFalse(saved.risk_output)

    def test_save_instance_with_empty_fields(self):
        instance = FarmRisk()
        instance.save()

        saved = FarmRisk.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNone(saved.farm_id)
        self.assertIsNone(saved.analysis_id)
        self.assertIsNone(saved.farm_polygons_id)
        self.assertIsNone(saved.deforestation)
        self.assertIsNone(saved.protected)
        self.assertIsNone(saved.farming_in)
        self.assertIsNone(saved.farming_out)
        self.assertIsNone(saved.risk_direct)
        self.assertIsNone(saved.risk_input)
        self.assertIsNone(saved.risk_output)

    def test_create_instance_with_invalid_deforestation_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            FarmRisk(deforestation='invalid_attributes')

    def test_create_instance_with_invalid_protected_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            FarmRisk(protected='invalid_attributes')

    def test_create_instance_with_invalid_farming_in_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            FarmRisk(farming_in='invalid_attributes')

    def test_create_instance_with_invalid_farming_out_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            FarmRisk(farming_out='invalid_attributes')

    def test_update_persisted_instance(self):
        farm = self._create_farm()
        analysis = self._create_analysis()
        farm_polygon = self._create_farm_polygon(farm)

        instance = FarmRisk(
            farm_id=farm,
            analysis_id=analysis,
            farm_polygons_id=farm_polygon,
            deforestation=self._build_attributes(),
            protected=self._build_attributes(),
            farming_in=self._build_attributes(),
            farming_out=self._build_attributes(),
            risk_direct=False,
            risk_input=False,
            risk_output=False
        )
        instance.save()

        instance.risk_direct = True
        instance.risk_input = True
        instance.risk_output = True
        instance.save()

        updated = FarmRisk.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.farm_id.id, farm.id)
        self.assertEqual(updated.analysis_id.id, analysis.id)
        self.assertEqual(updated.farm_polygons_id.id, farm_polygon.id)
        self.assertTrue(updated.risk_direct)
        self.assertTrue(updated.risk_input)
        self.assertTrue(updated.risk_output)

    def test_delete_instance(self):
        farm = self._create_farm()
        analysis = self._create_analysis()
        farm_polygon = self._create_farm_polygon(farm)

        instance = FarmRisk(
            farm_id=farm,
            analysis_id=analysis,
            farm_polygons_id=farm_polygon,
            deforestation=self._build_attributes(),
            protected=self._build_attributes(),
            farming_in=self._build_attributes(),
            farming_out=self._build_attributes(),
            risk_direct=True,
            risk_input=False,
            risk_output=True
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = FarmRisk.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()