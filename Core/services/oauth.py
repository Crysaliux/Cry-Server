from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from ..services.worker import Client, Group, Space, Room, Message, Role
from sqlalchemy import insert, select, update, delete
from sqlalchemy.exc import SQLAlchemyError
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime, timedelta, date, timezone
from .validators import ClientValidator
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


class Authentication:
    def __init__(
            self, 
            hasher, 
            session, 
            ws,
            algorithm,
            access_key, 
            oauth2, 
        ):
        self.access_key = access_key
        self.hasher = hasher
        self.session = session
        self.ws = ws
        self.algorithm = algorithm
        self.oauth2 = oauth2
        self.router = APIRouter()

        self.__call_signup = self.ws(self.__signup, self.session)
        self.__call_login = self.ws(self.__login, self.session)
        self.__call_refresh_session = self.ws(self.__refresh_session, self.session)

    def __emit_api_error(self, index: str, target: str):
        return {
            "status": False, 
            "body": None, 
            "error": {"index": index, "target": target},
        }


    async def __signup(self, username: str, email: str, password: str, date_of_birth: date, session) -> dict:
        username_check_res = await session.execute(select(Client).where(Client.username == username))
        username_check = username_check_res.scalar_one_or_none()

        email_check_res = await session.execute(select(Client).where(Client.email == email))
        email_check = email_check_res.scalar_one_or_none()
        
        if email_check: return self.__emit_api_error("EMAIL_EXISTS", "client")
        if username_check: return self.__emit_api_error("USERNAME_EXISTS", "client")
        datedelta = date.today() - date.fromisoformat(date_of_birth)
        if divmod(datedelta.total_seconds(), 31536000)[0] < 13: self.__emit_api_error("UNDERAGE", "client")

        access_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        session_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        client_id = str(uuid.uuid4())
        access_token = jwt.encode(
            {
                "username": username, 
                "id": client_id,
                "exp": int(access_expires_at.timestamp())
            }, self.access_key, algorithm=self.algorithm)
        
        session_token = jwt.encode(
            {
                "id": client_id, 
                "exp": int(session_expires_at.timestamp())
            }, self.access_key, algorithm=self.algorithm)
        
        session.add(Client(
            username=username,
            password_hashed=self.hasher.hash(password),
            email=email,
            date_of_birth=date.fromisoformat(date_of_birth),
            token=access_token, 
            token_expires_at=access_expires_at.timestamp(), #check
            id=client_id))
        
        await session.commit()
        return {
            "status": True, 
            "body": {
                "access_token": access_token,
                "session_token": session_token,
            }, 
            "error": None,
        }
    
    async def __login(self, email: str, password: str, session) -> dict:
        client_res = await session.execute(select(Client).where(Client.email == email))
        client = client_res.scalar_one_or_none()

        if not client:
            return self.__emit_api_error("WRONG_CREDENTIALS", "client")
        
        if self.hasher.verify(client.hashed_password, password):
            access_expires_at = datetime.now(datetime.timezone.utc) + timedelta(days=7)
            session_expires_at = datetime.now(datetime.timezone.utc) + timedelta(minutes=15)

            access_token = jwt.encode(
            {
                "username": client.username, 
                "id": client.id, 
                "exp": int(access_expires_at.timestamp())
            }, self.access_key, algorithms=[self.algorithm])

            session_token = jwt.encode(
            {
                "id": client.id, 
                "exp": int(session_expires_at.timestamp())
            }, self.access_key, algorithms=[self.algorithm])

            return {
                "status": True, 
                "body": {
                    "access_token": access_token,
                    "session_token": session_token
                }, 
                "error": None,
            }
        else:
            return self.__emit_api_error("WRONG_CREDENTIALS", "client")
    
    async def __refresh_session(self, request, session) -> dict:
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = valid.access_is_valid(request.access_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_ACCESS_TOKEN", "client")
        
        session_expires_at = datetime.now(datetime.timezone.utc) + timedelta(minutes=15)
        session_token = jwt.encode(
        {
            "id": client.id, 
            "exp": int(session_expires_at.timestamp())
        }, self.access_key, algorithms=[self.algorithm])

        return {
            "status": True, 
            "body": {"session_token": session_token}, 
            "error": None,
        }

    def router_tasks(self):
        @self.router.post("/signup")
        async def signup(request: Request, payload: NewValidationRequest):
            return await self.__call_signup(payload.username, payload.email, payload.password, payload.date_of_birth)

        @self.router.post("/login")
        async def login(request: Request, payload: ExistingValidationRequest):
            return await self.__call_login(payload.email, payload.password)
        
        @self.router.post("/refresh_session")
        async def validate_client_session(request: Request, access_token: str = Depends(self.oauth2)): #automatically fetches from header bearer
            return await self.__call_refresh_session(access_token)