import unittest
from datetime import datetime
from bson import ObjectId

import mongomock
from mongoengine import connect, disconnect

from ganabosques_orm.collections.analysis import Analysis
from ganabosques_orm.collections.protectedareas import ProtectedAreas
from ganabosques_orm.collections.farmingareas import FarmingAreas
from ganabosques_orm.collections.deforestation import Deforestation
from ganabosques_orm.auxiliaries.typeanalysis import TypeAnalysis
from ganabosques_orm.enums.valuechain import ValueChain
from ganabosques_orm.enums.deforestationtype import DeforestationType
from ganabosques_orm.enums.deforestationsource import DeforestationSource


class TestAnalysis(unittest.TestCase):

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
        Analysis.drop_collection()
        Deforestation.drop_collection()
        FarmingAreas.drop_collection()
        ProtectedAreas.drop_collection()

    def _get_value_chain(self):
        return list(ValueChain)[0]

    def _get_deforestation_source(self):
        return list(DeforestationSource)[0]

    def _get_deforestation_type(self):
        return list(DeforestationType)[0]

    def _create_protected_area(self):
        instance = ProtectedAreas(
            name='Parque Natural',
            path='/data/protected/parque.geojson'
        )
        instance.save()
        return instance

    def _create_farming_area(self):
        instance = FarmingAreas(
            name='Zona Agricola',
            path='/data/farming/zona.geojson'
        )
        instance.save()
        return instance

    def _create_deforestation(self):
        instance = Deforestation(
            deforestation_source=self._get_deforestation_source(),
            deforestation_type=self._get_deforestation_type(),
            name='Deforestacion 2024',
            period_start=datetime(2024, 1, 1, 0, 0, 0),
            period_end=datetime(2024, 12, 31, 23, 59, 59),
            path='/data/deforestation/2024.geojson'
        )
        instance.save()
        return instance

    def _build_type_analysis(self):
        return TypeAnalysis()

    def test_create_instance(self):
        instance = Analysis()
        self.assertIsInstance(instance, Analysis)

    def test_collection_name_is_analysis(self):
        self.assertEqual(Analysis._get_collection_name(), 'analysis')

    def test_create_instance_with_valid_data(self):
        protected_area = self._create_protected_area()
        farming_area = self._create_farming_area()
        deforestation = self._create_deforestation()
        user_id = ObjectId()
        analysis_date = datetime(2024, 6, 1, 8, 30, 0)
        type_analysis = self._build_type_analysis()
        value_chain = self._get_value_chain()

        instance = Analysis(
            protected_areas_id=protected_area,
            farming_areas_id=farming_area,
            deforestation_id=deforestation,
            user_id=user_id,
            date=analysis_date,
            type_analysis=type_analysis,
            value_chain=value_chain
        )

        self.assertEqual(instance.protected_areas_id, protected_area)
        self.assertEqual(instance.farming_areas_id, farming_area)
        self.assertEqual(instance.deforestation_id, deforestation)
        self.assertEqual(instance.user_id, user_id)
        self.assertEqual(instance.date, analysis_date)
        self.assertIsInstance(instance.type_analysis, TypeAnalysis)
        self.assertEqual(instance.value_chain, value_chain)

    def test_save_instance_with_valid_data(self):
        protected_area = self._create_protected_area()
        farming_area = self._create_farming_area()
        deforestation = self._create_deforestation()
        user_id = ObjectId()
        analysis_date = datetime(2024, 7, 15, 14, 0, 0)
        value_chain = self._get_value_chain()

        instance = Analysis(
            protected_areas_id=protected_area,
            farming_areas_id=farming_area,
            deforestation_id=deforestation,
            user_id=user_id,
            date=analysis_date,
            type_analysis=self._build_type_analysis(),
            value_chain=value_chain
        )
        instance.save()

        saved = Analysis.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.protected_areas_id.id, protected_area.id)
        self.assertEqual(saved.farming_areas_id.id, farming_area.id)
        self.assertEqual(saved.deforestation_id.id, deforestation.id)
        self.assertEqual(saved.user_id, user_id)
        self.assertEqual(saved.date, analysis_date)
        self.assertIsInstance(saved.type_analysis, TypeAnalysis)
        self.assertEqual(saved.value_chain, value_chain)

    def test_save_instance_with_empty_fields(self):
        instance = Analysis()
        instance.save()

        saved = Analysis.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNone(saved.protected_areas_id)
        self.assertIsNone(saved.farming_areas_id)
        self.assertIsNone(saved.deforestation_id)
        self.assertIsNone(saved.user_id)
        self.assertIsNone(saved.date)
        self.assertIsNone(saved.type_analysis)
        self.assertIsNone(saved.value_chain)

    def test_create_instance_with_invalid_type_analysis_raises_value_error(self):
        with self.assertRaises(ValueError):
            Analysis(type_analysis='invalid_type_analysis')

    def test_update_persisted_instance(self):
        protected_area = self._create_protected_area()
        farming_area = self._create_farming_area()
        deforestation = self._create_deforestation()

        instance = Analysis(
            protected_areas_id=protected_area,
            farming_areas_id=farming_area,
            deforestation_id=deforestation,
            user_id=ObjectId(),
            date=datetime(2024, 1, 1, 10, 0, 0),
            type_analysis=self._build_type_analysis(),
            value_chain=self._get_value_chain()
        )
        instance.save()

        new_user_id = ObjectId()
        new_date = datetime(2024, 8, 20, 16, 45, 0)

        instance.user_id = new_user_id
        instance.date = new_date
        instance.type_analysis = self._build_type_analysis()
        instance.value_chain = self._get_value_chain()
        instance.save()

        updated = Analysis.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.protected_areas_id.id, protected_area.id)
        self.assertEqual(updated.farming_areas_id.id, farming_area.id)
        self.assertEqual(updated.deforestation_id.id, deforestation.id)
        self.assertEqual(updated.user_id, new_user_id)
        self.assertEqual(updated.date, new_date)
        self.assertIsInstance(updated.type_analysis, TypeAnalysis)
        self.assertEqual(updated.value_chain, self._get_value_chain())

    def test_delete_instance(self):
        instance = Analysis(
            protected_areas_id=self._create_protected_area(),
            farming_areas_id=self._create_farming_area(),
            deforestation_id=self._create_deforestation(),
            user_id=ObjectId(),
            date=datetime(2024, 3, 10, 9, 0, 0),
            type_analysis=self._build_type_analysis(),
            value_chain=self._get_value_chain()
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = Analysis.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()