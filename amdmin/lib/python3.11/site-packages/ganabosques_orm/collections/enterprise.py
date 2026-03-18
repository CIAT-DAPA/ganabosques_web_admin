from mongoengine import Document, StringField, ObjectIdField, EmbeddedDocumentField, EmbeddedDocumentListField, EnumField, FloatField, ReferenceField
from ganabosques_orm.enums.typeenterprise import TypeEnterprise
from ganabosques_orm.auxiliaries.log import Log
from ganabosques_orm.auxiliaries.extidenterprise import ExtIdEnterprise
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.tools.exceptiondata import ExceptionData
from ganabosques_orm.enums.valuechain import ValueChain
class Enterprise(Document):
    """Auto-generated MongoDB collection: Enterprise"""
    meta = {'collection': 'enterprise'}
    adm2_id = ReferenceField(Adm2)
    name = StringField()
    ext_id = EmbeddedDocumentListField(ExtIdEnterprise)
    type_enterprise = EnumField(TypeEnterprise)
    latitude = FloatField()
    longitud = FloatField()
    log = EmbeddedDocumentField(Log)
    value_chain = EnumField(ValueChain)

    def validate(self, clean=True):
        if not self.name or self.name.strip() == "":
            raise ExceptionData("Name field is mandatory")
        
        if not self.type_enterprise:
            raise ExceptionData("Type Enterprise field is mandatory", attribute="type_enterprise")

        return True