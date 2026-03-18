from mongoengine import EmbeddedDocument, StringField, EnumField, FloatField, IntField, ListField
from ganabosques_orm.enums.ugg import UGG
from ganabosques_orm.enums.species import Species

class BufferParameter(EmbeddedDocument):
    """Auto-generated auxiliary: Attributes"""
    ugg = EnumField(UGG)
    species = EnumField(Species)
    size = FloatField()