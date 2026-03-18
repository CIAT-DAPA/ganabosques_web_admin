from mongoengine import EmbeddedDocument, FloatField

class Attributes(EmbeddedDocument):
    """Auto-generated auxiliary: Attributes"""
    prop = FloatField()
    ha = FloatField()
