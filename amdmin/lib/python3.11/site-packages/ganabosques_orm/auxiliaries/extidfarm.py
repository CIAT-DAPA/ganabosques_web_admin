from mongoengine import EmbeddedDocument, StringField, EnumField
from ganabosques_orm.enums.source import Source

class ExtIdFarm(EmbeddedDocument):
    """Auto-generated auxiliary: ExtIdFarm"""
    source = EnumField(Source)
    ext_code = StringField()