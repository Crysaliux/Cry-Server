from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class UpdateClient(BaseModel):
    nickname: str
    about_me: str | None
    avatar_url: str | None
    color_theme: str | None