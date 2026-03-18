from mongoengine import EmbeddedDocument, StringField

class Classification(EmbeddedDocument):
    """Auto-generated auxiliary: Classification"""
    label = StringField()
    amount = StringField()