from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.security import APIKeyHeader
from .protocols.dmp import DMP
from .protocols.cmp import CMP
from .api_modules.authentication import Authentication
from .api_modules.clientinterface import Clientinterface
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from itertools import takewhile
from datetime import datetime
from random import uniform
from argon2 import PasswordHasher
from pathlib import Path
import subprocess
import threading
import asyncio
import uvicorn
import json
import time
import ast
import os
import uuid
import re


class Core(FastAPI):
    def __init__(self, host: str, port: int):
        super().__init__()
        self.sv_host = host
        self.sv_port = port
        self.dmp = DMP()
        self.cmp = CMP()
        self.storage_images_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../Storage/Images")
        self.storage_files_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../Storage/Files")
        self.templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"))
        self.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")), name="static")
        self.mount("/images", StaticFiles(directory=self.storage_images_path), name="images")
        self.mount("/files", StaticFiles(directory=self.storage_files_path), name="files")
        
        self.server_access_key = str(uuid.uuid4())
        self.algorithm = "HS256" 
        self.login_expiration = 24 #hours
        self.hasher = PasswordHasher()
        self.oauth2 = OAuth2PasswordBearer(tokenUrl="token")

        self.max_image_size = 500

        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.auth = Authentication(
            dmp=self.dmp, 
            tepmlates=self.templates, 
            hasher=self.hasher, 
            algorithm=self.algorithm, 
            access_key=self.server_access_key
        )
        self.auth.router_tasks()

        self.client = Clientinterface(
            cmp=self.cmp,
            addr=(self.sv_host, self.sv_port),
            dmp=self.dmp,
            tepmlates=self.templates, 
            hasher=self.hasher, 
            algorithm=self.algorithm, 
            storage_images_path=self.storage_images_path, 
            storage_files_path=self.storage_files_path, 
            max_image_size=self.max_image_size,
            access_key=self.server_access_key
        )
        self.client.router_tasks()

        self.include_router(self.auth.router, prefix="/auth")
        self.include_router(self.client.router, prefix="/client")

        self.main_routes = [
            {"path": "/", "func": self.__main, "method": ["GET"]},
        ]

        for route in self.main_routes:
            self.add_api_route(route["path"], route["func"], methods=route["method"], response_class=HTMLResponse)

    
    def start(self):
        background = threading.Thread(target=lambda: self.__start_background())
        background.start()

        uvicorn.run(self, host=self.sv_host, port=self.sv_port, log_level="debug")

    def __start_background(self):
        asyncio.run(self.__background())

    async def __background(self):
        await self.dmp.start()

    async def __main(self, request: Request):
        return self.templates.TemplateResponse("main.html", {"request": request})