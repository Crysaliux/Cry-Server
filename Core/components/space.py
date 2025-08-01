from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class CreateSpace(BaseModel):
    group_id: str
    name: str
    id: str

class UpdateSpace(BaseModel):
    group_id: str
    name: str
    id: str

class DeleteSpace(BaseModel):
    group_id: str
    id: str