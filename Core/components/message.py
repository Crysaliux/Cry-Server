from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class NewMessage(BaseModel):
    type: Literal['new_message']
    group_id: str
    space_id: str
    room_id: str
    author_id: str
    content: str
    id: str

class UpdateMessage(BaseModel): #.edited must be set to True
    type: Literal['update_message']
    group_id: str
    room_id: str
    author_id: str
    content: str
    id: str

class DeleteMessage(BaseModel): #.edited must be set to True
    type: Literal['delete_message']
    group_id: str
    room_id: str
    author_id: str
    id: str