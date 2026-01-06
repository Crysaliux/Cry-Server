from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class CreateGroup(BaseModel):
    name: str
    global_name: str
    about_group: str | None
    icon_url: str | None

class EditGroup(BaseModel):
    name: str
    global_name: str
    about_group: str | None
    icon_url: str | None
    nsfw: bool
    id: str

    content_filter: bool
    content_filter_level: str

class DeleteGroup(BaseModel):
    id: str

class JoinGroup(BaseModel):
    global_name: str

class LeaveGroup(BaseModel):
    id: str

class BanClient(BaseModel):
    id: str
    client_id: str

class KickClient(BaseModel):
    id: str
    client_id: str

class ViewGroupSettings(BaseModel):
    id: str

class ViewGroupRoles(BaseModel):
    id: str

class ViewBanned(BaseModel):
    id: str