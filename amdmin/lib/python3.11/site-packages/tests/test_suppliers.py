import unittest
from datetime import datetime

import mongomock
from mongoengine import connect, disconnect

from ganabosques_orm.collections.adm1 import Adm1
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.collections.adm3 import Adm3
from ganabosques_orm.collections.enterprise import Enterprise
from ganabosques_orm.collections.farm import Farm
from ganabosques_orm.collections.suppliers import Suppliers
from ganabosques_orm.auxiliaries.log import Log
from ganabosques_orm.auxiliaries.extidfarm import ExtIdFarm
from ganabosques_orm.enums.farmsource import FarmSource
from ganabosques_orm.enums.typeenterprise import TypeEnterprise


class TestSuppliers(unittest.TestCase):

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
        Suppliers.drop_collection()
        Farm.drop_collection()
        Enterprise.drop_collection()
        Adm3.drop_collection()
        Adm2.drop_collection()
        Adm1.drop_collection()

    def _get_type_enterprise(self):
        return list(TypeEnterprise)[0]

    def _get_farm_source(self):
        return list(FarmSource)[0]

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

    def _create_enterprise(self):
        enterprise = Enterprise(
            name='Empresa Proveedora',
            type_enterprise=self._get_type_enterprise()
        )
        enterprise.save()
        return enterprise

    def _create_farm(self):
        adm3 = self._create_adm3()
        farm = Farm(
            adm3_id=adm3,
            ext_id=[ExtIdFarm()],
            farm_source=self._get_farm_source()
        )
        farm.save()
        return farm

    def test_create_instance(self):
        instance = Suppliers()
        self.assertIsInstance(instance, Suppliers)

    def test_collection_name_is_suppliers(self):
        self.assertEqual(Suppliers._get_collection_name(), 'suppliers')

    def test_create_instance_with_valid_data(self):
        enterprise = self._create_enterprise()
        farm = self._create_farm()

        instance = Suppliers(
            enterprise_id=enterprise,
            farm_id=farm,
            years=[2020, 2021, 2022]
        )

        self.assertEqual(instance.enterprise_id, enterprise)
        self.assertEqual(instance.farm_id, farm)
        self.assertEqual(instance.years, [2020, 2021, 2022])
        self.assertIsNone(instance.log)

    def test_save_instance_with_valid_data(self):
        enterprise = self._create_enterprise()
        farm = self._create_farm()

        instance = Suppliers(
            enterprise_id=enterprise,
            farm_id=farm,
            years=[2019, 2020]
        )
        instance.save()

        saved = Suppliers.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.enterprise_id.id, enterprise.id)
        self.assertEqual(saved.farm_id.id, farm.id)
        self.assertEqual(saved.years, [2019, 2020])
        self.assertIsNone(saved.log)

    def test_save_instance_with_log_embedded_document(self):
        enterprise = self._create_enterprise()
        farm = self._create_farm()
        log = Log(
            enable=True,
            created=datetime(2024, 1, 1, 10, 0, 0),
            updated=datetime(2024, 1, 2, 12, 0, 0)
        )

        instance = Suppliers(
            enterprise_id=enterprise,
            farm_id=farm,
            years=[2023],
            log=log
        )
        instance.save()

        saved = Suppliers.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.enterprise_id.id, enterprise.id)
        self.assertEqual(saved.farm_id.id, farm.id)
        self.assertEqual(saved.years, [2023])
        self.assertIsInstance(saved.log, Log)
        self.assertTrue(saved.log.enable)
        self.assertEqual(saved.log.created, datetime(2024, 1, 1, 10, 0, 0))
        self.assertEqual(saved.log.updated, datetime(2024, 1, 2, 12, 0, 0))

    def test_save_instance_with_empty_fields(self):
        instance = Suppliers()
        instance.save()

        saved = Suppliers.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNone(saved.enterprise_id)
        self.assertIsNone(saved.farm_id)
        self.assertEqual(saved.years, [])
        self.assertIsNone(saved.log)

    def test_save_instance_with_empty_years_list(self):
        enterprise = self._create_enterprise()
        farm = self._create_farm()

        instance = Suppliers(
            enterprise_id=enterprise,
            farm_id=farm,
            years=[]
        )
        instance.save()

        saved = Suppliers.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.years, [])

    def test_create_instance_with_invalid_log_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            Suppliers(log='invalid_log')

    def test_update_persisted_instance(self):
        enterprise = self._create_enterprise()
        farm = self._create_farm()

        instance = Suppliers(
            enterprise_id=enterprise,
            farm_id=farm,
            years=[2020]
        )
        instance.save()

        instance.years = [2020, 2021, 2022]
        instance.save()

        updated = Suppliers.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.enterprise_id.id, enterprise.id)
        self.assertEqual(updated.farm_id.id, farm.id)
        self.assertEqual(updated.years, [2020, 2021, 2022])

    def test_delete_instance(self):
        enterprise = self._create_enterprise()
        farm = self._create_farm()

        instance = Suppliers(
            enterprise_id=enterprise,
            farm_id=farm,
            years=[2021]
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = Suppliers.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()