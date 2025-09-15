from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from socketio.async_redis_manager import AsyncRedisManager
from socketio.async_server import AsyncServer
from socketio.asgi import ASGIApp
from pydantic import BaseModel
from itertools import takewhile
from datetime import datetime
from random import uniform
from argon2 import PasswordHasher
import redis.asyncio as aioredis
from pathlib import Path
from Core.services import *
import subprocess
import threading
import asyncio
import uvicorn
import socketio
import logging
import json
import time
import ast
import os
import uuid
import re

#logging
logging.basicConfig(level=logging.DEBUG)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../config.json")) as conf:
    CONFIG = json.load(conf)

class Core(FastAPI):
    def __init__(self, host: str, port: int):
        super().__init__()
        self.sv_host = host
        self.sv_port = port
        self.heartbeat_interval = 10000 #milliseconds (10 seconds)
        self.client_server_origin = "http://localhost:5173"
        self.rm = AsyncRedisManager("redis://localhost:6379/0")
        self.storage_images_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../Storage/Images")
        self.storage_files_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../Storage/Files")
        self.gateway = AsyncServer(
            async_mode="asgi", 
            client_manager=self.rm, 
            logger=True, 
            cors_allowed_origins=self.client_server_origin
        ) #Disable logger later

        self.worker = Worker()
        self.cecchm = CECCHManager(self.gateway)
        
        self.server_access_key = str(uuid.uuid4())
        self.algorithm = "HS256" 
        self.login_expiration = 24 #hours
        self.hasher = PasswordHasher()
        self.oauth2 = OAuth2PasswordBearer(tokenUrl="token")
        
        self.message_load_batch_size = CONFIG["MESSAGE_LOAD_BATCH_SIZE"] #messages
        self.max_message_length = CONFIG["MAX_MESSAGE_LENGTH"] #characters
        self.max_image_size = CONFIG["MAX_IMAGE_SIZE"] #pixels
        self.max_file_size = CONFIG["MAX_FILE_SIZE"] #megabytes

        class PERMISSIONS:
            class _global:
                pass
            class _room_oriented:
                pass
        
        for name, code in CONFIG["PERMISSIONS"]["GLOBAL"].items():
            setattr(PERMISSIONS._global, name, 1 << code)

        for name, code in CONFIG["PERMISSIONS"]["ROOM_ORIENTED"].items():
            setattr(PERMISSIONS._room_oriented, name, 1 << code)

        self.perms = PERMISSIONS

        self.add_middleware(
            CORSMiddleware,
            allow_origins=[self.client_server_origin],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        #Initializing Listener module
        self.listener = Listener(
            addr=(self.sv_host, self.sv_port),
            session=self.worker.session,
            oauth2=self.oauth2,
            hasher=self.hasher, 
            algorithm=self.algorithm, 
            storage_images_path=self.storage_images_path, 
            storage_files_path=self.storage_files_path, 
            max_image_size=self.max_image_size,
            max_file_size=self.max_file_size,
            heartbeat_interval=self.heartbeat_interval,
            max_message_length=self.max_message_length,
            client_server_origin=self.client_server_origin,
            access_key=self.server_access_key,
            gateway=self.gateway,
            perms = self.perms,
        )

        #Initializing Oauth module
        self.oauth = Authentication(
            session=self.worker.session,
            hasher=self.hasher, 
            algorithm=self.algorithm, 
            access_key=self.server_access_key,
            oauth2=self.oauth2,
        )
        self.oauth.router_tasks()

        #Initializing APIListener module
        self.api_listener = APIListener(
            session=self.worker.session,
            oauth2=self.oauth2,
            algorithm=self.algorithm, 
            perms = self.perms,
            message_load_batch_size = self.message_load_batch_size,
        )
        self.api_listener.router_tasks()

        self.include_router(self.oauth.router, prefix="/oauth")
        self.include_router(self.api_listener.router, prefix="/api")

        self.main_routes = [
            {"path": "/", "func": self.__main, "method": ["GET"]},
        ]

        for route in self.main_routes:
            self.add_api_route(route["path"], route["func"], methods=route["method"], response_class=HTMLResponse)

        self.gt_app = ASGIApp(self.gateway, other_asgi_app=self, socketio_path="gateway")

        self.mount("/gateway", self.gt_app)
        self.mount("/images", StaticFiles(directory=self.storage_images_path), name="images")
        self.mount("/files", StaticFiles(directory=self.storage_files_path), name="files")

    
    def start(self):
        background = threading.Thread(target=lambda: self.__start_background())
        background.start()

        uvicorn.run(self, host=self.sv_host, port=self.sv_port, log_level="debug")

    def __start_background(self):
        asyncio.run(self.__gather_background())

    async def __gather_background(self):
        await asyncio.gather(self.__background_worker(), self.__background_ceecchm())


    async def __background_worker(self):
        await self.worker.start()

    async def __background_ceecchm(self):
        await self.cecchm.start()


    async def __main(self, request: Request):
        return self.templates.TemplateResponse("main.html", {"request": request})