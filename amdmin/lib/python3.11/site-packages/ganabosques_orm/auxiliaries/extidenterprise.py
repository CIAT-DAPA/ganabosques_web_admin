from mongoengine import EmbeddedDocument, StringField, EnumField
from ganabosques_orm.enums.label import Label

class ExtIdEnterprise(EmbeddedDocument):
    """Auto-generated auxiliary: ExtIdEnterprise"""
    label = EnumField(Label)
    ext_code = StringField()