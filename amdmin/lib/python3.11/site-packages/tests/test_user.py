import unittest

import mongomock
from mongoengine import connect, disconnect

from ganabosques_orm.collections.user import User
from ganabosques_orm.collections.role import Role, ActionPermission
from ganabosques_orm.enums.actions import Actions
from ganabosques_orm.enums.options import Options


class TestUser(unittest.TestCase):

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
        User.drop_collection()
        Role.drop_collection()

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

    def test_create_instance(self):
        instance = User()
        self.assertIsInstance(instance, User)

    def test_collection_name_is_user(self):
        self.assertEqual(User._get_collection_name(), 'user')

    def test_create_instance_with_valid_data(self):
        role = self._create_role()

        instance = User(
            ext_id='USR-001',
            admin=True,
            role=[role]
        )

        self.assertEqual(instance.ext_id, 'USR-001')
        self.assertTrue(instance.admin)
        self.assertEqual(len(instance.role), 1)
        self.assertEqual(instance.role[0], role)

    def test_save_instance_with_valid_data(self):
        role = self._create_role()

        instance = User(
            ext_id='USR-002',
            admin=False,
            role=[role]
        )
        instance.save()

        saved = User.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.ext_id, 'USR-002')
        self.assertFalse(saved.admin)
        self.assertEqual(len(saved.role), 1)
        self.assertEqual(saved.role[0].id, role.id)

    def test_save_instance_with_multiple_roles(self):
        role_1 = self._create_role(name='Administrador')
        role_2 = self._create_role(name='Operador')

        instance = User(
            ext_id='USR-003',
            admin=True,
            role=[role_1, role_2]
        )
        instance.save()

        saved = User.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.ext_id, 'USR-003')
        self.assertTrue(saved.admin)
        self.assertEqual(len(saved.role), 2)
        self.assertEqual(saved.role[0].id, role_1.id)
        self.assertEqual(saved.role[1].id, role_2.id)

    def test_save_instance_with_empty_fields(self):
        instance = User()
        instance.save()

        saved = User.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNone(saved.ext_id)
        self.assertIsNone(saved.admin)
        self.assertEqual(saved.role, [])

    def test_save_instance_with_empty_role_list(self):
        instance = User(
            ext_id='USR-004',
            admin=False,
            role=[]
        )
        instance.save()

        saved = User.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.ext_id, 'USR-004')
        self.assertFalse(saved.admin)
        self.assertEqual(saved.role, [])

    def test_update_persisted_instance(self):
        role_1 = self._create_role(name='Consulta')
        role_2 = self._create_role(name='Supervisor')

        instance = User(
            ext_id='USR-005',
            admin=False,
            role=[role_1]
        )
        instance.save()

        instance.ext_id = 'USR-005-UPD'
        instance.admin = True
        instance.role = [role_1, role_2]
        instance.save()

        updated = User.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.ext_id, 'USR-005-UPD')
        self.assertTrue(updated.admin)
        self.assertEqual(len(updated.role), 2)
        self.assertEqual(updated.role[0].id, role_1.id)
        self.assertEqual(updated.role[1].id, role_2.id)

    def test_delete_instance(self):
        role = self._create_role()

        instance = User(
            ext_id='USR-006',
            admin=True,
            role=[role]
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = User.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()