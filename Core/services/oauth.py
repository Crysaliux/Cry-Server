from fastapi import FastAPI, Cookie, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from ..services.worker import Client, Group, Space, Room, Message, Role
from sqlalchemy import insert, select, update, delete
from sqlalchemy.exc import SQLAlchemyError
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime, timedelta, date, timezone
from .validators import ClientValidator
from typing import Literal, TypeAlias
from functools import wraps
import jwt
import uuid

class NewValidationRequest(BaseModel):
    username: str
    email: str
    password: str
    date_of_birth: str

class ExistingValidationRequest(BaseModel):
    email: str
    password: str


#Emission types
EmitError: TypeAlias = dict[str, Literal[False] | None | dict[str, str]]
EmitCommon: TypeAlias = dict[str, bool | str | None]



class Authentication:
    def __init__(
            self, 
            hasher, 
            session, 
            ws,
            logger,
            algorithm,
            access_key,
            oauth2, 
        ):
        self.access_key = access_key
        self.hasher = hasher
        self.session = session
        self.ws = ws
        self.logger = logger
        self.algorithm = algorithm
        self.oauth2 = oauth2
        self.router = APIRouter()

        self._call_signup = self.ws(self.__signup, self.session)
        self._call_login = self.ws(self.__login, self.session)
        self._call_refresh_session = self.ws(self.__refresh_session, self.session)

    def __emit_api_error(self, index: str, target: str) -> EmitError:
        return {
            "status": False, 
            "body": None, 
            "error": {"index": index, "target": target},
        }


    async def __signup(self, response: Response, username: str, email: str, password: str, date_of_birth: date, session) -> EmitError | EmitCommon:
        username_check_res = await session.execute(select(Client).where(Client.username == username))
        username_check = username_check_res.scalar_one_or_none()

        email_check_res = await session.execute(select(Client).where(Client.email == email))
        email_check = email_check_res.scalar_one_or_none()
        
        if email_check: return self.__emit_api_error("EMAIL_EXISTS", "client")
        if username_check: return self.__emit_api_error("USERNAME_EXISTS", "client")
        datedelta = date.today() - date.fromisoformat(date_of_birth)
        if divmod(datedelta.total_seconds(), 31536000)[0] < 13: self.__emit_api_error("UNDERAGE", "client")

        refresh_expires_at = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        refresh_expires_in = int(timedelta(days=7).total_seconds())

        access_expires_at = int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp())

        client_id = str(uuid.uuid4())
        refresh_token = jwt.encode(
            {
                "username": username, 
                "id": client_id,
                "exp": refresh_expires_at
            }, self.access_key, algorithm=self.algorithm)
        
        access_token = jwt.encode(
            {
                "id": client_id, 
                "exp": access_expires_at
            }, self.access_key, algorithm=self.algorithm)
        
        session.add(Client(
            username=username,
            password_hashed=self.hasher.hash(password),
            email=email,
            date_of_birth=date.fromisoformat(date_of_birth),
            token=refresh_token, 
            id=client_id))
        await session.commit()

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite=None,
            max_age=refresh_expires_in,
        )

        return {
            "status": True, 
            "body": {
                "access_token": access_token,
            }, 
            "error": None,
        }
    
    async def __login(self, response: Response, email: str, password: str, session) -> EmitError | EmitCommon:
        client_res = await session.execute(select(Client).where(Client.email == email))
        client = client_res.scalar_one_or_none()

        if not client:
            return self.__emit_api_error("WRONG_CREDENTIALS", "client")
        
        if self.hasher.verify(client.hashed_password, password):
            refresh_expires_at = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
            refresh_expires_in = int(timedelta(days=7).total_seconds())

            access_expires_at = int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp())

            refresh_token = jwt.encode(
            {
                "username": client.username, 
                "id": client.id, 
                "exp": refresh_expires_at
            }, self.access_key, algorithms=[self.algorithm])

            access_token = jwt.encode(
            {
                "id": client.id, 
                "exp": access_expires_at
            }, self.access_key, algorithms=[self.algorithm])

            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite=None,
                max_age=refresh_expires_in,
            )

            return {
                "status": True, 
                "body": {
                    "access_token": access_token,
                }, 
                "error": None,
            }
        else:
            return self.__emit_api_error("WRONG_CREDENTIALS", "client")
    
    async def __refresh_session(self, refresh_token, session) -> EmitError | EmitCommon:
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = valid.refresh_token_is_valid(refresh_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_REFRESH_TOKEN", "client")
        
        access_expires_at = int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp())

        access_token = jwt.encode(
        {
            "id": client.id, 
            "exp": access_expires_at
        }, self.access_key, algorithms=[self.algorithm])

        return {
            "status": True, 
            "body": {"access_token": access_token},
            "error": None,
        }

    def router_tasks(self):
        @self.router.post("/signup")
        async def signup(response: Response, payload: NewValidationRequest):
            return await self._call_signup(response, payload.username, payload.email, payload.password, payload.date_of_birth)

        @self.router.post("/login")
        async def login(response: Response, payload: ExistingValidationRequest):
            return await self._call_login(response, payload.email, payload.password)
        
        @self.router.post("/refresh_session")
        async def validate_client_session(refresh_token: str = Cookie(...)):
            return await self._call_refresh_session(refresh_token)