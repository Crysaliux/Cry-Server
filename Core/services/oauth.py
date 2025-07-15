from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from worker import executer, Client, Group, Space, Room, Message, Role, Permission
from sqlalchemy import insert, select, update, delete
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt

class NewValidationRequest(BaseModel):
    username: str
    email: str
    password: str

class ExistingValidationRequest(BaseModel):
    email: str
    password: str
    token: str

class Authentication:
    def __init__(self, hasher, ws, algorithm, access_key, oauth2, tepmlates: Jinja2Templates):
        self.access_key = access_key
        self.hasher = hasher
        self.ws = ws
        self.templates = tepmlates
        self.algorithm = algorithm
        self.oauth2 = oauth2
        self.router = APIRouter()
    
    @executer
    async def __validate_new_client(self, request, session):
        username_check, mail_check = await session.execute(select(Client).where(Client.username == request.username)), await session.execute(select(Client).where(Client.email == request.email))
        if mail_check is not None: return False, "User with this email already exists! :0"
        if username_check is not None: return False, "This username is taken, try another! :3"
        token = jwt.encode({"username": request.username, "id": request.id, "type": "client-oriented"}, self.access_key, algorithm=self.algorithm)
        session.add(Client(username=request.username, password_hashed=self.hasher.hash(request.password), email=request.email, token=token, token_expires_at=datetime.now(datetime.timezone.utc) + timedelta(days=7), id=request.id))
        return True, {"token": token}
    
    @executer
    async def __validate_existing_client(self, request, session):
        payload = jwt.decode(request.token, self.access_key, algorithm=self.algorithm)
        username, id = payload["username"], payload["id"]
        client = session.execute(select(Client).where(Client.username == username, Client.email == request.email, Client.id == id, Client.token == request.token))
        if client is not None: return True, "Access granted"
        return False, "You've entered wrong credentials!"

    def router_tasks(self):
        @self.router.post("/validate_new_client", response_class=HTMLResponse)
        async def validate_new_client(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...)):
            status, response = await self.__validate_new_client(NewValidationRequest(username, email, password))
            return JSONResponse(content={"status": status, "response": response}, status_code=201)

        @self.router.post("/validate_existing_client", response_class=HTMLResponse)
        async def validate_existing_client(request: Request, email: str = Form(...), password: str = Form(...), token: str = Depends(self.oauth2)):
            status, response = await self.__validate_existing_client(ExistingValidationRequest(email, password, token))
            return JSONResponse(content={"status": status, "response": response}, status_code=201)