from mongoengine import Document, StringField
from pydantic import BaseModel

class QualitiesTable(Document):
    title = StringField(required=True)

class QualitiesCreate(BaseModel):
    title : str