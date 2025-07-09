from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class NewRole(BaseModel):
    type: Literal['new_role']
    group_id: str
    name: str
    id: str