from mongoengine import EmbeddedDocument, StringField

class Parameters(EmbeddedDocument):
    """Auto-generated auxiliary: Parameters"""
    key = StringField()
    value = StringField()