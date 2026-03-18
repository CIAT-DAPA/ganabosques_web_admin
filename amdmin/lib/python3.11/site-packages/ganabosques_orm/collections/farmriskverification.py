from mongoengine import Document, ObjectIdField, ReferenceField, FloatField, IntField, BooleanField, DateTimeField, StringField
from ganabosques_orm.collections.user import User
from ganabosques_orm.collections.farmrisk import FarmRisk
from ganabosques_orm.collections.entity import Entity


class FarmRiskVerification(Document):
    """Auto-generated MongoDB collection: FarmRiskVerification"""
    meta = {'collection': 'farmriskverification'}
    user_id = ReferenceField(User)
    farmrisk = ReferenceField(FarmRisk)
    verification = DateTimeField()
    observation = StringField()
    status = BooleanField()