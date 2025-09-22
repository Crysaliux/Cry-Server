from sqlalchemy import insert, select, update, delete
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from ...services.worker import Client
from jwt import ExpiredSignatureError, InvalidTokenError
from typing import Literal, Any, Union, TypeAlias
import jwt


#Return types
ReType: TypeAlias = tuple[Literal[False], None] | tuple[bool, Client]


class ClientValidator:
    def __init__(self, access_key, algorithm, logger = None):
        self.access_key = access_key
        self.algorithm = algorithm
        self.logger = logger #debug

    async def refresh_token_is_valid(self, refresh_token: str, session) -> ReType:
        try:
            payload = jwt.decode(refresh_token, self.access_key, algorithm=self.algorithm)
            username, id, expires_at = payload["username"], payload["id"], payload["exp"]
            client_res = await session.execute(select(Client).options(
                selectinload(Client.groups),
            ).where(
                Client.username == username,
                Client.id == id, 
                Client.token == refresh_token))
            client = client_res.scalar_one_or_none()
        
            if not client:
                return False, None
        
            return datetime.now(timezone.utc) <= datetime.fromtimestamp(expires_at, tz=timezone.utc), client
        except (ExpiredSignatureError, InvalidTokenError):
            return False, None
    
    async def access_token_is_valid(self, access_token: str, session) -> ReType:
        try:
            payload = jwt.decode(access_token, self.access_key, algorithm=self.algorithm)
            id, expires_at = payload["id"], payload["exp"]
            client_res = await session.execute(select(Client).options(
                selectinload(Client.groups),
            ).where(Client.id == id))
            client = client_res.scalar_one_or_none()

            self.logger.info("Hello!")

            if not client:
                return False, None

            return datetime.now(timezone.utc) <= datetime.fromtimestamp(expires_at, tz=timezone.utc), client
        except (ExpiredSignatureError, InvalidTokenError):
            return False, None
        
    async def running_session_is_valid(self, access_token: str) -> bool:
        try:
            payload = jwt.decode(access_token, self.access_key, algorithm=self.algorithm)
            _, expires_at = payload["id"], payload["exp"]

            return datetime.now(timezone.utc) <= datetime.fromtimestamp(expires_at, tz=timezone.utc)
        except (ExpiredSignatureError, InvalidTokenError):
            return False

"""
Creating tokens:

expires_at = datetime.now(datetime.timezone.utc) + timedelta(minutes=15)

payload = {
    "username: ...,
    "id": ...,
    "exp": int(expires_at.timestamp()),
    "iat": int(datetime.utcnow().timestamp()),
}

session tokens do not have username or id!
"""