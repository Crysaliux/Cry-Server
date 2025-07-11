from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.security import APIKeyHeader
from .services.worker import Worker
from .services.listener import Listener
from .services.oauth import Authentication
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
        self.worker = Worker()
        self.client_server_origin = "http://localhost:5173"
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
        
        self.max_message_length = {"default": 1024, "premium": 3000} #characters
        self.max_image_size = 500 #pixels
        self.max_file_size = {"default": 10, "premium": 30} #megabytes

        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.oauth = Authentication(
            ws=self.worker.session, #ws - worker session
            tepmlates=self.templates, 
            hasher=self.hasher, 
            algorithm=self.algorithm, 
            access_key=self.server_access_key
        )
        self.oauth.router_tasks()

        self.listener = Listener(
            addr=(self.sv_host, self.sv_port),
            ws=self.worker.session, #ws - worker session
            oauth2=self.oauth2,
            tepmlates=self.templates, 
            hasher=self.hasher, 
            algorithm=self.algorithm, 
            storage_images_path=self.storage_images_path, 
            storage_files_path=self.storage_files_path, 
            max_image_size=self.max_image_size,
            max_file_size=self.max_file_size,
            max_message_length=self.max_message_length,
            client_server_origin=self.client_server_origin,
            access_key=self.server_access_key,
        )
        self.listener.router_tasks()

        self.include_router(self.auth.router, prefix="/oauth")
        self.include_router(self.listener.router, prefix="/api_hatch")

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