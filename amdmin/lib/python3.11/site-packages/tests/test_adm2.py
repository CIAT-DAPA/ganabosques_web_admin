import unittest
from datetime import datetime

import mongomock
from mongoengine import connect, disconnect, ValidationError

from ganabosques_orm.collections.adm1 import Adm1
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.auxiliaries.log import Log


class TestAdm2(unittest.TestCase):

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
        Adm2.drop_collection()
        Adm1.drop_collection()

    def test_create_instance(self):
        instance = Adm2()
        self.assertIsInstance(instance, Adm2)

    def test_collection_name_is_adm2(self):
        self.assertEqual(Adm2._get_collection_name(), 'adm2')

    def test_create_instance_with_valid_data(self):
        adm1 = Adm1(name='Cundinamarca', ext_id='ADM1-001', ugg_size=100.0).save()

        instance = Adm2(
            adm1_id=adm1,
            name='Bogota',
            ext_id='ADM2-001'
        )

        self.assertEqual(instance.adm1_id, adm1)
        self.assertEqual(instance.name, 'Bogota')
        self.assertEqual(instance.ext_id, 'ADM2-001')
        self.assertIsNone(instance.log)

    def test_save_instance_with_reference_to_adm1(self):
        adm1 = Adm1(name='Antioquia', ext_id='ADM1-002', ugg_size=200.0).save()

        instance = Adm2(
            adm1_id=adm1,
            name='Medellin',
            ext_id='ADM2-002'
        )
        instance.save()

        saved = Adm2.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNotNone(saved.adm1_id)
        self.assertEqual(saved.adm1_id.id, adm1.id)
        self.assertEqual(saved.name, 'Medellin')
        self.assertEqual(saved.ext_id, 'ADM2-002')

    def test_save_instance_with_log_embedded_document(self):
        adm1 = Adm1(name='Valle del Cauca', ext_id='ADM1-003', ugg_size=50.0).save()
        log = Log(
            enable=True,
            created=datetime(2024, 1, 1, 10, 0, 0),
            updated=datetime(2024, 1, 2, 12, 0, 0)
        )

        instance = Adm2(
            adm1_id=adm1,
            name='Cali',
            ext_id='ADM2-003',
            log=log
        )
        instance.save()

        saved = Adm2.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsInstance(saved.log, Log)
        self.assertTrue(saved.log.enable)
        self.assertEqual(saved.log.created, datetime(2024, 1, 1, 10, 0, 0))
        self.assertEqual(saved.log.updated, datetime(2024, 1, 2, 12, 0, 0))

    def test_save_instance_with_empty_fields(self):
        instance = Adm2()
        instance.save()

        saved = Adm2.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNone(saved.adm1_id)
        self.assertIsNone(saved.name)
        self.assertIsNone(saved.ext_id)
        self.assertIsNone(saved.log)

    def test_create_instance_with_invalid_log_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            Adm2(log='invalid_log')

    def test_save_instance_with_valid_adm1_reference(self):
        adm1 = Adm1(
            name='Santander',
            ext_id='ADM1-006',
            ugg_size=44.0
        )
        adm1.save()

        instance = Adm2(
            adm1_id=adm1,
            name='Bucaramanga',
            ext_id='ADM2-006'
        )
        instance.save()

        saved = Adm2.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNotNone(saved.adm1_id)
        self.assertEqual(saved.adm1_id.id, adm1.id)
        self.assertEqual(saved.name, 'Bucaramanga')
        self.assertEqual(saved.ext_id, 'ADM2-006')

    def test_update_persisted_instance(self):
        adm1 = Adm1(name='Meta', ext_id='ADM1-004', ugg_size=10.0).save()
        instance = Adm2(
            adm1_id=adm1,
            name='Villavicencio',
            ext_id='ADM2-004'
        )
        instance.save()

        instance.name = 'Villavicencio Actualizado'
        instance.ext_id = 'ADM2-004-UPD'
        instance.save()

        updated = Adm2.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, 'Villavicencio Actualizado')
        self.assertEqual(updated.ext_id, 'ADM2-004-UPD')
        self.assertEqual(updated.adm1_id.id, adm1.id)

    def test_delete_instance(self):
        adm1 = Adm1(name='Tolima', ext_id='ADM1-005', ugg_size=30.0).save()
        instance = Adm2(
            adm1_id=adm1,
            name='Ibague',
            ext_id='ADM2-005'
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = Adm2.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()