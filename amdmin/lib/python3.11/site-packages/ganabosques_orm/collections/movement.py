from mongoengine import Document, StringField, ObjectIdField, DateTimeField, EmbeddedDocumentField, EmbeddedDocumentListField, EnumField, ReferenceField
from ganabosques_orm.enums.typemovement import TypeMovement
from ganabosques_orm.collections.sourcemovement import SourceMovement
from ganabosques_orm.auxiliaries.classification import Classification
from ganabosques_orm.collections.farm import Farm
from ganabosques_orm.collections.enterprise import Enterprise
from ganabosques_orm.tools.exceptiondata import ExceptionData
from ganabosques_orm.enums.species import Species

class Movement(Document):
    """Auto-generated MongoDB collection: Movement"""
    meta = {'collection': 'movement'}
    date = DateTimeField()
    type_origin = EnumField(TypeMovement)
    type_destination = EnumField(TypeMovement)
    source_movement = ReferenceField(SourceMovement)
    ext_id = StringField()
    farm_id_origin = ReferenceField(Farm)
    farm_id_destination = ReferenceField(Farm)
    enterprise_id_origin = ReferenceField(Enterprise)
    enterprise_id_destination = ReferenceField(Enterprise)
    movement = EmbeddedDocumentListField(Classification)
    species = EnumField(Species)

    def validate(self, clean=True):
        # Verify that the required fields are present before saving.
        if self.date is None:
            raise ExceptionData("Date field is mandatory", attribute="date")

        if self.type_origin is None:
            raise ExceptionData("Type origin field is mandatory", attribute="type_origin")

        if self.type_destination is None:
            raise ExceptionData("Type destination field is mandatory", attribute="type_destination")
        
        if self.species is None:
            raise ExceptionData("Species field is mandatory", attribute="species")

        return True