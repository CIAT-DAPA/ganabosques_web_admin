import unittest
from datetime import datetime

import mongomock
from mongoengine import connect, disconnect

from ganabosques_orm.collections.adm1 import Adm1
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.collections.adm3 import Adm3
from ganabosques_orm.collections.farm import Farm
from ganabosques_orm.collections.farmpolygons import FarmPolygons
from ganabosques_orm.auxiliaries.bufferpolygon import BufferPolygon
from ganabosques_orm.auxiliaries.extidfarm import ExtIdFarm
from ganabosques_orm.auxiliaries.log import Log
from ganabosques_orm.enums.farmsource import FarmSource


class TestFarmPolygons(unittest.TestCase):

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
        FarmPolygons.drop_collection()
        Farm.drop_collection()
        Adm3.drop_collection()
        Adm2.drop_collection()
        Adm1.drop_collection()

    def _get_farm_source(self):
        return list(FarmSource)[0]

    def _create_farm(self):
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

        farm = Farm(
            adm3_id=adm3,
            ext_id=[ExtIdFarm()],
            farm_source=self._get_farm_source()
        )
        farm.save()

        return farm

    def _build_buffer_inputs(self):
        return [BufferPolygon()]

    def test_create_instance(self):
        instance = FarmPolygons()
        self.assertIsInstance(instance, FarmPolygons)

    def test_collection_name_is_farmpolygons(self):
        self.assertEqual(FarmPolygons._get_collection_name(), 'farmpolygons')

    def test_create_instance_with_valid_data(self):
        farm = self._create_farm()
        buffer_inputs = self._build_buffer_inputs()

        instance = FarmPolygons(
            farm_id=farm,
            geojson='{"type":"Polygon","coordinates":[]}',
            latitude=4.7110,
            longitud=-74.0721,
            farm_ha=25.5,
            radio=150.0,
            buffer_inputs=buffer_inputs
        )

        self.assertEqual(instance.farm_id, farm)
        self.assertEqual(instance.geojson, '{"type":"Polygon","coordinates":[]}')
        self.assertEqual(instance.latitude, 4.7110)
        self.assertEqual(instance.longitud, -74.0721)
        self.assertEqual(instance.farm_ha, 25.5)
        self.assertEqual(instance.radio, 150.0)
        self.assertEqual(len(instance.buffer_inputs), 1)
        self.assertIsInstance(instance.buffer_inputs[0], BufferPolygon)
        self.assertIsNone(instance.log)

    def test_save_instance_with_valid_data(self):
        farm = self._create_farm()
        buffer_inputs = self._build_buffer_inputs()

        instance = FarmPolygons(
            farm_id=farm,
            geojson='{"type":"Polygon","coordinates":[[[-74.0,4.7],[-74.1,4.8]]]}',
            latitude=4.7,
            longitud=-74.1,
            farm_ha=10.75,
            radio=50.0,
            buffer_inputs=buffer_inputs
        )
        instance.save()

        saved = FarmPolygons.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.farm_id.id, farm.id)
        self.assertEqual(
            saved.geojson,
            '{"type":"Polygon","coordinates":[[[-74.0,4.7],[-74.1,4.8]]]}'
        )
        self.assertEqual(saved.latitude, 4.7)
        self.assertEqual(saved.longitud, -74.1)
        self.assertEqual(saved.farm_ha, 10.75)
        self.assertEqual(saved.radio, 50.0)
        self.assertEqual(len(saved.buffer_inputs), 1)
        self.assertIsInstance(saved.buffer_inputs[0], BufferPolygon)
        self.assertIsNone(saved.log)

    def test_save_instance_with_log_embedded_document(self):
        farm = self._create_farm()
        log = Log(
            enable=True,
            created=datetime(2024, 1, 1, 10, 0, 0),
            updated=datetime(2024, 1, 2, 12, 0, 0)
        )

        instance = FarmPolygons(
            farm_id=farm,
            geojson='{"type":"Polygon","coordinates":[]}',
            latitude=5.0,
            longitud=-73.9,
            farm_ha=30.0,
            radio=80.0,
            buffer_inputs=self._build_buffer_inputs(),
            log=log
        )
        instance.save()

        saved = FarmPolygons.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.farm_id.id, farm.id)
        self.assertIsInstance(saved.log, Log)
        self.assertTrue(saved.log.enable)
        self.assertEqual(saved.log.created, datetime(2024, 1, 1, 10, 0, 0))
        self.assertEqual(saved.log.updated, datetime(2024, 1, 2, 12, 0, 0))

    def test_save_instance_with_empty_fields(self):
        instance = FarmPolygons()
        instance.save()

        saved = FarmPolygons.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNone(saved.farm_id)
        self.assertIsNone(saved.geojson)
        self.assertIsNone(saved.latitude)
        self.assertIsNone(saved.longitud)
        self.assertIsNone(saved.farm_ha)
        self.assertIsNone(saved.radio)
        self.assertEqual(list(saved.buffer_inputs), [])
        self.assertIsNone(saved.log)

    def test_create_instance_with_invalid_log_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            FarmPolygons(log='invalid_log')

    def test_create_instance_with_invalid_buffer_inputs_item_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            FarmPolygons(buffer_inputs=['invalid_buffer'])

    def test_update_persisted_instance(self):
        farm = self._create_farm()

        instance = FarmPolygons(
            farm_id=farm,
            geojson='{"type":"Polygon","coordinates":[]}',
            latitude=4.1,
            longitud=-73.1,
            farm_ha=12.0,
            radio=40.0,
            buffer_inputs=self._build_buffer_inputs()
        )
        instance.save()

        instance.geojson = '{"type":"Polygon","coordinates":[[[-73.0,4.0],[-73.2,4.2]]]}'
        instance.latitude = 4.2
        instance.longitud = -73.2
        instance.farm_ha = 18.5
        instance.radio = 60.0
        instance.buffer_inputs = [BufferPolygon(), BufferPolygon()]
        instance.save()

        updated = FarmPolygons.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.farm_id.id, farm.id)
        self.assertEqual(
            updated.geojson,
            '{"type":"Polygon","coordinates":[[[-73.0,4.0],[-73.2,4.2]]]}'
        )
        self.assertEqual(updated.latitude, 4.2)
        self.assertEqual(updated.longitud, -73.2)
        self.assertEqual(updated.farm_ha, 18.5)
        self.assertEqual(updated.radio, 60.0)
        self.assertEqual(len(updated.buffer_inputs), 2)
        self.assertIsInstance(updated.buffer_inputs[0], BufferPolygon)
        self.assertIsInstance(updated.buffer_inputs[1], BufferPolygon)

    def test_delete_instance(self):
        instance = FarmPolygons(
            farm_id=self._create_farm(),
            geojson='{"type":"Polygon","coordinates":[]}',
            latitude=4.5,
            longitud=-74.0,
            farm_ha=9.0,
            radio=25.0,
            buffer_inputs=self._build_buffer_inputs()
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = FarmPolygons.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()