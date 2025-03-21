from typing import List
from mongoengine import Document, StringField, FloatField, IntField, ListField, ReferenceField
from pydantic import BaseModel

class UserTable(Document):
    uuid = StringField(required=True)
    email_address = StringField(required=True)
    fullName = StringField(required=True)
    profilePicture = StringField(required=True)
    age = StringField(required=True)
    gender = StringField(required=True)
    password_hash = StringField(required=True)
    sexual_orientation = StringField(required=True)
    location_city = StringField(required=True)
    location_state = StringField(required=True)
    interests = ListField(StringField())
    qualities = ListField(StringField())
    firstPrompt = StringField(required=True)
    secondPrompt = StringField(required=True)
    thirdPrompt = StringField(required=True)
class UserCreate(BaseModel):
    uuid: str
    email_address: str
    fullName: str
    profilePicture: str
    age: str
    gender: str
    password: str
    sexual_orientation: str
    location_city: str
    location_state: str
    interests: List[str]
    qualities: List[str]
    firstPrompt : str
    secondPrompt: str
    thirdPrompt : str

class UserResponse(BaseModel):
    uuid: str
    fullName: str
    profilePicture: str
    age: str
    gender: str
    sexual_orientation: str
    location_city: str
    location_state: str
    interests: List[str]
    qualities: List[str]
    compatibility_score: float
class UserInteraction(Document):
    user_id = ReferenceField(UserTable, required=True)
    target_user_id = ReferenceField(UserTable, required=True)
    decision = StringField(required=True, choices=["accept", "deny"])
class UserDecision(BaseModel):
    user_id: str  # The current user's UUID
    target_user_id: str  # The UUID of the user being accepted/denied
    decision: str  #