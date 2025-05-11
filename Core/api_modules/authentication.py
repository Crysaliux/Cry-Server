from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import jwt

class SignUp(BaseModel):
    username: str
    email: str
    password: str

class Login(BaseModel):
    email: str
    password: str

class Authentication:
    def __init__(self, hasher, dmp, algorithm, access_key, tepmlates: Jinja2Templates):
        self.access_key = access_key
        self.hasher = hasher
        self.dmp = dmp
        self.templates = tepmlates
        self.algorithm = algorithm
        self.router = APIRouter()

    def __create_token(self, data: dict):
        encdat = data.copy()
        encoded = jwt.encode(encdat, self.access_key, algorithm=self.algorithm)
        return encoded

    def router_tasks(self): #To be completely refactored.
        @self.router.post("/submit/signup", response_class=HTMLResponse)
        async def sign_up(request: Request, form: SignUp):
            created, id = await self.dmp.create_client(form.username, form.email, self.hasher.hash(form.password))
            if not created:
                raise HTTPException(status_code=400, detail=f"User with email {form.email} already exists!")
            token = self.__create_token({"id": id, "username": form.username})
            return JSONResponse(content={"redirect": f"/client/{id}", "token": token}, status_code=201)
        
        @self.router.post("/submit/login", response_class=HTMLResponse)
        async def sign_up(request: Request, form: Login):
            client = await self.dmp.fetch_client_by_mail(form.email)
            if client is None or not self.hasher.verify(client.password, form.password):
                raise HTTPException(status_code=400, detail=f"Wrong password or mail, please try again!")
            token = self.__create_token({"id": client.id, "username": client.username})
            return JSONResponse(content={"redirect": f"/client/{client.id}", "token": token}, status_code=201)