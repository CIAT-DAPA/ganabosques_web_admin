from mongoengine import EmbeddedDocument, BooleanField, DateTimeField

class Log(EmbeddedDocument):
    """Auto-generated auxiliary: Log"""
    enable = BooleanField()
    created = DateTimeField()
    updated = DateTimeField()