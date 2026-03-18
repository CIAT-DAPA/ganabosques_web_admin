from mongoengine import Document, ObjectIdField, EmbeddedDocumentField, EmbeddedDocumentListField, EnumField, ReferenceField
from ganabosques_orm.enums.farmsource import FarmSource
from ganabosques_orm.auxiliaries.log import Log
from ganabosques_orm.auxiliaries.extidfarm import ExtIdFarm
from ganabosques_orm.collections.adm3 import Adm3
from ganabosques_orm.tools.exceptiondata import ExceptionData 
from ganabosques_orm.enums.valuechain import ValueChain


class Farm(Document):
    """Auto-generated MongoDB collection: Farm"""
    meta = {'collection': 'farm'}
    adm3_id = ReferenceField(Adm3)
    ext_id = EmbeddedDocumentListField(ExtIdFarm)
    farm_source = EnumField(FarmSource)
    log = EmbeddedDocumentField(Log)
    value_chain = EnumField(ValueChain)

    def validate(self, clean=True):
        # Validación: adm3_id is mandatory
        if not self.adm3_id:
            raise ExceptionData("adm3_id is required", attribute="adm3_id")

        # Validación: farm_source is mandatory
        if not self.farm_source:
            raise ExceptionData("farm_source is required", attribute="farm_source")

        # Validación: ext_id must not be empty
        if not self.ext_id or len(self.ext_id) == 0:
            raise ExceptionData("ext_id must contain at least one entry", attribute="ext_id")

        return True