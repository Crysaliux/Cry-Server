from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class NewGroup(BaseModel):
    type: Literal['new_group']
    owner_id: str
    name: str
    about_group: Union[str, None]
    icon_url: Union[str, None]
    id: str

class UpdateGroup(BaseModel):
    type: Literal['update_group']
    name: str
    about_group: Union[str, None]
    icon_url: Union[str, None]
    nsfw: bool
    id: str

    content_filter: bool
    content_filter_level: str

class DeleteGroup(BaseModel):
    type: Literal['delete_group']
    owner_id: str
    id: str