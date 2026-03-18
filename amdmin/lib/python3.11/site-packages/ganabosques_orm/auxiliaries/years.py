from mongoengine import EmbeddedDocument, StringField

class Years(EmbeddedDocument): 
    """Auto-generated auxiliary: Years"""  
    years = StringField()