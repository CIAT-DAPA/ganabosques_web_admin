from mongoengine import Document, StringField, ObjectIdField, EmbeddedDocumentField, ReferenceField
from ganabosques_orm.auxiliaries.log import Log
from ganabosques_orm.collections.adm2 import Adm2

class Adm3(Document):
    """Auto-generated MongoDB collection: Adm3"""
    meta = {'collection': 'adm3'}
    adm2_id = ReferenceField(Adm2)
    name = StringField()
    ext_id = StringField()
    label = StringField()
    log = EmbeddedDocumentField(Log)