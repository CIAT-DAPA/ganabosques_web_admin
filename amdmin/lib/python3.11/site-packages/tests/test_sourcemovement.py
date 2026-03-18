import unittest
from datetime import datetime

import mongomock
from mongoengine import connect, disconnect

from ganabosques_orm.collections.sourcemovement import SourceMovement
from ganabosques_orm.auxiliaries.log import Log


class TestSourceMovement(unittest.TestCase):

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
        SourceMovement.drop_collection()

    def test_create_instance(self):
        instance = SourceMovement()
        self.assertIsInstance(instance, SourceMovement)

    def test_collection_name_is_sourcemovement(self):
        self.assertEqual(SourceMovement._get_collection_name(), 'sourcemovement')

    def test_create_instance_with_valid_data(self):
        instance = SourceMovement(
            name='ICA'
        )

        self.assertEqual(instance.name, 'ICA')
        self.assertIsNone(instance.log)

    def test_save_instance_with_valid_data(self):
        instance = SourceMovement(
            name='SIPSA'
        )
        instance.save()

        saved = SourceMovement.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.name, 'SIPSA')
        self.assertIsNone(saved.log)

    def test_save_instance_with_log_embedded_document(self):
        log = Log(
            enable=True,
            created=datetime(2024, 1, 1, 10, 0, 0),
            updated=datetime(2024, 1, 2, 12, 0, 0)
        )

        instance = SourceMovement(
            name='FEDEGAN',
            log=log
        )
        instance.save()

        saved = SourceMovement.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.name, 'FEDEGAN')
        self.assertIsInstance(saved.log, Log)
        self.assertTrue(saved.log.enable)
        self.assertEqual(saved.log.created, datetime(2024, 1, 1, 10, 0, 0))
        self.assertEqual(saved.log.updated, datetime(2024, 1, 2, 12, 0, 0))

    def test_save_instance_with_empty_fields(self):
        instance = SourceMovement()
        instance.save()

        saved = SourceMovement.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNone(saved.name)
        self.assertIsNone(saved.log)

    def test_create_instance_with_invalid_log_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            SourceMovement(log='invalid_log')

    def test_update_persisted_instance(self):
        instance = SourceMovement(
            name='Origen Inicial'
        )
        instance.save()

        instance.name = 'Origen Actualizado'
        instance.save()

        updated = SourceMovement.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, 'Origen Actualizado')

    def test_delete_instance(self):
        instance = SourceMovement(
            name='Origen a Eliminar'
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = SourceMovement.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()