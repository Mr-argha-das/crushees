from mongoengine import Document, StringField, DateTimeField, ReferenceField, ListField, connect, BooleanField
from datetime import datetime


class Message(Document):
    sender_id = StringField(required=True)
    receiver_id = StringField(required=True)
    message = StringField(required=True)
    timestamp = DateTimeField(default=datetime.utcnow)
    is_read = BooleanField(default=False)  # Mark if the message is read

class Conversation(Document):
    participants = ListField(StringField(), required=True)  # [user1, user2]
    last_message = ReferenceField(Message) 