import unittest
from datetime import datetime
from bson import ObjectId

import mongomock
from mongoengine import connect, disconnect, ValidationError

from ganabosques_orm.collections.adm1 import Adm1
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.collections.adm3 import Adm3
from ganabosques_orm.collections.analysis import Analysis
from ganabosques_orm.collections.protectedareas import ProtectedAreas
from ganabosques_orm.collections.farmingareas import FarmingAreas
from ganabosques_orm.collections.deforestation import Deforestation
from ganabosques_orm.collections.adm3risk import Adm3Risk

from ganabosques_orm.auxiliaries.typeanalysis import TypeAnalysis

from ganabosques_orm.enums.valuechain import ValueChain
from ganabosques_orm.enums.deforestationtype import DeforestationType
from ganabosques_orm.enums.deforestationsource import DeforestationSource


class TestAdm3Risk(unittest.TestCase):

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
        Adm3Risk.drop_collection()
        Analysis.drop_collection()
        Deforestation.drop_collection()
        FarmingAreas.drop_collection()
        ProtectedAreas.drop_collection()
        Adm3.drop_collection()
        Adm2.drop_collection()
        Adm1.drop_collection()

    def _get_value_chain(self):
        return list(ValueChain)[0]

    def _get_deforestation_source(self):
        return list(DeforestationSource)[0]

    def _get_deforestation_type(self):
        return list(DeforestationType)[0]

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

    def _create_analysis(self):
        protected_area = ProtectedAreas(
            name='Parque Natural',
            path='/data/protected/parque.geojson'
        )
        protected_area.save()

        farming_area = FarmingAreas(
            name='Zona Agricola',
            path='/data/farming/zona.geojson'
        )
        farming_area.save()

        deforestation = Deforestation(
            deforestation_source=self._get_deforestation_source(),
            deforestation_type=self._get_deforestation_type(),
            name='Deforestacion 2024',
            period_start=datetime(2024, 1, 1, 0, 0, 0),
            period_end=datetime(2024, 12, 31, 23, 59, 59),
            path='/data/deforestation/2024.geojson'
        )
        deforestation.save()

        analysis = Analysis(
            protected_areas_id=protected_area,
            farming_areas_id=farming_area,
            deforestation_id=deforestation,
            user_id=ObjectId(),
            date=datetime(2024, 6, 1, 8, 30, 0),
            type_analysis=TypeAnalysis(),
            value_chain=self._get_value_chain()
        )
        analysis.save()

        return analysis

    def test_create_instance(self):
        instance = Adm3Risk()
        self.assertIsInstance(instance, Adm3Risk)

    def test_collection_name_is_adm3risk(self):
        self.assertEqual(Adm3Risk._get_collection_name(), 'adm3risk')

    def test_create_instance_with_valid_data(self):
        adm3 = self._create_adm3()
        analysis = self._create_analysis()

        instance = Adm3Risk(
            adm3_id=adm3,
            analysis_id=analysis,
            def_ha=125.75,
            farm_amount=12,
            risk_total=True,
            farm_total_amount=20
        )

        self.assertEqual(instance.adm3_id, adm3)
        self.assertEqual(instance.analysis_id, analysis)
        self.assertEqual(instance.def_ha, 125.75)
        self.assertEqual(instance.farm_amount, 12)
        self.assertTrue(instance.risk_total)
        self.assertEqual(instance.farm_total_amount, 20)

    def test_save_instance_with_valid_data(self):
        adm3 = self._create_adm3()
        analysis = self._create_analysis()

        instance = Adm3Risk(
            adm3_id=adm3,
            analysis_id=analysis,
            def_ha=80.5,
            farm_amount=7,
            risk_total=False,
            farm_total_amount=15
        )
        instance.save()

        saved = Adm3Risk.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.adm3_id.id, adm3.id)
        self.assertEqual(saved.analysis_id.id, analysis.id)
        self.assertEqual(saved.def_ha, 80.5)
        self.assertEqual(saved.farm_amount, 7)
        self.assertFalse(saved.risk_total)
        self.assertEqual(saved.farm_total_amount, 15)

    def test_save_instance_with_empty_fields(self):
        instance = Adm3Risk()
        instance.save()

        saved = Adm3Risk.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNone(saved.adm3_id)
        self.assertIsNone(saved.analysis_id)
        self.assertIsNone(saved.def_ha)
        self.assertIsNone(saved.farm_amount)
        self.assertIsNone(saved.risk_total)
        self.assertIsNone(saved.farm_total_amount)

    def test_validate_invalid_def_ha_type_raises_validation_error(self):
        instance = Adm3Risk(def_ha='invalid_float')

        with self.assertRaises(ValidationError):
            instance.validate()

    def test_validate_invalid_farm_amount_type_raises_validation_error(self):
        instance = Adm3Risk(farm_amount='invalid_int')

        with self.assertRaises(ValidationError):
            instance.validate()

    def test_validate_invalid_farm_total_amount_type_raises_validation_error(self):
        instance = Adm3Risk(farm_total_amount='invalid_int')

        with self.assertRaises(ValidationError):
            instance.validate()

    def test_update_persisted_instance(self):
        adm3 = self._create_adm3()
        analysis = self._create_analysis()

        instance = Adm3Risk(
            adm3_id=adm3,
            analysis_id=analysis,
            def_ha=40.0,
            farm_amount=4,
            risk_total=False,
            farm_total_amount=10
        )
        instance.save()

        instance.def_ha = 55.25
        instance.farm_amount = 6
        instance.risk_total = True
        instance.farm_total_amount = 14
        instance.save()

        updated = Adm3Risk.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.adm3_id.id, adm3.id)
        self.assertEqual(updated.analysis_id.id, analysis.id)
        self.assertEqual(updated.def_ha, 55.25)
        self.assertEqual(updated.farm_amount, 6)
        self.assertTrue(updated.risk_total)
        self.assertEqual(updated.farm_total_amount, 14)

    def test_delete_instance(self):
        instance = Adm3Risk(
            adm3_id=self._create_adm3(),
            analysis_id=self._create_analysis(),
            def_ha=22.0,
            farm_amount=3,
            risk_total=True,
            farm_total_amount=5
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = Adm3Risk.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()