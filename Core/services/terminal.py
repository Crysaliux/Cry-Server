from fastapi import FastAPI, Cookie, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from ..services.worker import Client, Group, Space, Room, Message, Role
from sqlalchemy import insert, select, update, delete
from sqlalchemy.exc import SQLAlchemyError
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime, timedelta, date, timezone
from .permgate import ClientValidator
from typing import Literal, TypeAlias
from functools import wraps
import jwt
import uuid

class Terminal:
    def __init__(
            self,
            hasher,
            session,
            ws,
            logger,
            algorithm,
        ):
        self.hasher = hasher
        self.session = session
        self.ws = ws
        self.logger = logger
        self.algorithm = algorithm