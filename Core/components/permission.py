from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class NewPermission(BaseModel):
    type: Literal['new_permission']
    group_id: str
    role_id: str
    room_id: Union[str, None] #None when global permission is passed
    body: dict
    id: str

class DeletePermission(BaseModel):
    type: Literal['delete_permission']
    group_id: str
    room_id: Union[str, None] #None when global permission is passed
    body: dict
    id: str