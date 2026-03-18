from mongoengine import Document, StringField, ObjectIdField, BooleanField, ListField, ReferenceField
from ganabosques_orm.collections.role import Role
class User(Document):
    """Auto-generated MongoDB collection: User"""
    meta = {'collection': 'user'}
    ext_id = StringField()
    admin = BooleanField()
    role = ListField(ReferenceField(Role))

    