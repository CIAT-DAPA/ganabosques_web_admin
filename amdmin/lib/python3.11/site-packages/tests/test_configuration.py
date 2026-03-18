import unittest
from datetime import datetime

import mongomock
from mongoengine import connect, disconnect

from ganabosques_orm.collections.configuration import Configuration
from ganabosques_orm.auxiliaries.log import Log
from ganabosques_orm.auxiliaries.parameters import Parameters


class TestConfiguration(unittest.TestCase):

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
        Configuration.drop_collection()

    def test_create_instance(self):
        instance = Configuration()
        self.assertIsInstance(instance, Configuration)

    def test_collection_name_is_configuration(self):
        self.assertEqual(Configuration._get_collection_name(), 'configuration')

    def test_create_instance_with_valid_data(self):
        parameters = [
            Parameters(key='buffer_distance', value='100'),
            Parameters(key='risk_level', value='high')
        ]

        instance = Configuration(
            name='Configuracion General',
            parameters=parameters
        )

        self.assertEqual(instance.name, 'Configuracion General')
        self.assertEqual(len(instance.parameters), 2)
        self.assertEqual(instance.parameters[0].key, 'buffer_distance')
        self.assertEqual(instance.parameters[0].value, '100')
        self.assertEqual(instance.parameters[1].key, 'risk_level')
        self.assertEqual(instance.parameters[1].value, 'high')
        self.assertIsNone(instance.log)

    def test_save_instance_with_valid_data(self):
        parameters = [
            Parameters(key='pixel_size', value='30'),
            Parameters(key='source', value='ideam')
        ]

        instance = Configuration(
            name='Configuracion Inicial',
            parameters=parameters
        )
        instance.save()

        saved = Configuration.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.name, 'Configuracion Inicial')
        self.assertEqual(len(saved.parameters), 2)
        self.assertEqual(saved.parameters[0].key, 'pixel_size')
        self.assertEqual(saved.parameters[0].value, '30')
        self.assertEqual(saved.parameters[1].key, 'source')
        self.assertEqual(saved.parameters[1].value, 'ideam')
        self.assertIsNone(saved.log)

    def test_save_instance_with_log_embedded_document(self):
        log = Log(
            enable=True,
            created=datetime(2024, 1, 1, 10, 0, 0),
            updated=datetime(2024, 1, 2, 12, 0, 0)
        )

        parameters = [
            Parameters(key='threshold', value='0.75')
        ]

        instance = Configuration(
            name='Configuracion con Log',
            parameters=parameters,
            log=log
        )
        instance.save()

        saved = Configuration.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.name, 'Configuracion con Log')
        self.assertEqual(len(saved.parameters), 1)
        self.assertEqual(saved.parameters[0].key, 'threshold')
        self.assertEqual(saved.parameters[0].value, '0.75')
        self.assertIsInstance(saved.log, Log)
        self.assertTrue(saved.log.enable)
        self.assertEqual(saved.log.created, datetime(2024, 1, 1, 10, 0, 0))
        self.assertEqual(saved.log.updated, datetime(2024, 1, 2, 12, 0, 0))

    def test_save_instance_with_empty_fields(self):
        instance = Configuration()
        instance.save()

        saved = Configuration.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNone(saved.name)
        self.assertEqual(list(saved.parameters), [])
        self.assertIsNone(saved.log)

    def test_create_instance_with_invalid_log_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            Configuration(log='invalid_log')

    def test_create_instance_with_invalid_parameters_item_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            Configuration(
                parameters=['invalid_parameter']
            )

    def test_update_persisted_instance(self):
        instance = Configuration(
            name='Configuracion Base',
            parameters=[
                Parameters(key='mode', value='draft')
            ]
        )
        instance.save()

        instance.name = 'Configuracion Actualizada'
        instance.parameters = [
            Parameters(key='mode', value='production'),
            Parameters(key='region', value='colombia')
        ]
        instance.save()

        updated = Configuration.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, 'Configuracion Actualizada')
        self.assertEqual(len(updated.parameters), 2)
        self.assertEqual(updated.parameters[0].key, 'mode')
        self.assertEqual(updated.parameters[0].value, 'production')
        self.assertEqual(updated.parameters[1].key, 'region')
        self.assertEqual(updated.parameters[1].value, 'colombia')

    def test_delete_instance(self):
        instance = Configuration(
            name='Configuracion a Eliminar',
            parameters=[
                Parameters(key='status', value='inactive')
            ]
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = Configuration.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()