from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class NewSpace(BaseModel):
    type: Literal['new_space']
    group_id: str
    creator_id: str
    name: str
    id: str

class UpdateSpace(BaseModel):
    type: Literal['update_space']
    group_id: str
    creator_id: str
    name: str
    id: str