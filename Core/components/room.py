from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class NewRoom(BaseModel):
    type: Literal['new_room']
    group_id: str
    space_id: Union[str, None]
    creator_id: str
    name: str
    about_room: Union[str, None]
    id: str

class UpdateRoom(BaseModel):
    type: Literal['update_room']
    space_id: Union[str, None]
    group_id: str
    name: str
    about_room: Union[str, None]
    nsfw: bool
    id: str

class DeleteRoom(BaseModel):
    type: Literal['delete_room']
    group_id: str
    id: str