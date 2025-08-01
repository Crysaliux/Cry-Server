from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class CreatePermission(BaseModel):
    group_id: str
    role_id: str
    room_id: Union[str, None] #None when global permission is passed
    body: dict
    id: str

class DeletePermission(BaseModel):
    group_id: str
    id: str