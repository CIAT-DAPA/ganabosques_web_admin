import unittest
from datetime import datetime

import mongomock
from mongoengine import connect, disconnect, ValidationError

from ganabosques_orm.collections.adm1 import Adm1
from ganabosques_orm.auxiliaries.log import Log


class TestAdm1(unittest.TestCase):

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
        Adm1.drop_collection()

    def test_create_instance(self):
        instance = Adm1()
        self.assertIsInstance(instance, Adm1)

    def test_collection_name_is_adm1(self):
        self.assertEqual(Adm1._get_collection_name(), 'adm1')

    def test_create_instance_with_valid_data(self):
        instance = Adm1(
            name='Cundinamarca',
            ext_id='ADM1-001',
            ugg_size=123.45
        )

        self.assertEqual(instance.name, 'Cundinamarca')
        self.assertEqual(instance.ext_id, 'ADM1-001')
        self.assertEqual(instance.ugg_size, 123.45)
        self.assertIsNone(instance.log)

    def test_save_instance_with_valid_data(self):
        instance = Adm1(
            name='Antioquia',
            ext_id='ADM1-002',
            ugg_size=87.5
        )
        instance.save()

        saved = Adm1.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.name, 'Antioquia')
        self.assertEqual(saved.ext_id, 'ADM1-002')
        self.assertEqual(saved.ugg_size, 87.5)
        self.assertIsNone(saved.log)

    def test_save_instance_with_log_embedded_document(self):
        log = Log(
            enable=True,
            created=datetime(2024, 1, 1, 10, 0, 0),
            updated=datetime(2024, 1, 2, 12, 0, 0)
        )

        instance = Adm1(
            name='Valle del Cauca',
            ext_id='ADM1-003',
            ugg_size=50.0,
            log=log
        )
        instance.save()

        saved = Adm1.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsInstance(saved.log, Log)
        self.assertTrue(saved.log.enable)
        self.assertEqual(saved.log.created, datetime(2024, 1, 1, 10, 0, 0))
        self.assertEqual(saved.log.updated, datetime(2024, 1, 2, 12, 0, 0))

    def test_save_instance_with_empty_fields(self):
        instance = Adm1()
        instance.save()

        saved = Adm1.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNone(saved.name)
        self.assertIsNone(saved.ext_id)
        self.assertIsNone(saved.ugg_size)
        self.assertIsNone(saved.log)

    def test_validate_invalid_ugg_size_type_raises_error(self):
        instance = Adm1(ugg_size='invalid_float')

        with self.assertRaises(ValidationError):
            instance.validate()

    def test_create_instance_with_invalid_log_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            Adm1(log='invalid_log')

    def test_update_persisted_instance(self):
        instance = Adm1(
            name='Meta',
            ext_id='ADM1-004',
            ugg_size=10.0
        )
        instance.save()

        instance.name = 'Meta Actualizado'
        instance.ugg_size = 20.5
        instance.save()

        updated = Adm1.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, 'Meta Actualizado')
        self.assertEqual(updated.ext_id, 'ADM1-004')
        self.assertEqual(updated.ugg_size, 20.5)

    def test_delete_instance(self):
        instance = Adm1(
            name='Tolima',
            ext_id='ADM1-005',
            ugg_size=30.0
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = Adm1.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()