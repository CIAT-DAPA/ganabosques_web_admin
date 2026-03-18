import unittest
from datetime import datetime

import mongomock
from mongoengine import connect, disconnect

from ganabosques_orm.collections.farmingareas import FarmingAreas
from ganabosques_orm.auxiliaries.log import Log


class TestFarmingAreas(unittest.TestCase):

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
        FarmingAreas.drop_collection()

    def test_create_instance(self):
        instance = FarmingAreas()
        self.assertIsInstance(instance, FarmingAreas)

    def test_collection_name_is_farmingareas(self):
        self.assertEqual(FarmingAreas._get_collection_name(), 'farmingareas')

    def test_create_instance_with_valid_data(self):
        instance = FarmingAreas(
            name='Area Norte',
            path='/tmp/areas/area_norte.geojson'
        )

        self.assertEqual(instance.name, 'Area Norte')
        self.assertEqual(instance.path, '/tmp/areas/area_norte.geojson')
        self.assertIsNone(instance.log)

    def test_save_instance_with_valid_data(self):
        instance = FarmingAreas(
            name='Area Centro',
            path='/data/farming/centro.shp'
        )
        instance.save()

        saved = FarmingAreas.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.name, 'Area Centro')
        self.assertEqual(saved.path, '/data/farming/centro.shp')
        self.assertIsNone(saved.log)

    def test_save_instance_with_log_embedded_document(self):
        log = Log(
            enable=True,
            created=datetime(2024, 1, 1, 10, 0, 0),
            updated=datetime(2024, 1, 2, 12, 0, 0)
        )

        instance = FarmingAreas(
            name='Area Sur',
            path='/data/farming/sur.kml',
            log=log
        )
        instance.save()

        saved = FarmingAreas.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsInstance(saved.log, Log)
        self.assertTrue(saved.log.enable)
        self.assertEqual(saved.log.created, datetime(2024, 1, 1, 10, 0, 0))
        self.assertEqual(saved.log.updated, datetime(2024, 1, 2, 12, 0, 0))

    def test_save_instance_with_empty_fields(self):
        instance = FarmingAreas()
        instance.save()

        saved = FarmingAreas.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNone(saved.name)
        self.assertIsNone(saved.path)
        self.assertIsNone(saved.log)

    def test_create_instance_with_invalid_log_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            FarmingAreas(log='invalid_log')

    def test_update_persisted_instance(self):
        instance = FarmingAreas(
            name='Area Occidente',
            path='/data/farming/occidente.geojson'
        )
        instance.save()

        instance.name = 'Area Occidente Actualizada'
        instance.path = '/data/farming/occidente_v2.geojson'
        instance.save()

        updated = FarmingAreas.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, 'Area Occidente Actualizada')
        self.assertEqual(updated.path, '/data/farming/occidente_v2.geojson')

    def test_delete_instance(self):
        instance = FarmingAreas(
            name='Area Oriente',
            path='/data/farming/oriente.geojson'
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = FarmingAreas.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()