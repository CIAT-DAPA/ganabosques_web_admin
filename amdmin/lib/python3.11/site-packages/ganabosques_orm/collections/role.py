from mongoengine import Document, EmbeddedDocument, StringField, ListField, EmbeddedDocumentField, EnumField
from ganabosques_orm.enums.actions import Actions
from ganabosques_orm.enums.options import Options


class ActionPermission(EmbeddedDocument):
    action = EnumField(Actions, required=True)
    options = ListField(EnumField(Options))


class Role(Document):
    meta = {'collection': 'role'}

    name = StringField()

    actions = ListField(EmbeddedDocumentField(ActionPermission))