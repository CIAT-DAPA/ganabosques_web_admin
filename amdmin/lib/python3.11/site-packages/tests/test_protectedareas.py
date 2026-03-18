import unittest
from datetime import datetime

import mongomock
from mongoengine import connect, disconnect

from ganabosques_orm.collections.protectedareas import ProtectedAreas
from ganabosques_orm.auxiliaries.log import Log


class TestProtectedAreas(unittest.TestCase):

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
        ProtectedAreas.drop_collection()

    def test_create_instance(self):
        instance = ProtectedAreas()
        self.assertIsInstance(instance, ProtectedAreas)

    def test_collection_name_is_protectedareas(self):
        self.assertEqual(ProtectedAreas._get_collection_name(), 'protectedareas')

    def test_create_instance_with_valid_data(self):
        instance = ProtectedAreas(
            name='Parque Nacional Natural',
            path='/data/protected/parque_nacional.geojson'
        )

        self.assertEqual(instance.name, 'Parque Nacional Natural')
        self.assertEqual(instance.path, '/data/protected/parque_nacional.geojson')
        self.assertIsNone(instance.log)

    def test_save_instance_with_valid_data(self):
        instance = ProtectedAreas(
            name='Reserva Forestal',
            path='/data/protected/reserva_forestal.shp'
        )
        instance.save()

        saved = ProtectedAreas.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.name, 'Reserva Forestal')
        self.assertEqual(saved.path, '/data/protected/reserva_forestal.shp')
        self.assertIsNone(saved.log)

    def test_save_instance_with_log_embedded_document(self):
        log = Log(
            enable=True,
            created=datetime(2024, 1, 1, 10, 0, 0),
            updated=datetime(2024, 1, 2, 12, 0, 0)
        )

        instance = ProtectedAreas(
            name='Zona de Conservacion',
            path='/data/protected/conservacion.kml',
            log=log
        )
        instance.save()

        saved = ProtectedAreas.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsInstance(saved.log, Log)
        self.assertTrue(saved.log.enable)
        self.assertEqual(saved.log.created, datetime(2024, 1, 1, 10, 0, 0))
        self.assertEqual(saved.log.updated, datetime(2024, 1, 2, 12, 0, 0))

    def test_save_instance_with_empty_fields(self):
        instance = ProtectedAreas()
        instance.save()

        saved = ProtectedAreas.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNone(saved.name)
        self.assertIsNone(saved.path)
        self.assertIsNone(saved.log)

    def test_create_instance_with_invalid_log_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            ProtectedAreas(log='invalid_log')

    def test_update_persisted_instance(self):
        instance = ProtectedAreas(
            name='Area Protegida Inicial',
            path='/data/protected/area_inicial.geojson'
        )
        instance.save()

        instance.name = 'Area Protegida Actualizada'
        instance.path = '/data/protected/area_actualizada.geojson'
        instance.save()

        updated = ProtectedAreas.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, 'Area Protegida Actualizada')
        self.assertEqual(updated.path, '/data/protected/area_actualizada.geojson')

    def test_delete_instance(self):
        instance = ProtectedAreas(
            name='Humedal Protegido',
            path='/data/protected/humedal.geojson'
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = ProtectedAreas.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()