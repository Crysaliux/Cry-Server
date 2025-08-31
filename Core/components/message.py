from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class SendMessage(BaseModel):
    group_id: str
    room_id: str
    content: str
    id: str

class EditMessage(BaseModel): #.edited must be set to True
    group_id: str
    room_id: str
    content: str
    id: str

class DeleteMessage(BaseModel): #.edited must be set to True
    group_id: str
    room_id: str
    id: str