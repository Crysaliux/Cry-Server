from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from ..services.worker import Client, Group, Space, Room, Message, Role, Permission
from sqlalchemy import insert, select, update, delete
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime, timedelta, date
from .validators import ClientValidator
import jwt

class NewValidationRequest(BaseModel):
    username: str
    email: str
    password: str
    date_of_birth: str

class ExistingValidationRequest(BaseModel):
    email: str
    password: str

class ClientSessionValidationRequest(BaseModel):
    access_token: str

class Authentication:
    def __init__(self, hasher, worker_session, algorithm, access_key, oauth2, tepmlates: Jinja2Templates):
        self.access_key = access_key
        self.hasher = hasher
        self.worker_session = worker_session
        self.templates = tepmlates
        self.algorithm = algorithm
        self.oauth2 = oauth2
        self.router = APIRouter()

        self.__signup = self.worker_session(self.__signup)
        self.__login = self.worker_session(self.__login)
        self.__refresh_session = self.worker_session(self.__refresh_session)


    async def __signup(self, request, session):
        username_check_res = await session.execute(select(Client).where(Client.username == request.username))
        username_check = username_check_res.scalar_one_or_none()

        email_check_res = await session.execute(select(Client).where(Client.email == request.email))
        email_check = email_check_res.scalar_one_or_none()
        
        if email_check: return False, "EMAIL_EXISTS"
        if username_check: return False, "USERNAME_EXISTS" 
        datedelta = date.today() - date.fromisoformat(request.date_of_birth)
        if divmod(datedelta.total_seconds(), 31536000)[0] < 13: return False, "UNDERAGE"

        access_expires_at = datetime.now(datetime.timezone.utc) + timedelta(days=7)
        session_expires_at = datetime.now(datetime.timezone.utc) + timedelta(minutes=15)

        access_token = jwt.encode(
            {
                "username": request.username, 
                "id": request.id, 
                "exp": int(access_expires_at.timestamp())
            }, self.access_key, algorithms=[self.algorithm])
        
        session_token = jwt.encode(
            {
                "id": request.id, 
                "exp": int(session_expires_at.timestamp())
            }, self.access_key, algorithms=[self.algorithm])
        
        session.add(Client(
            username=request.username,
            password_hashed=self.hasher.hash(request.password),
            email=request.email,
            date_of_birth=date.fromisoformat(request.date_of_birth),
            token=access_token, 
            token_expires_at=datetime.now(datetime.timezone.utc) + timedelta(days=7), 
            id=request.id))
        
        await session.commit()
        return True, {"ACCESS_TOKEN": access_token, "SESSION_TOKEN": session_token}
    
    async def __login(self, request, session):
        client_res = await session.execute(select(Client).where(Client.email == request.email))
        client = client_res.scalar_one_or_none()

        if not client:
            return False, "WRONG_CREDENTIALS"
        
        if self.hasher.verify(client.hashed_password, request.password):
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

            return True, {"ACCESS_TOKEN": access_token, "SESSION_TOKEN": session_token}
        else:
            return False, "WRONG_CREDENTIALS"
        
    async def __refresh_session(self, request, session):
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = valid.access_is_valid(request.access_token, session)

        if not status:
            return False, "INVALID_OR_EXPIRED_ACCESS_TOKEN"
        
        session_expires_at = datetime.now(datetime.timezone.utc) + timedelta(minutes=15)
        session_token = jwt.encode(
        {
            "id": client.id, 
            "exp": int(session_expires_at.timestamp())
        }, self.access_key, algorithms=[self.algorithm])

        return True, {"SESSION_TOKEN": session_token}

    def router_tasks(self):
        @self.router.post("/signup", response_class=HTMLResponse)
        async def signup(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...), date_of_birth: str = Form(...)):
            status, response = await self.__signup(NewValidationRequest(username, email, password, date_of_birth))
            return JSONResponse(content={"status": status, "response": response}, status_code=201)

        @self.router.post("/login", response_class=HTMLResponse)
        async def login(request: Request, email: str = Form(...), password: str = Form(...)):
            status, response = await self.__login(ExistingValidationRequest(email, password))
            return JSONResponse(content={"status": status, "response": response}, status_code=201)
        
        @self.router.post("/refresh_session", response_class=HTMLResponse)
        async def validate_client_session(request: Request, access_token: str = Depends(self.oauth2)):
            status, response = await self.__refresh_session(ExistingValidationRequest(access_token))
            return JSONResponse(content={"status": status, "response": response}, status_code=201)