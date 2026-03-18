from mongoengine import Document, ObjectIdField, EmbeddedDocumentField, FloatField, ReferenceField, BooleanField
from ganabosques_orm.auxiliaries.attributes import Attributes
from ganabosques_orm.collections.farm import Farm
from ganabosques_orm.collections.farmpolygons import FarmPolygons
from ganabosques_orm.collections.analysis import Analysis


class FarmRisk(Document):
    """Auto-generated MongoDB collection: FarmRisk"""
    meta = {'collection': 'farmrisk'}
    farm_id = ReferenceField(Farm)
    analysis_id = ReferenceField(Analysis)
    farm_polygons_id = ReferenceField(FarmPolygons)
    deforestation = EmbeddedDocumentField(Attributes)
    protected = EmbeddedDocumentField(Attributes)
    farming_in = EmbeddedDocumentField(Attributes)
    farming_out = EmbeddedDocumentField(Attributes)
    risk_direct = BooleanField()
    risk_input = BooleanField()
    risk_output = BooleanField()
