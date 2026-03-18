import unittest
from datetime import datetime

import mongomock
from mongoengine import connect, disconnect

from ganabosques_orm.collections.adm1 import Adm1
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.collections.adm3 import Adm3
from ganabosques_orm.auxiliaries.log import Log


class TestAdm3(unittest.TestCase):

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
        Adm3.drop_collection()
        Adm2.drop_collection()
        Adm1.drop_collection()

    def _create_adm2(self):
        adm1 = Adm1(
            name='Cundinamarca',
            ext_id='ADM1-001',
            ugg_size=100.0
        ).save()

        adm2 = Adm2(
            adm1_id=adm1,
            name='Bogota',
            ext_id='ADM2-001'
        ).save()

        return adm2

    def test_create_instance(self):
        instance = Adm3()
        self.assertIsInstance(instance, Adm3)

    def test_collection_name_is_adm3(self):
        self.assertEqual(Adm3._get_collection_name(), 'adm3')

    def test_create_instance_with_valid_data(self):
        adm2 = self._create_adm2()

        instance = Adm3(
            adm2_id=adm2,
            name='Usaquen',
            ext_id='ADM3-001',
            label='Localidad'
        )

        self.assertEqual(instance.adm2_id, adm2)
        self.assertEqual(instance.name, 'Usaquen')
        self.assertEqual(instance.ext_id, 'ADM3-001')
        self.assertEqual(instance.label, 'Localidad')
        self.assertIsNone(instance.log)

    def test_save_instance_with_valid_reference(self):
        adm2 = self._create_adm2()

        instance = Adm3(
            adm2_id=adm2,
            name='Chapinero',
            ext_id='ADM3-002',
            label='Zona urbana'
        )
        instance.save()

        saved = Adm3.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNotNone(saved.adm2_id)
        self.assertEqual(saved.adm2_id.id, adm2.id)
        self.assertEqual(saved.name, 'Chapinero')
        self.assertEqual(saved.ext_id, 'ADM3-002')
        self.assertEqual(saved.label, 'Zona urbana')

    def test_save_instance_with_log_embedded_document(self):
        adm2 = self._create_adm2()
        log = Log(
            enable=True,
            created=datetime(2024, 1, 1, 10, 0, 0),
            updated=datetime(2024, 1, 2, 12, 0, 0)
        )

        instance = Adm3(
            adm2_id=adm2,
            name='Suba',
            ext_id='ADM3-003',
            label='Sector',
            log=log
        )
        instance.save()

        saved = Adm3.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsInstance(saved.log, Log)
        self.assertTrue(saved.log.enable)
        self.assertEqual(saved.log.created, datetime(2024, 1, 1, 10, 0, 0))
        self.assertEqual(saved.log.updated, datetime(2024, 1, 2, 12, 0, 0))

    def test_save_instance_with_empty_fields(self):
        instance = Adm3()
        instance.save()

        saved = Adm3.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNone(saved.adm2_id)
        self.assertIsNone(saved.name)
        self.assertIsNone(saved.ext_id)
        self.assertIsNone(saved.label)
        self.assertIsNone(saved.log)

    def test_create_instance_with_invalid_log_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            Adm3(log='invalid_log')

    def test_update_persisted_instance(self):
        adm2 = self._create_adm2()

        instance = Adm3(
            adm2_id=adm2,
            name='Kennedy',
            ext_id='ADM3-004',
            label='Localidad inicial'
        )
        instance.save()

        instance.name = 'Kennedy Actualizado'
        instance.ext_id = 'ADM3-004-UPD'
        instance.label = 'Localidad actualizada'
        instance.save()

        updated = Adm3.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.adm2_id.id, adm2.id)
        self.assertEqual(updated.name, 'Kennedy Actualizado')
        self.assertEqual(updated.ext_id, 'ADM3-004-UPD')
        self.assertEqual(updated.label, 'Localidad actualizada')

    def test_delete_instance(self):
        adm2 = self._create_adm2()

        instance = Adm3(
            adm2_id=adm2,
            name='Engativa',
            ext_id='ADM3-005',
            label='Zona'
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = Adm3.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()