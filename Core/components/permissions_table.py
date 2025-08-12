from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class CreatePermissionsTable(BaseModel):
    group_id: str
    role_id: str
    room_id: str
    permissions: List[str]
    id: str

class UpdatePermissionsTable(BaseModel):
    group_id: str
    permissions: List[str]
    id: str