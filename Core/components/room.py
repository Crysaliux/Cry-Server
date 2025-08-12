from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class CreateRoom(BaseModel):
    group_id: str
    space_id: Union[str, None]
    name: str
    about_room: Union[str, None]
    id: str

class UpdateRoom(BaseModel):
    group_id: str
    space_id: Union[str, None]
    name: str
    about_room: Union[str, None]
    nsfw: bool
    id: str

class DeleteRoom(BaseModel):
    group_id: str
    id: str