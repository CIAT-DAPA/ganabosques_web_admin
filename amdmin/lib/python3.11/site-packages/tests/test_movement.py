import unittest
from datetime import datetime

import mongomock
from mongoengine import connect, disconnect

from ganabosques_orm.collections.adm1 import Adm1
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.collections.adm3 import Adm3
from ganabosques_orm.collections.farm import Farm
from ganabosques_orm.collections.enterprise import Enterprise
from ganabosques_orm.collections.movement import Movement
from ganabosques_orm.collections.sourcemovement import SourceMovement

from ganabosques_orm.auxiliaries.classification import Classification
from ganabosques_orm.auxiliaries.extidfarm import ExtIdFarm

from ganabosques_orm.enums.farmsource import FarmSource
from ganabosques_orm.enums.typeenterprise import TypeEnterprise
from ganabosques_orm.enums.typemovement import TypeMovement
from ganabosques_orm.enums.species import Species

from ganabosques_orm.tools.exceptiondata import ExceptionData


class TestMovement(unittest.TestCase):

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
        Movement.drop_collection()
        SourceMovement.drop_collection()
        Farm.drop_collection()
        Enterprise.drop_collection()
        Adm3.drop_collection()
        Adm2.drop_collection()
        Adm1.drop_collection()

    def _get_type_movement(self):
        return list(TypeMovement)[0]

    def _get_species(self):
        return list(Species)[0]

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

    def _create_farm(self):
        farm = Farm(
            adm3_id=self._create_adm3(),
            ext_id=[ExtIdFarm()],
            farm_source=self._get_farm_source()
        )
        farm.save()
        return farm

    def _create_enterprise(self):
        enterprise = Enterprise(
            name='Empresa Demo',
            type_enterprise=self._get_type_enterprise()
        )
        enterprise.save()
        return enterprise

    def _create_source_movement(self):
        source = SourceMovement()
        source.save()
        return source

    def _build_classification_list(self):
        return [Classification()]

    def test_create_instance(self):
        instance = Movement()
        self.assertIsInstance(instance, Movement)

    def test_collection_name_is_movement(self):
        self.assertEqual(Movement._get_collection_name(), 'movement')

    def test_create_instance_with_valid_data(self):
        source_movement = self._create_source_movement()
        farm_origin = self._create_farm()
        farm_destination = self._create_farm()
        enterprise_origin = self._create_enterprise()
        enterprise_destination = self._create_enterprise()
        movement_items = self._build_classification_list()

        instance = Movement(
            date=datetime(2024, 7, 1, 10, 0, 0),
            type_origin=self._get_type_movement(),
            type_destination=self._get_type_movement(),
            source_movement=source_movement,
            ext_id='MOV-001',
            farm_id_origin=farm_origin,
            farm_id_destination=farm_destination,
            enterprise_id_origin=enterprise_origin,
            enterprise_id_destination=enterprise_destination,
            movement=movement_items,
            species=self._get_species()
        )

        self.assertEqual(instance.date, datetime(2024, 7, 1, 10, 0, 0))
        self.assertEqual(instance.type_origin, self._get_type_movement())
        self.assertEqual(instance.type_destination, self._get_type_movement())
        self.assertEqual(instance.source_movement, source_movement)
        self.assertEqual(instance.ext_id, 'MOV-001')
        self.assertEqual(instance.farm_id_origin, farm_origin)
        self.assertEqual(instance.farm_id_destination, farm_destination)
        self.assertEqual(instance.enterprise_id_origin, enterprise_origin)
        self.assertEqual(instance.enterprise_id_destination, enterprise_destination)
        self.assertEqual(len(instance.movement), 1)
        self.assertIsInstance(instance.movement[0], Classification)
        self.assertEqual(instance.species, self._get_species())

    def test_validate_returns_true_when_required_fields_are_present(self):
        instance = Movement(
            date=datetime(2024, 7, 1, 10, 0, 0),
            type_origin=self._get_type_movement(),
            type_destination=self._get_type_movement(),
            species=self._get_species()
        )

        result = instance.validate()

        self.assertTrue(result)

    def test_validate_raises_exceptiondata_when_date_is_missing(self):
        instance = Movement(
            type_origin=self._get_type_movement(),
            type_destination=self._get_type_movement(),
            species=self._get_species()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.validate()

        self.assertEqual(str(context.exception), 'Date field is mandatory')

    def test_validate_raises_exceptiondata_when_type_origin_is_missing(self):
        instance = Movement(
            date=datetime(2024, 7, 1, 10, 0, 0),
            type_destination=self._get_type_movement(),
            species=self._get_species()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.validate()

        self.assertEqual(str(context.exception), 'Type origin field is mandatory')

    def test_validate_raises_exceptiondata_when_type_destination_is_missing(self):
        instance = Movement(
            date=datetime(2024, 7, 1, 10, 0, 0),
            type_origin=self._get_type_movement(),
            species=self._get_species()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.validate()

        self.assertEqual(str(context.exception), 'Type destination field is mandatory')

    def test_validate_raises_exceptiondata_when_species_is_missing(self):
        instance = Movement(
            date=datetime(2024, 7, 1, 10, 0, 0),
            type_origin=self._get_type_movement(),
            type_destination=self._get_type_movement()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.validate()

        self.assertEqual(str(context.exception), 'Species field is mandatory')

    def test_save_instance_with_valid_data(self):
        source_movement = self._create_source_movement()
        farm_origin = self._create_farm()
        farm_destination = self._create_farm()
        enterprise_origin = self._create_enterprise()
        enterprise_destination = self._create_enterprise()

        instance = Movement(
            date=datetime(2024, 8, 15, 14, 0, 0),
            type_origin=self._get_type_movement(),
            type_destination=self._get_type_movement(),
            source_movement=source_movement,
            ext_id='MOV-002',
            farm_id_origin=farm_origin,
            farm_id_destination=farm_destination,
            enterprise_id_origin=enterprise_origin,
            enterprise_id_destination=enterprise_destination,
            movement=self._build_classification_list(),
            species=self._get_species()
        )
        instance.save()

        saved = Movement.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.date, datetime(2024, 8, 15, 14, 0, 0))
        self.assertEqual(saved.type_origin, self._get_type_movement())
        self.assertEqual(saved.type_destination, self._get_type_movement())
        self.assertEqual(saved.source_movement.id, source_movement.id)
        self.assertEqual(saved.ext_id, 'MOV-002')
        self.assertEqual(saved.farm_id_origin.id, farm_origin.id)
        self.assertEqual(saved.farm_id_destination.id, farm_destination.id)
        self.assertEqual(saved.enterprise_id_origin.id, enterprise_origin.id)
        self.assertEqual(saved.enterprise_id_destination.id, enterprise_destination.id)
        self.assertEqual(len(saved.movement), 1)
        self.assertIsInstance(saved.movement[0], Classification)
        self.assertEqual(saved.species, self._get_species())

    def test_save_raises_exceptiondata_when_date_is_missing(self):
        instance = Movement(
            type_origin=self._get_type_movement(),
            type_destination=self._get_type_movement(),
            species=self._get_species()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.save()

        self.assertEqual(str(context.exception), 'Date field is mandatory')

    def test_save_raises_exceptiondata_when_type_origin_is_missing(self):
        instance = Movement(
            date=datetime(2024, 7, 1, 10, 0, 0),
            type_destination=self._get_type_movement(),
            species=self._get_species()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.save()

        self.assertEqual(str(context.exception), 'Type origin field is mandatory')

    def test_save_raises_exceptiondata_when_type_destination_is_missing(self):
        instance = Movement(
            date=datetime(2024, 7, 1, 10, 0, 0),
            type_origin=self._get_type_movement(),
            species=self._get_species()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.save()

        self.assertEqual(str(context.exception), 'Type destination field is mandatory')

    def test_save_raises_exceptiondata_when_species_is_missing(self):
        instance = Movement(
            date=datetime(2024, 7, 1, 10, 0, 0),
            type_origin=self._get_type_movement(),
            type_destination=self._get_type_movement()
        )

        with self.assertRaises(ExceptionData) as context:
            instance.save()

        self.assertEqual(str(context.exception), 'Species field is mandatory')

    def test_save_instance_with_empty_optional_fields(self):
        instance = Movement(
            date=datetime(2024, 9, 1, 8, 0, 0),
            type_origin=self._get_type_movement(),
            type_destination=self._get_type_movement(),
            species=self._get_species()
        )
        instance.save()

        saved = Movement.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.date, datetime(2024, 9, 1, 8, 0, 0))
        self.assertEqual(saved.type_origin, self._get_type_movement())
        self.assertEqual(saved.type_destination, self._get_type_movement())
        self.assertIsNone(saved.source_movement)
        self.assertIsNone(saved.ext_id)
        self.assertIsNone(saved.farm_id_origin)
        self.assertIsNone(saved.farm_id_destination)
        self.assertIsNone(saved.enterprise_id_origin)
        self.assertIsNone(saved.enterprise_id_destination)
        self.assertEqual(saved.movement, [])
        self.assertEqual(saved.species, self._get_species())

    def test_create_instance_with_invalid_movement_item_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            Movement(movement=['invalid_classification'])

    def test_update_persisted_instance(self):
        instance = Movement(
            date=datetime(2024, 1, 10, 8, 0, 0),
            type_origin=self._get_type_movement(),
            type_destination=self._get_type_movement(),
            species=self._get_species()
        )
        instance.save()

        instance.ext_id = 'MOV-UPD-001'
        instance.movement = [Classification(), Classification()]
        instance.save()

        updated = Movement.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.ext_id, 'MOV-UPD-001')
        self.assertEqual(len(updated.movement), 2)
        self.assertIsInstance(updated.movement[0], Classification)
        self.assertIsInstance(updated.movement[1], Classification)

    def test_delete_instance(self):
        instance = Movement(
            date=datetime(2024, 3, 5, 11, 0, 0),
            type_origin=self._get_type_movement(),
            type_destination=self._get_type_movement(),
            species=self._get_species()
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = Movement.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()