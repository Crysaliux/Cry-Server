from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class NewPermission(BaseModel):
    type: Literal['new_permission']
    role_id: str
    room_id: str
    body: dict