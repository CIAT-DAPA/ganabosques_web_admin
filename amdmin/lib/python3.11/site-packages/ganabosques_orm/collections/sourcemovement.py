from mongoengine import  Document, EmbeddedDocument, StringField, EmbeddedDocumentField
from ganabosques_orm.auxiliaries.log import Log

class SourceMovement(Document):
    """Auto-generated MongoDB collection: SourceMovement"""
    meta = {'collection': 'sourcemovement'}
    name = StringField()
    log = EmbeddedDocumentField(Log)