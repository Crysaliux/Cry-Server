from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from ..services.worker import executer, Client, Group, Space, Room, Message, Role, Permission
from sqlalchemy import insert, select, update, delete
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime, timedelta, date
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
    token: str

class Authentication:
    def __init__(self, hasher, worker_session, algorithm, access_key, oauth2, tepmlates: Jinja2Templates):
        self.access_key = access_key
        self.hasher = hasher
        self.worker_session = worker_session
        self.templates = tepmlates
        self.algorithm = algorithm
        self.oauth2 = oauth2
        self.router = APIRouter()
    
    @executer
    async def __validate_new_client(self, request, session):
        username_check, mail_check = await session.execute(select(Client).where(
            Client.username == request.username)), await session.execute(select(Client).where(
                Client.email == request.email))
        if mail_check is not None: return False, "User with this email already exists! :0"
        if username_check is not None: return False, "This username is taken, try another! :3"
        datedelta = date.today() - date.fromisoformat(request.date_of_birth)
        if divmod(datedelta.total_seconds(), 31536000)[0] < 13: return False, "You must at least 13 years old to use ...!"
        token = jwt.encode({"username": request.username, "id": request.id, "type": "client-oriented"}, self.access_key, algorithm=self.algorithm)
        session.add(Client(
            username=request.username,
            password_hashed=self.hasher.hash(request.password),
            email=request.email,
            date_of_birth=date.fromisoformat(request.date_of_birth),
            token=token, 
            token_expires_at=datetime.now(datetime.timezone.utc) + timedelta(days=7), 
            id=request.id))
        await session.commit()
        return True, {"token": token}
    
    @executer
    async def __validate_existing_client(self, request, session):
        client = await session.execute(select(Client).where(Client.email == request.email))
        if client is not None: 
            if self.hasher.verify(client.hashed_password, request.password):
                token = jwt.encode({"username": client.username, "id": client.id, "type": "client-oriented"}, self.access_key, algorithm=self.algorithm)
                return True, {"token": token}
        return False, "You've entered wrong credentials!"
    
    @executer
    async def __validate_client_session(self, request, session):
        payload = jwt.decode(request.token, self.access_key, algorithm=self.algorithm)
        username, id = payload["username"], payload["id"]
        client = await session.execute(select(Client).where(
            Client.username == username,
            Client.id == id, 
            Client.token == request.token))
        if client is not None: 
            if datetime.now(datetime.timezone.utc) > client.token_expires_at:
                return False, "Session has expired"
            return True, "Session active, all good"
        return False, "Wrong session, closing connection"

    def router_tasks(self):
        @self.router.post("/validate_new_client", response_class=HTMLResponse)
        async def validate_new_client(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...), date_of_birth: str = Form(...)):
            status, response = await self.__validate_new_client(NewValidationRequest(username, email, password))
            return JSONResponse(content={"status": status, "response": response}, status_code=201)

        @self.router.post("/validate_existing_client", response_class=HTMLResponse)
        async def validate_existing_client(request: Request, email: str = Form(...), password: str = Form(...)):
            status, response = await self.__validate_existing_client(ExistingValidationRequest(email, password))
            return JSONResponse(content={"status": status, "response": response}, status_code=201)
        
        @self.router.post("/validate_client_session", response_class=HTMLResponse)
        async def validate_client_session(request: Request, token: str = Depends(self.oauth2)):
            status, response = await self.__validate_client_session(ExistingValidationRequest(token))
            return JSONResponse(content={"status": status, "response": response}, status_code=201)