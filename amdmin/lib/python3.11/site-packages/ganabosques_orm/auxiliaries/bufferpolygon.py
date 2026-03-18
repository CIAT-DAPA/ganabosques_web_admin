from mongoengine import EmbeddedDocument, StringField, EnumField, FloatField, IntField, ListField
from ganabosques_orm.enums.ugg import UGG
from ganabosques_orm.enums.species import Species

class BufferPolygon(EmbeddedDocument):
    """Auto-generated auxiliary: BufferPolygon"""
    ugg = EnumField(UGG)
    amount = IntField()
    species = EnumField(Species)