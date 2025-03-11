from mongoengine import Document, connect, StringField, FloatField, ObjectIdField


class ActiveUser(Document):
    user_id = ObjectIdField(required=True, primary_key=True)
    latitude = FloatField(required=True)
    longitude = FloatField(required=True)