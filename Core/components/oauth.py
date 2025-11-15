from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal

class Login(BaseModel):
    email: str
    password: str

class Signup(BaseModel):
    username: str
    email: str
    password: str
    date_of_birth: str