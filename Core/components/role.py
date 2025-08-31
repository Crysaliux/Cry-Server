from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class CreateRole(BaseModel):
    group_id: str
    name: str
    id: str

class UpdateRole(BaseModel):
    group_id: str
    name: str
    color:str
    global_permissions: list[str]
    id: str

class DeleteRole(BaseModel):
    group_id: str
    id: str