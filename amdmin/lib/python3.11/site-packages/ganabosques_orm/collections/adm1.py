from mongoengine import Document, StringField, ObjectIdField, EmbeddedDocumentField,FloatField
from ganabosques_orm.auxiliaries.log import Log
#from ganabosques_orm.auxiliaries.bufferparameter import BufferParameter

class Adm1(Document):
    """Auto-generated MongoDB collection: Adm1"""
    meta = {'collection': 'adm1'}
    name = StringField()
    ext_id = StringField()
    #buffer_p = EmbeddedDocumentField(BufferParameter)
    ugg_size = FloatField()
    log = EmbeddedDocumentField(Log)