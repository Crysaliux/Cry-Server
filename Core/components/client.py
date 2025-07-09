from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class NewClient(BaseModel):
    type: Literal['new_client']
    username: str
    nickname: str
    email: str
    password_hashed: str
    about_me: Union[str, None]
    avatar_url: Union[str, None]
    color_theme: Union[str, None]
    id: str