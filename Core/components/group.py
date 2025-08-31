from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class CreateGroup(BaseModel):
    name: str
    about_group: Union[str, None]
    icon_url: Union[str, None]
    id: str

class UpdateGroup(BaseModel):
    name: str
    about_group: Union[str, None]
    icon_url: Union[str, None]
    nsfw: bool
    id: str

    content_filter: bool
    content_filter_level: str

class DeleteGroup(BaseModel):
    id: str