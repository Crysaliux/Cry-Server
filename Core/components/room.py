from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class NewRoom(BaseModel):
    type: Literal['new_room']
    group_id: str
    space_id: str
    creator_id: str
    name: str
    about_room: Union[str, None]
    nsfw: bool
    id: str