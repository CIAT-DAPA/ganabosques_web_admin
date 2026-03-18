import unittest
from datetime import datetime

import mongomock
from mongoengine import connect, disconnect

from ganabosques_orm.collections.adm1 import Adm1
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.collections.adm3 import Adm3
from ganabosques_orm.collections.farm import Farm
from ganabosques_orm.collections.farmpolygons import FarmPolygons
from ganabosques_orm.collections.analysis import Analysis
from ganabosques_orm.collections.protectedareas import ProtectedAreas
from ganabosques_orm.collections.farmingareas import FarmingAreas
from ganabosques_orm.collections.deforestation import Deforestation
from ganabosques_orm.collections.farmrisk import FarmRisk
from ganabosques_orm.collections.farmriskverification import FarmRiskVerification
from ganabosques_orm.collections.user import User

from ganabosques_orm.auxiliaries.attributes import Attributes
from ganabosques_orm.auxiliaries.bufferpolygon import BufferPolygon
from ganabosques_orm.auxiliaries.extidfarm import ExtIdFarm
from ganabosques_orm.auxiliaries.typeanalysis import TypeAnalysis

from ganabosques_orm.enums.farmsource import FarmSource
from ganabosques_orm.enums.valuechain import ValueChain
from ganabosques_orm.enums.deforestationtype import DeforestationType
from ganabosques_orm.enums.deforestationsource import DeforestationSource


class TestFarmRiskVerification(unittest.TestCase):

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
        FarmRiskVerification.drop_collection()
        FarmRisk.drop_collection()
        FarmPolygons.drop_collection()
        Farm.drop_collection()
        Analysis.drop_collection()
        Deforestation.drop_collection()
        FarmingAreas.drop_collection()
        ProtectedAreas.drop_collection()
        User.drop_collection()
        Adm3.drop_collection()
        Adm2.drop_collection()
        Adm1.drop_collection()

    def _get_farm_source(self):
        return list(FarmSource)[0]

    def _get_value_chain(self):
        return list(ValueChain)[0]

    def _get_deforestation_source(self):
        return list(DeforestationSource)[0]

    def _get_deforestation_type(self):
        return list(DeforestationType)[0]

    def _create_user(self):
        user = User()
        user.save()
        return user

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

    def _create_farm(self):
        farm = Farm(
            adm3_id=self._create_adm3(),
            ext_id=[ExtIdFarm()],
            farm_source=self._get_farm_source()
        )
        farm.save()
        return farm

    def _create_farm_polygon(self, farm):
        farm_polygon = FarmPolygons(
            farm_id=farm,
            geojson='{"type":"Polygon","coordinates":[]}',
            latitude=4.7110,
            longitud=-74.0721,
            farm_ha=10.5,
            radio=50.0,
            buffer_inputs=[BufferPolygon()]
        )
        farm_polygon.save()
        return farm_polygon

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
            type_analysis=TypeAnalysis(),
            value_chain=self._get_value_chain()
        )
        analysis.save()

        return analysis

    def _create_farm_risk(self):
        farm = self._create_farm()
        analysis = self._create_analysis()
        farm_polygon = self._create_farm_polygon(farm)

        farm_risk = FarmRisk(
            farm_id=farm,
            analysis_id=analysis,
            farm_polygons_id=farm_polygon,
            deforestation=Attributes(),
            protected=Attributes(),
            farming_in=Attributes(),
            farming_out=Attributes(),
            risk_direct=True,
            risk_input=False,
            risk_output=True
        )
        farm_risk.save()
        return farm_risk

    def test_create_instance(self):
        instance = FarmRiskVerification()
        self.assertIsInstance(instance, FarmRiskVerification)

    def test_collection_name_is_farmriskverification(self):
        self.assertEqual(
            FarmRiskVerification._get_collection_name(),
            'farmriskverification'
        )

    def test_create_instance_with_valid_data(self):
        user = self._create_user()
        farm_risk = self._create_farm_risk()
        verification_date = datetime(2024, 7, 1, 9, 30, 0)

        instance = FarmRiskVerification(
            user_id=user,
            farmrisk=farm_risk,
            verification=verification_date,
            observation='Riesgo revisado manualmente',
            status=True
        )

        self.assertEqual(instance.user_id, user)
        self.assertEqual(instance.farmrisk, farm_risk)
        self.assertEqual(instance.verification, verification_date)
        self.assertEqual(instance.observation, 'Riesgo revisado manualmente')
        self.assertTrue(instance.status)

    def test_save_instance_with_valid_data(self):
        user = self._create_user()
        farm_risk = self._create_farm_risk()
        verification_date = datetime(2024, 8, 15, 14, 0, 0)

        instance = FarmRiskVerification(
            user_id=user,
            farmrisk=farm_risk,
            verification=verification_date,
            observation='Verificacion aprobada',
            status=False
        )
        instance.save()

        saved = FarmRiskVerification.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.user_id.id, user.id)
        self.assertEqual(saved.farmrisk.id, farm_risk.id)
        self.assertEqual(saved.verification, verification_date)
        self.assertEqual(saved.observation, 'Verificacion aprobada')
        self.assertFalse(saved.status)

    def test_save_instance_with_empty_fields(self):
        instance = FarmRiskVerification()
        instance.save()

        saved = FarmRiskVerification.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNone(saved.user_id)
        self.assertIsNone(saved.farmrisk)
        self.assertIsNone(saved.verification)
        self.assertIsNone(saved.observation)
        self.assertIsNone(saved.status)

    def test_update_persisted_instance(self):
        user = self._create_user()
        farm_risk = self._create_farm_risk()

        instance = FarmRiskVerification(
            user_id=user,
            farmrisk=farm_risk,
            verification=datetime(2024, 1, 10, 8, 0, 0),
            observation='Observacion inicial',
            status=False
        )
        instance.save()

        new_verification = datetime(2024, 2, 20, 16, 45, 0)
        instance.verification = new_verification
        instance.observation = 'Observacion actualizada'
        instance.status = True
        instance.save()

        updated = FarmRiskVerification.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.user_id.id, user.id)
        self.assertEqual(updated.farmrisk.id, farm_risk.id)
        self.assertEqual(updated.verification, new_verification)
        self.assertEqual(updated.observation, 'Observacion actualizada')
        self.assertTrue(updated.status)

    def test_delete_instance(self):
        instance = FarmRiskVerification(
            user_id=self._create_user(),
            farmrisk=self._create_farm_risk(),
            verification=datetime(2024, 3, 5, 11, 0, 0),
            observation='Registro a eliminar',
            status=True
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = FarmRiskVerification.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()