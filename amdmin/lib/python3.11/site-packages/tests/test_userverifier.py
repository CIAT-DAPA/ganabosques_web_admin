import unittest
from datetime import datetime

import mongomock
from mongoengine import connect, disconnect

from ganabosques_orm.collections.userverifier import UserVerifier
from ganabosques_orm.collections.user import User
from ganabosques_orm.collections.role import Role, ActionPermission
from ganabosques_orm.collections.entity import Entity
from ganabosques_orm.enums.actions import Actions
from ganabosques_orm.enums.options import Options


class TestUserVerifier(unittest.TestCase):

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
        UserVerifier.drop_collection()
        User.drop_collection()
        Role.drop_collection()
        Entity.drop_collection()

    def _create_role(self, name='Rol Base'):
        role = Role(
            name=name,
            actions=[
                ActionPermission(
                    action=list(Actions)[0],
                    options=[Options.READ]
                )
            ]
        )
        role.save()
        return role

    def _create_user(self):
        role = self._create_role()
        user = User(
            ext_id='USR-001',
            admin=False,
            role=[role]
        )
        user.save()
        return user

    def _create_entity(self):
        entity = Entity()
        entity.save()
        return entity

    def test_create_instance(self):
        instance = UserVerifier()
        self.assertIsInstance(instance, UserVerifier)

    def test_collection_name_is_userverifier(self):
        self.assertEqual(UserVerifier._get_collection_name(), 'userverifier')

    def test_create_instance_with_valid_data(self):
        user = self._create_user()
        entity = self._create_entity()
        verification_date = datetime(2024, 7, 1, 9, 30, 0)

        instance = UserVerifier(
            user_id=user,
            verification_entity_id=entity,
            date=verification_date
        )

        self.assertEqual(instance.user_id, user)
        self.assertEqual(instance.verification_entity_id, entity)
        self.assertEqual(instance.date, verification_date)

    def test_save_instance_with_valid_data(self):
        user = self._create_user()
        entity = self._create_entity()
        verification_date = datetime(2024, 8, 15, 14, 0, 0)

        instance = UserVerifier(
            user_id=user,
            verification_entity_id=entity,
            date=verification_date
        )
        instance.save()

        saved = UserVerifier.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.user_id.id, user.id)
        self.assertEqual(saved.verification_entity_id.id, entity.id)
        self.assertEqual(saved.date, verification_date)

    def test_save_instance_with_empty_fields(self):
        instance = UserVerifier()
        instance.save()

        saved = UserVerifier.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNone(saved.user_id)
        self.assertIsNone(saved.verification_entity_id)
        self.assertIsNone(saved.date)

    def test_update_persisted_instance(self):
        user = self._create_user()
        entity = self._create_entity()

        instance = UserVerifier(
            user_id=user,
            verification_entity_id=entity,
            date=datetime(2024, 1, 10, 8, 0, 0)
        )
        instance.save()

        new_date = datetime(2024, 2, 20, 16, 45, 0)
        instance.date = new_date
        instance.save()

        updated = UserVerifier.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.user_id.id, user.id)
        self.assertEqual(updated.verification_entity_id.id, entity.id)
        self.assertEqual(updated.date, new_date)

    def test_delete_instance(self):
        instance = UserVerifier(
            user_id=self._create_user(),
            verification_entity_id=self._create_entity(),
            date=datetime(2024, 3, 5, 11, 0, 0)
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = UserVerifier.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()