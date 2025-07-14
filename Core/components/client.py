from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class UpdateClient(BaseModel):
    type: Literal['update_client']
    nickname: str
    about_me: Union[str, None]
    avatar_url: Union[str, None]
    color_theme: Union[str, None]

class DeleteClient(BaseModel):
    type: Literal['delete_client']
    id: str