import unittest
from datetime import datetime

import mongomock
from mongoengine import connect, disconnect

from ganabosques_orm.collections.adm1 import Adm1
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.collections.enterprise import Enterprise
from ganabosques_orm.auxiliaries.log import Log
from ganabosques_orm.tools.exceptiondata import ExceptionData
from ganabosques_orm.enums.typeenterprise import TypeEnterprise
from ganabosques_orm.enums.valuechain import ValueChain


class TestEnterprise(unittest.TestCase):

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
        Enterprise.drop_collection()
        Adm2.drop_collection()
        Adm1.drop_collection()

    def _create_adm2(self):
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

        return adm2

    def _get_type_enterprise(self):
        return list(TypeEnterprise)[0]

    def _get_value_chain(self):
        return list(ValueChain)[0]

    def test_create_instance(self):
        instance = Enterprise()
        self.assertIsInstance(instance, Enterprise)

    def test_collection_name_is_enterprise(self):
        self.assertEqual(Enterprise._get_collection_name(), 'enterprise')

    def test_create_instance_with_valid_data(self):
        adm2 = self._create_adm2()
        enterprise_type = self._get_type_enterprise()
        value_chain = self._get_value_chain()

        instance = Enterprise(
            adm2_id=adm2,
            name='Empresa Demo',
            type_enterprise=enterprise_type,
            latitude=4.7110,
            longitud=-74.0721,
            value_chain=value_chain
        )

        self.assertEqual(instance.adm2_id, adm2)
        self.assertEqual(instance.name, 'Empresa Demo')
        self.assertEqual(instance.type_enterprise, enterprise_type)
        self.assertEqual(instance.latitude, 4.7110)
        self.assertEqual(instance.longitud, -74.0721)
        self.assertEqual(instance.value_chain, value_chain)
        self.assertEqual(list(instance.ext_id), [])
        self.assertIsNone(instance.log)

    def test_validate_returns_true_when_required_fields_are_present(self):
        instance = Enterprise(
            name='Empresa Valida',
            type_enterprise=self._get_type_enterprise()
        )

        result = instance.validate()

        self.assertTrue(result)

    def test_validate_raises_exceptiondata_when_name_is_none(self):
        instance = Enterprise(
            type_enterprise=self._get_type_enterprise()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.validate()

        self.assertEqual(str(context.exception), 'Name field is mandatory')

    def test_validate_raises_exceptiondata_when_name_is_empty_string(self):
        instance = Enterprise(
            name='',
            type_enterprise=self._get_type_enterprise()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.validate()

        self.assertEqual(str(context.exception), 'Name field is mandatory')

    def test_validate_raises_exceptiondata_when_name_is_whitespace(self):
        instance = Enterprise(
            name='   ',
            type_enterprise=self._get_type_enterprise()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.validate()

        self.assertEqual(str(context.exception), 'Name field is mandatory')

    def test_validate_raises_exceptiondata_when_type_enterprise_is_missing(self):
        instance = Enterprise(
            name='Empresa Sin Tipo'
        )

        with self.assertRaises(ExceptionData) as context:
            instance.validate()

        self.assertEqual(str(context.exception), 'Type Enterprise field is mandatory')

    def test_save_instance_with_valid_data(self):
        adm2 = self._create_adm2()
        enterprise_type = self._get_type_enterprise()
        value_chain = self._get_value_chain()

        instance = Enterprise(
            adm2_id=adm2,
            name='Empresa Guardada',
            type_enterprise=enterprise_type,
            latitude=5.0001,
            longitud=-73.9999,
            value_chain=value_chain
        )
        instance.save()

        saved = Enterprise.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.adm2_id.id, adm2.id)
        self.assertEqual(saved.name, 'Empresa Guardada')
        self.assertEqual(saved.type_enterprise, enterprise_type)
        self.assertEqual(saved.latitude, 5.0001)
        self.assertEqual(saved.longitud, -73.9999)
        self.assertEqual(saved.value_chain, value_chain)

    def test_save_instance_with_log_embedded_document(self):
        adm2 = self._create_adm2()
        enterprise_type = self._get_type_enterprise()
        log = Log(
            enable=True,
            created=datetime(2024, 1, 1, 10, 0, 0),
            updated=datetime(2024, 1, 2, 12, 0, 0)
        )

        instance = Enterprise(
            adm2_id=adm2,
            name='Empresa con Log',
            type_enterprise=enterprise_type,
            latitude=4.5,
            longitud=-75.1,
            log=log
        )
        instance.save()

        saved = Enterprise.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsInstance(saved.log, Log)
        self.assertTrue(saved.log.enable)
        self.assertEqual(saved.log.created, datetime(2024, 1, 1, 10, 0, 0))
        self.assertEqual(saved.log.updated, datetime(2024, 1, 2, 12, 0, 0))

    def test_save_raises_exceptiondata_when_name_is_missing(self):
        instance = Enterprise(
            type_enterprise=self._get_type_enterprise()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.save()

        self.assertEqual(str(context.exception), 'Name field is mandatory')

    def test_save_raises_exceptiondata_when_type_enterprise_is_missing(self):
        instance = Enterprise(
            name='Empresa Sin Tipo'
        )

        with self.assertRaises(ExceptionData) as context:
            instance.save()

        self.assertEqual(str(context.exception), 'Type Enterprise field is mandatory')

    def test_create_instance_with_invalid_log_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            Enterprise(log='invalid_log')

    def test_update_persisted_instance(self):
        adm2 = self._create_adm2()
        enterprise_type = self._get_type_enterprise()

        instance = Enterprise(
            adm2_id=adm2,
            name='Empresa Inicial',
            type_enterprise=enterprise_type,
            latitude=1.0,
            longitud=-1.0
        )
        instance.save()

        instance.name = 'Empresa Actualizada'
        instance.latitude = 6.1234
        instance.longitud = -72.5678
        instance.value_chain = self._get_value_chain()
        instance.save()

        updated = Enterprise.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.adm2_id.id, adm2.id)
        self.assertEqual(updated.name, 'Empresa Actualizada')
        self.assertEqual(updated.latitude, 6.1234)
        self.assertEqual(updated.longitud, -72.5678)
        self.assertEqual(updated.value_chain, self._get_value_chain())

    def test_delete_instance(self):
        instance = Enterprise(
            name='Empresa a Eliminar',
            type_enterprise=self._get_type_enterprise()
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = Enterprise.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()