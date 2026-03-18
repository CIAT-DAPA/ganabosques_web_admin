from mongoengine import Document, StringField, ObjectIdField, EmbeddedDocumentField, ReferenceField
from ganabosques_orm.auxiliaries.log import Log
from ganabosques_orm.collections.adm1 import Adm1

class Adm2(Document):
    """Auto-generated MongoDB collection: Adm2"""
    meta = {'collection': 'adm2'}
    adm1_id = ReferenceField(Adm1)
    name = StringField()
    ext_id = StringField()
    log = EmbeddedDocumentField(Log)