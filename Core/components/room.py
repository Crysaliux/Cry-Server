from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class CreateRoom(BaseModel):
    group_id: str
    space_id: str | None
    name: str
    about_room: str | None

class EditRoom(BaseModel):
    group_id: str
    name: str
    about_room: str | None
    nsfw: bool
    id: str

class DeleteRoom(BaseModel):
    group_id: str
    id: str

class RelocateRoom(BaseModel):
    group_id: str
    space_id: str
    id: str

class JoinRoom(BaseModel):
    group_id: str
    id: str

class ViewRoomSettings(BaseModel):
    group_id: str
    id: str