import unittest
from datetime import datetime

import mongomock
from mongoengine import connect, disconnect

from ganabosques_orm.collections.adm1 import Adm1
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.collections.adm3 import Adm3
from ganabosques_orm.collections.farm import Farm
from ganabosques_orm.auxiliaries.log import Log
from ganabosques_orm.auxiliaries.extidfarm import ExtIdFarm
from ganabosques_orm.tools.exceptiondata import ExceptionData
from ganabosques_orm.enums.farmsource import FarmSource
from ganabosques_orm.enums.valuechain import ValueChain


class TestFarm(unittest.TestCase):

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
        Farm.drop_collection()
        Adm3.drop_collection()
        Adm2.drop_collection()
        Adm1.drop_collection()

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

    def _get_farm_source(self):
        return list(FarmSource)[0]

    def _get_value_chain(self):
        return list(ValueChain)[0]

    def _build_valid_ext_id(self):
        return [ExtIdFarm()]

    def test_create_instance(self):
        instance = Farm()
        self.assertIsInstance(instance, Farm)

    def test_collection_name_is_farm(self):
        self.assertEqual(Farm._get_collection_name(), 'farm')

    def test_create_instance_with_valid_data(self):
        adm3 = self._create_adm3()
        farm_source = self._get_farm_source()
        value_chain = self._get_value_chain()
        ext_id = self._build_valid_ext_id()

        instance = Farm(
            adm3_id=adm3,
            ext_id=ext_id,
            farm_source=farm_source,
            value_chain=value_chain
        )

        self.assertEqual(instance.adm3_id, adm3)
        self.assertEqual(instance.farm_source, farm_source)
        self.assertEqual(instance.value_chain, value_chain)
        self.assertEqual(len(instance.ext_id), 1)
        self.assertIsInstance(instance.ext_id[0], ExtIdFarm)
        self.assertIsNone(instance.log)

    def test_validate_returns_true_when_required_fields_are_present(self):
        instance = Farm(
            adm3_id=self._create_adm3(),
            ext_id=self._build_valid_ext_id(),
            farm_source=self._get_farm_source()
        )

        result = instance.validate()

        self.assertTrue(result)

    def test_validate_raises_exceptiondata_when_adm3_id_is_missing(self):
        instance = Farm(
            ext_id=self._build_valid_ext_id(),
            farm_source=self._get_farm_source()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.validate()

        self.assertEqual(str(context.exception), 'adm3_id is required')

    def test_validate_raises_exceptiondata_when_farm_source_is_missing(self):
        instance = Farm(
            adm3_id=self._create_adm3(),
            ext_id=self._build_valid_ext_id()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.validate()

        self.assertEqual(str(context.exception), 'farm_source is required')

    def test_validate_raises_exceptiondata_when_ext_id_is_missing(self):
        instance = Farm(
            adm3_id=self._create_adm3(),
            farm_source=self._get_farm_source()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.validate()

        self.assertEqual(
            str(context.exception),
            'ext_id must contain at least one entry'
        )

    def test_validate_raises_exceptiondata_when_ext_id_is_empty(self):
        instance = Farm(
            adm3_id=self._create_adm3(),
            ext_id=[],
            farm_source=self._get_farm_source()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.validate()

        self.assertEqual(
            str(context.exception),
            'ext_id must contain at least one entry'
        )

    def test_save_instance_with_valid_data(self):
        adm3 = self._create_adm3()
        farm_source = self._get_farm_source()
        value_chain = self._get_value_chain()
        ext_id = self._build_valid_ext_id()

        instance = Farm(
            adm3_id=adm3,
            ext_id=ext_id,
            farm_source=farm_source,
            value_chain=value_chain
        )
        instance.save()

        saved = Farm.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.adm3_id.id, adm3.id)
        self.assertEqual(saved.farm_source, farm_source)
        self.assertEqual(saved.value_chain, value_chain)
        self.assertEqual(len(saved.ext_id), 1)
        self.assertIsInstance(saved.ext_id[0], ExtIdFarm)

    def test_save_instance_with_log_embedded_document(self):
        adm3 = self._create_adm3()
        farm_source = self._get_farm_source()
        log = Log(
            enable=True,
            created=datetime(2024, 1, 1, 10, 0, 0),
            updated=datetime(2024, 1, 2, 12, 0, 0)
        )

        instance = Farm(
            adm3_id=adm3,
            ext_id=self._build_valid_ext_id(),
            farm_source=farm_source,
            log=log
        )
        instance.save()

        saved = Farm.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsInstance(saved.log, Log)
        self.assertTrue(saved.log.enable)
        self.assertEqual(saved.log.created, datetime(2024, 1, 1, 10, 0, 0))
        self.assertEqual(saved.log.updated, datetime(2024, 1, 2, 12, 0, 0))

    def test_save_raises_exceptiondata_when_adm3_id_is_missing(self):
        instance = Farm(
            ext_id=self._build_valid_ext_id(),
            farm_source=self._get_farm_source()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.save()

        self.assertEqual(str(context.exception), 'adm3_id is required')

    def test_save_raises_exceptiondata_when_farm_source_is_missing(self):
        instance = Farm(
            adm3_id=self._create_adm3(),
            ext_id=self._build_valid_ext_id()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.save()

        self.assertEqual(str(context.exception), 'farm_source is required')

    def test_save_raises_exceptiondata_when_ext_id_is_empty(self):
        instance = Farm(
            adm3_id=self._create_adm3(),
            ext_id=[],
            farm_source=self._get_farm_source()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.save()

        self.assertEqual(
            str(context.exception),
            'ext_id must contain at least one entry'
        )

    def test_create_instance_with_invalid_log_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            Farm(log='invalid_log')

    def test_update_persisted_instance(self):
        instance = Farm(
            adm3_id=self._create_adm3(),
            ext_id=self._build_valid_ext_id(),
            farm_source=self._get_farm_source()
        )
        instance.save()

        instance.value_chain = self._get_value_chain()
        instance.save()

        updated = Farm.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(len(updated.ext_id), 1)
        self.assertEqual(updated.farm_source, self._get_farm_source())
        self.assertEqual(updated.value_chain, self._get_value_chain())

    def test_delete_instance(self):
        instance = Farm(
            adm3_id=self._create_adm3(),
            ext_id=self._build_valid_ext_id(),
            farm_source=self._get_farm_source()
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = Farm.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()