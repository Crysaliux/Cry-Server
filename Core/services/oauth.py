from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from worker import executer, Client, Group, Space, Room, Message, Role, Permission
from sqlalchemy import insert, select, update, delete
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt

class ValidationRequest(BaseModel):
    username: str
    email: str
    password: str

class Authentication:
    def __init__(self, hasher, ws, algorithm, access_key, tepmlates: Jinja2Templates):
        self.access_key = access_key
        self.hasher = hasher
        self.ws = ws
        self.templates = tepmlates
        self.algorithm = algorithm
        self.router = APIRouter()

    def __create_token(self, data: dict):
        encdat = data.copy()
        encoded = jwt.encode(encdat, self.access_key, algorithm=self.algorithm)
        return encoded
    
    @executer
    async def __validate_client(self, request, session):
        username_check, mail_check = await session.execute(select(Client).where(Client.username == request.username)), await session.execute(select(Client).where(Client.email == request.email))
        if mail_check is not None: return False, "User with this email already exists! :0"
        if username_check is not None: return False, "This username is already take, try another! :3"
        token = jwt.encode({"username": request.username, "id": request.id, "type": "client-oriented"}, self.access_key, algorithm=self.algorithm)
        session.add(Client(username=request.username, password_hashed=self.hasher.hash(request.password), email=request.email, token=token, token_expires_at=datetime.now(datetime.timezone.utc) + timedelta(days=7), id=request.id))
        return True, {"token": token}

    def router_tasks(self):
        @self.router.post("/receive_token", response_class=HTMLResponse)
        async def receive_token(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...)):
            status, response = await self.__validate_client(ValidationRequest(username, email, password))
            if status:
                ...
            return JSONResponse(content={"status": status, "response": response}, status_code=201)


        @self.router.post("/submit/login", response_class=HTMLResponse) #To be completely refactored.
        async def sign_up(request: Request, form: Login):
            client = await self.dmp.fetch_client_by_mail(form.email)
            if client is None or not self.hasher.verify(client.password, form.password):
                raise HTTPException(status_code=400, detail=f"Wrong password or mail, please try again!")
            token = self.__create_token({"id": client.id, "username": client.username})
            return JSONResponse(content={"redirect": f"/client/{client.id}", "token": token}, status_code=201)