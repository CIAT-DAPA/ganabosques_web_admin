from mongoengine import Document, StringField, ObjectIdField


class Permission(Document):
    """Auto-generated MongoDB collection: Permission"""
    meta = {'collection': 'permission'}
    name = StringField()
    descr = StringField()