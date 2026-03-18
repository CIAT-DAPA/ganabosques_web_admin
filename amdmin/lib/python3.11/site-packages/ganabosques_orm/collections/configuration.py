from mongoengine import Document, StringField, ObjectIdField, EmbeddedDocumentField, EmbeddedDocumentListField
from ganabosques_orm.auxiliaries.log import Log
from ganabosques_orm.auxiliaries.parameters import Parameters

class Configuration(Document):
    """Auto-generated MongoDB collection: Configuration"""
    meta = {'collection': 'configuration'}
    name = StringField()
    parameters = EmbeddedDocumentListField(Parameters)
    log = EmbeddedDocumentField(Log)