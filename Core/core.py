from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from socketio.async_server import AsyncServer
from socketio.async_redis_manager import AsyncRedisManager
from passlib.context import CryptContext
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from itertools import takewhile
from datetime import datetime
from random import uniform
from argon2 import PasswordHasher
from redis.asyncio import Redis
from pathlib import Path
from Core.services import *
from Core.services.permgate import *
import configparser
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


os.chdir("../")

#logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

LOGGER = logging.getLogger("system_logger")
LOGGER.setLevel(logging.DEBUG)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "core_config.json")) as conf:
    CONFIG = {key: value for key, value in json.load(conf).items() if not key.startswith("_")}


class Core(FastAPI):
    def __init__(self):
        super().__init__()
        self.root_path = os.getcwd()
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(self.root_path, "Core/core.conf"))
        self.sv_host = self.config["coreserver"]["host"]
        self.sv_port = self.config["coreserver"]["port"]
        self.client_server_origin = f"http://{self.config["clientserver"]["host"]}:{self.config["clientserver"]["port"]}"
        self.rdserver = RDServer(
            host=self.config["rdsserver"]["host"],
            port=self.config["rdsserver"]["port"],
        )

        self.smger = AsyncRedisManager(
            url=f"redis://{self.config["rdsserver"]["host"]}:{self.config["rdsserver"]["port"]}/1",
            channel="socket",
        ) 
        self.socket = AsyncServer(
            async_mode=self.config["socket"]["mode"], 
            client_manager=self.smger, 
            logger=self.config.getboolean("socket", "logger"),
            cors_allowed_origins=self.client_server_origin
        )
        
        self.storage_images_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.config["storage"]["images"])
        self.storage_files_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.config["storage"]["files"])
        self.group_cluster_index = self.config["clusters"]["groups"]
        self.room_cluster_index = self.config["clusters"]["rooms"]

        self.worker = Worker()
        self.pg = Permgate()
        
        self.server_access_key = str(uuid.uuid4())
        #self.algorithm = CONFIG["ENCRYPTION_ALGORITHM"]
        self.login_expiration = self.config.getint("oauth", "login_expiration")
        self.session_expiration = self.config.getint("oauth", "session_expiration")
        self.heartbeat_delta = (self.session_expiration // 3) * 2  #must be in config!!!
        self.hasher = PasswordHasher()
        
        self.message_load_batch_size = self.config.getint("batchloading", "messages")
        self.member_load_batch_size = self.config.getint("batchloading", "members")
        self.max_message_length = self.config.getint("limits", "message_length")
        self.max_image_size = self.config.getint("limits", "image_size")
        self.max_file_size = self.config.getint("limits", "file_size")


        self.add_middleware(
            CORSMiddleware,
            allow_origins=[self.client_server_origin],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        #Initializing Gateway module
        self.gateway = Gateway(
            addr=(self.sv_host, self.sv_port),
            session=self.worker.session,
            rdserver=self.rdserver,
            ws=worker_session,
            s=self.socket,
            logger=LOGGER,
            hasher=self.hasher, 
            algorithm=self.algorithm, 
            storage_images_path=self.storage_images_path, 
            storage_files_path=self.storage_files_path, 
            max_image_size=self.max_image_size,
            max_file_size=self.max_file_size,
            max_message_length=self.max_message_length,
            message_load_batch_size=self.message_load_batch_size,
            member_load_batch_size=self.member_load_batch_size,
            client_server_origin=self.client_server_origin,
            access_key=self.server_access_key,
            login_expiration=self.login_expiration,
            session_expiration=self.session_expiration,
            heartbeat_delta=self.heartbeat_delta,
            room_cluster_index=self.room_cluster_index,
            group_cluster_index=self.group_cluster_index,
            pg=self.pg,
        )

        self.gateway.router_tasks()
        self.include_router(self.gateway.router, prefix=CONFIG["GATEWAY_PATH"])

        self.main_routes = [
            {"path": "/", "func": self.__main, "method": ["GET"]},
        ]

        for route in self.main_routes:
            self.add_api_route(route["path"], route["func"], methods=route["method"], response_class=HTMLResponse)

        self.mount(CONFIG["STATIC_IMAGE_PATH"], StaticFiles(directory=self.storage_images_path), name="images")
        self.mount(CONFIG["STATIC_FILE_PATH"], StaticFiles(directory=self.storage_files_path), name="files")

    
    def start(self):
        background = threading.Thread(target=lambda: self.__load())
        background.start()

        uvicorn.run(self, host=self.sv_host, port=self.sv_port, log_level="debug")

    def __load(self):
        asyncio.run(self.__gather_processes())

    async def __gather_processes(self):
        await asyncio.gather(
            self.__worker(),
            self.__rdserver(),
        )

    async def __worker(self):
        await self.worker.start()

    async def __rdserver(self):
        await self.rdserver.connect()


    async def __main(self, request: Request):
        return self.templates.TemplateResponse("main.html", {"request": request})