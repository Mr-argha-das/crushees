from mongoengine import Document, StringField
from pydantic import BaseModel

class ThingsTable(Document):
    title = StringField(required=True)

class ThingsCreate(BaseModel):
    title : str