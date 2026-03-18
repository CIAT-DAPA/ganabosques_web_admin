from mongoengine import Document, StringField, ObjectIdField, BooleanField, ListField, ReferenceField, DateTimeField
from ganabosques_orm.collections.role import Role
from ganabosques_orm.collections.user import User
from ganabosques_orm.collections.entity import Entity

class UserVerifier(Document):
    """Auto-generated MongoDB collection: UserVerifier"""
    meta = {'collection': 'userverifier'}
    user_id= ReferenceField(User)
    verification_entity_id = ReferenceField(Entity)
    date= DateTimeField()

    