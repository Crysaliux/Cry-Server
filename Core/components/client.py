from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class BlockClient(BaseModel):
    id: str

class ViewClient(BaseModel):
    group_id: str
    id: str

class ChangePassword(BaseModel):
    old_password: str
    new_password: str

class EditProfileSettings(BaseModel):
    username: str
    nickname: str
    about_me: str | None
    avatar_url: str | None
    color_theme: str | None