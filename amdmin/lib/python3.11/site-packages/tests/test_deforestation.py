import unittest
from datetime import datetime

import mongomock
from mongoengine import connect, disconnect, ValidationError

from ganabosques_orm.collections.deforestation import Deforestation
from ganabosques_orm.auxiliaries.log import Log
from ganabosques_orm.enums.deforestationtype import DeforestationType
from ganabosques_orm.enums.deforestationsource import DeforestationSource


class TestDeforestation(unittest.TestCase):

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
        Deforestation.drop_collection()

    def _get_enum_member(self, enum_cls):
        return list(enum_cls)[0]

    def test_create_instance(self):
        instance = Deforestation()
        self.assertIsInstance(instance, Deforestation)

    def test_collection_name_is_deforestation(self):
        self.assertEqual(Deforestation._get_collection_name(), 'deforestation')

    def test_create_instance_with_valid_data(self):
        source = self._get_enum_member(DeforestationSource)
        dtype = self._get_enum_member(DeforestationType)
        period_start = datetime(2024, 1, 1, 0, 0, 0)
        period_end = datetime(2024, 12, 31, 23, 59, 59)

        instance = Deforestation(
            deforestation_source=source,
            deforestation_type=dtype,
            name='Deforestacion Amazonia 2024',
            period_start=period_start,
            period_end=period_end,
            path='/data/deforestation/amazonia_2024.tif'
        )

        self.assertEqual(instance.deforestation_source, source)
        self.assertEqual(instance.deforestation_type, dtype)
        self.assertEqual(instance.name, 'Deforestacion Amazonia 2024')
        self.assertEqual(instance.period_start, period_start)
        self.assertEqual(instance.period_end, period_end)
        self.assertEqual(instance.path, '/data/deforestation/amazonia_2024.tif')
        self.assertIsNone(instance.log)

    def test_save_instance_with_valid_data(self):
        source = self._get_enum_member(DeforestationSource)
        dtype = self._get_enum_member(DeforestationType)

        instance = Deforestation(
            deforestation_source=source,
            deforestation_type=dtype,
            name='Deforestacion Orinoquia',
            period_start=datetime(2023, 1, 1, 0, 0, 0),
            period_end=datetime(2023, 6, 30, 23, 59, 59),
            path='/data/deforestation/orinoquia_2023.geojson'
        )
        instance.save()

        saved = Deforestation.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.deforestation_source, source)
        self.assertEqual(saved.deforestation_type, dtype)
        self.assertEqual(saved.name, 'Deforestacion Orinoquia')
        self.assertEqual(saved.period_start, datetime(2023, 1, 1, 0, 0, 0))
        self.assertEqual(saved.period_end, datetime(2023, 6, 30, 23, 59, 59))
        self.assertEqual(saved.path, '/data/deforestation/orinoquia_2023.geojson')

    def test_save_instance_with_log_embedded_document(self):
        source = self._get_enum_member(DeforestationSource)
        dtype = self._get_enum_member(DeforestationType)
        log = Log(
            enable=True,
            created=datetime(2024, 1, 1, 10, 0, 0),
            updated=datetime(2024, 1, 2, 12, 0, 0)
        )

        instance = Deforestation(
            deforestation_source=source,
            deforestation_type=dtype,
            name='Deforestacion Caribe',
            period_start=datetime(2022, 1, 1, 0, 0, 0),
            period_end=datetime(2022, 12, 31, 23, 59, 59),
            path='/data/deforestation/caribe_2022.shp',
            log=log
        )
        instance.save()

        saved = Deforestation.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsInstance(saved.log, Log)
        self.assertTrue(saved.log.enable)
        self.assertEqual(saved.log.created, datetime(2024, 1, 1, 10, 0, 0))
        self.assertEqual(saved.log.updated, datetime(2024, 1, 2, 12, 0, 0))

    def test_save_instance_with_empty_fields(self):
        instance = Deforestation()
        instance.save()

        saved = Deforestation.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNone(saved.deforestation_source)
        self.assertIsNone(saved.deforestation_type)
        self.assertIsNone(saved.name)
        self.assertIsNone(saved.period_start)
        self.assertIsNone(saved.period_end)
        self.assertIsNone(saved.path)
        self.assertIsNone(saved.log)

    def test_create_instance_with_invalid_log_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            Deforestation(log='invalid_log')

    def test_validate_invalid_deforestation_source_raises_validation_error(self):
        instance = Deforestation(deforestation_source='invalid_source')

        with self.assertRaises(ValidationError):
            instance.validate()

    def test_validate_invalid_deforestation_type_raises_validation_error(self):
        instance = Deforestation(deforestation_type='invalid_type')

        with self.assertRaises(ValidationError):
            instance.validate()

    def test_update_persisted_instance(self):
        source = self._get_enum_member(DeforestationSource)
        dtype = self._get_enum_member(DeforestationType)

        instance = Deforestation(
            deforestation_source=source,
            deforestation_type=dtype,
            name='Deforestacion Inicial',
            period_start=datetime(2021, 1, 1, 0, 0, 0),
            period_end=datetime(2021, 12, 31, 23, 59, 59),
            path='/data/deforestation/inicial.geojson'
        )
        instance.save()

        instance.name = 'Deforestacion Actualizada'
        instance.path = '/data/deforestation/actualizada.geojson'
        instance.period_end = datetime(2022, 1, 31, 23, 59, 59)
        instance.save()

        updated = Deforestation.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, 'Deforestacion Actualizada')
        self.assertEqual(updated.path, '/data/deforestation/actualizada.geojson')
        self.assertEqual(updated.period_end, datetime(2022, 1, 31, 23, 59, 59))
        self.assertEqual(updated.deforestation_source, source)
        self.assertEqual(updated.deforestation_type, dtype)

    def test_delete_instance(self):
        source = self._get_enum_member(DeforestationSource)
        dtype = self._get_enum_member(DeforestationType)

        instance = Deforestation(
            deforestation_source=source,
            deforestation_type=dtype,
            name='Deforestacion a eliminar',
            path='/data/deforestation/delete.geojson'
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = Deforestation.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()