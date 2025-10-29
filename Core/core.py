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
import sys


#logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

LOGGER = logging.getLogger("system_logger")
LOGGER.setLevel(logging.DEBUG)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../config.json")) as conf:
    CONFIG = {key: value for key, value in json.load(conf).items() if not key.startswith("_")}


class Core(FastAPI):
    def __init__(self):
        super().__init__()
        self.sv_host = CONFIG["SERVER_HOST"]
        self.sv_port = CONFIG["SERVER_PORT"]
        self.client_server_origin = f"http://{CONFIG['CLIENT_SERVER_HOST']}:{CONFIG['CLIENT_SERVER_PORT']}"
        self.rm = AsyncRedisManager(f"redis:{CONFIG['REDIS_SERVER_HOST']}:{CONFIG['REDIS_SERVER_PORT']}/0") 
        self.storage_images_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG["IMAGE_STORAGE_PATH"])
        self.storage_files_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG["FILE_STORAGE_PATH"])
        self.gateway = AsyncServer(
            async_mode=CONFIG["GATEWAY_ASYNC_MODE"], 
            client_manager=self.rm, 
            logger=CONFIG["GATEWAY_LOGGER"], 
            cors_allowed_origins=self.client_server_origin,
        ) #Disable logger later

        self.worker = Worker()
        self.cecchm = CECCHManager(self.gateway)
        
        self.server_access_key = str(uuid.uuid4())
        self.algorithm = CONFIG["ENCRYPTION_ALGORITHM"]
        self.login_expiration = 24 #days
        self.hasher = PasswordHasher()
        self.oauth2 = OAuth2PasswordBearer(tokenUrl=CONFIG["BEARER_TOKEN_URL"])
        
        self.message_load_batch_size = CONFIG["MESSAGE_LOAD_BATCH_SIZE"]
        self.max_message_length = CONFIG["MAX_MESSAGE_LENGTH"]
        self.max_image_size = CONFIG["MAX_IMAGE_SIZE"]
        self.max_file_size = CONFIG["MAX_FILE_SIZE"]

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
            ws=worker_session,
            logger=LOGGER,
            oauth2=self.oauth2,
            hasher=self.hasher, 
            algorithm=self.algorithm, 
            storage_images_path=self.storage_images_path, 
            storage_files_path=self.storage_files_path, 
            max_image_size=self.max_image_size,
            max_file_size=self.max_file_size,
            max_message_length=self.max_message_length,
            client_server_origin=self.client_server_origin,
            access_key=self.server_access_key,
            gateway=self.gateway,
            perms = self.perms,
        )

        #Initializing Oauth module
        self.oauth = Authentication(
            session=self.worker.session,
            ws=worker_session,
            logger=LOGGER,
            hasher=self.hasher, 
            algorithm=self.algorithm, 
            access_key=self.server_access_key,
            oauth2=self.oauth2,
        )
        self.oauth.router_tasks()

        #Initializing APIListener module
        self.api_listener = APIListener(
            addr=(self.sv_host, self.sv_port),
            session=self.worker.session,
            ws=worker_session,
            logger=LOGGER,
            oauth2=self.oauth2,
            algorithm=self.algorithm, 
            perms = self.perms,
            access_key=self.server_access_key,
            message_load_batch_size = self.message_load_batch_size,
            client_server_origin=self.client_server_origin,
            storage_files_path=self.storage_files_path,
            storage_images_path=self.storage_images_path,
        )
        self.api_listener.router_tasks()

        self.include_router(self.oauth.router, prefix=CONFIG["OAUTH_PATH"])
        self.include_router(self.api_listener.router, prefix=CONFIG["API_PATH"])

        self.main_routes = [
            {"path": "/", "func": self.__main, "method": ["GET"]},
        ]

        for route in self.main_routes:
            self.add_api_route(route["path"], route["func"], methods=route["method"], response_class=HTMLResponse)

        self.gt_app = ASGIApp(self.gateway, other_asgi_app=self, socketio_path=CONFIG["GATEWAY_PATH"])

        self.mount(CONFIG["GATEWAY_PATH"], self.gt_app)
        self.mount(CONFIG["STATIC_IMAGE_PATH"], StaticFiles(directory=self.storage_images_path), name="images")
        self.mount(CONFIG["STATIC_FILE_PATH"], StaticFiles(directory=self.storage_files_path), name="files")

    
    def start(self):
        background = threading.Thread(target=lambda: self.__start_background())
        background.start()

        uvicorn.run(self, host=self.sv_host, port=self.sv_port, log_level="debug")

    def __start_background(self):
        asyncio.run(self.__gather_background())

    async def __gather_background(self):
        await asyncio.gather(self.__background_worker(), self.__background_ceecchm())

    #Background services
    async def __background_worker(self):
        await self.worker.start()

    async def __background_ceecchm(self):
        await self.cecchm.start()


    async def __main(self, request: Request):
        return self.templates.TemplateResponse("main.html", {"request": request})