import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import mongomock
from mongoengine import connect, disconnect, ValidationError

from ganabosques_orm.collections.role import Role, ActionPermission
from ganabosques_orm.enums.actions import Actions
from ganabosques_orm.enums.options import Options


class TestRole(unittest.TestCase):

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
        Role.drop_collection()

    def _make_permission(self, action=None, options=None):
        """Helper: crea un ActionPermission con valores por defecto."""
        return ActionPermission(
            action=action or list(Actions)[0],
            options=options or [Options.READ]
        )

    def _make_second_permission(self):
        """Helper: crea un segundo ActionPermission distinto."""
        actions = list(Actions)
        second_action = actions[1] if len(actions) > 1 else actions[0]
        return ActionPermission(
            action=second_action,
            options=[Options.CREATE, Options.UPDATE]
        )

    def test_create_instance(self):
        instance = Role()
        self.assertIsInstance(instance, Role)

    def test_collection_name_is_role(self):
        self.assertEqual(Role._get_collection_name(), 'role')

    def test_create_instance_with_valid_data(self):
        perm = self._make_permission()
        instance = Role(
            name='Administrador',
            actions=[perm]
        )

        self.assertEqual(instance.name, 'Administrador')
        self.assertEqual(len(instance.actions), 1)
        self.assertEqual(instance.actions[0].action, perm.action)
        self.assertEqual(instance.actions[0].options, perm.options)

    def test_save_instance_with_valid_data(self):
        perm = self._make_permission()
        instance = Role(
            name='Supervisor',
            actions=[perm]
        )
        instance.save()

        saved = Role.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.name, 'Supervisor')
        self.assertEqual(len(saved.actions), 1)
        self.assertEqual(saved.actions[0].action, perm.action)
        self.assertEqual(saved.actions[0].options, perm.options)

    def test_save_instance_with_multiple_actions(self):
        perm1 = self._make_permission()
        perm2 = self._make_second_permission()
        instance = Role(
            name='Operador',
            actions=[perm1, perm2]
        )
        instance.save()

        saved = Role.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(len(saved.actions), 2)
        self.assertEqual(saved.actions[0].action, perm1.action)
        self.assertEqual(saved.actions[0].options, perm1.options)
        self.assertEqual(saved.actions[1].action, perm2.action)
        self.assertEqual(saved.actions[1].options, perm2.options)

    def test_save_instance_with_empty_fields(self):
        instance = Role()
        instance.save()

        saved = Role.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertIsNone(saved.name)
        self.assertEqual(saved.actions, [])

    def test_save_instance_with_empty_actions_list(self):
        instance = Role(
            name='Consulta',
            actions=[]
        )
        instance.save()

        saved = Role.objects(id=instance.id).first()

        self.assertIsNotNone(saved)
        self.assertEqual(saved.name, 'Consulta')
        self.assertEqual(saved.actions, [])

    def test_each_action_has_its_own_options(self):
        """Verifica que cada action guarda sus propias options independientemente."""
        perm_farms = ActionPermission(
            action=Actions.FRONT_FARMS,
            options=[Options.READ, Options.UPDATE]
        )
        perm_enterprise = ActionPermission(
            action=Actions.FRONT_ENTERPRISE,
            options=[Options.CREATE, Options.READ, Options.UPDATE, Options.DELETE]
        )
        instance = Role(
            name='Mixto',
            actions=[perm_farms, perm_enterprise]
        )
        instance.save()

        saved = Role.objects(id=instance.id).first()

        self.assertEqual(len(saved.actions[0].options), 2)
        self.assertEqual(len(saved.actions[1].options), 4)
        self.assertIn(Options.READ, saved.actions[0].options)
        self.assertIn(Options.UPDATE, saved.actions[0].options)
        self.assertNotIn(Options.DELETE, saved.actions[0].options)
        self.assertIn(Options.DELETE, saved.actions[1].options)

    def test_update_persisted_instance(self):
        perm1 = self._make_permission()
        instance = Role(
            name='Rol Base',
            actions=[perm1]
        )
        instance.save()

        perm2 = self._make_second_permission()
        instance.name = 'Rol Actualizado'
        instance.actions = [perm1, perm2]
        instance.save()

        updated = Role.objects(id=instance.id).first()

        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, 'Rol Actualizado')
        self.assertEqual(len(updated.actions), 2)

    def test_delete_instance(self):
        perm = self._make_permission()
        instance = Role(
            name='Rol a Eliminar',
            actions=[perm]
        )
        instance.save()
        instance_id = instance.id

        instance.delete()

        deleted = Role.objects(id=instance_id).first()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()