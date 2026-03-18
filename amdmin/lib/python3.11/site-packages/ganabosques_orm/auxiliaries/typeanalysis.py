from mongoengine import EmbeddedDocument, BooleanField, EnumField, StringField 
from ganabosques_orm.enums.typeanalysisenum import TypeAnalysisEnum

class TypeAnalysis(EmbeddedDocument):
    """Auto-generated auxiliary: TypeAnalysis"""
    label = EnumField(TypeAnalysisEnum)
    value = StringField()