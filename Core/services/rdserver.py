"""
The rdmserver module handles redis database requests.

data = {
    "name": "Sillyrubber",
    "id": 1234,
}

redis_data_model = RedisData_model(**data)

v0.0.1 beta
"""

from redis.asyncio import Redis, ConnectionError, RedisError
from pydantic import BaseModel, ValidationError

class RedisDataModel(BaseModel):
    name: str
    details: dict

    @classmethod
    def from_redis(cls, json_string: str):
        return cls.model_validate_json(json_string)

    def to_redis(self) -> str:
        return self.model_dump_json()


class RDServer:
    def __init__(self, host='localhost', port=6379, db=0):
        self.host = host
        self.port = port
        self.db = db
        self.r = None

    async def connect(self) -> tuple[bool, None, str | None]:
        try:
            self.r = Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)
            await self.r.ping()
        except ConnectionError as e:
            self.r = None
            raise(e)

    async def set_(self, key: str, data_model: RedisDataModel) -> tuple[bool, None, str | None]:
        if not self.r: #Cannot set data: Not connected to Redis.
            return False, None, "200"
        try:
            json_string = data_model.to_redis()
            await self.r.set(key, json_string)
            return True, None, None
        except RedisError: #Redis error setting data for key '{key}': {e}
            return False, None, "201"

    async def get_(self, key: str) -> tuple[bool, RedisDataModel | None, str | None]:
        if not self.r:
            return False, None, "200"
        try:
            json_string = await self.r.get(key)
            if json_string:
                try:
                    return True, RedisDataModel.from_redis(json_string), None
                except ValidationError: #Pydantic validation error for key '{key}': {e}. Data might be corrupted or malformed
                    return False, None, "202"
            else:
                return True, None, None
        except RedisError: #Redis error getting data for key '{key}': {e}
            return False, None, "203"

    async def update_(self, key: str, new_data: dict) -> tuple[bool, None, str | None]:
        if not new_data: #"Update skipped: new_data dictionary is empty."
            return False, "204"

        if not self.r:
            return False, "200"

        status, existing_model, error = await self.get_data(key)
        if not status:
            return False, error

        if existing_model:
            try:
                existing_model.details.update(new_data)
                set_status, _, error = await self.set_data(key, existing_model)
                if set_status:
                    return True, None
                else: #Failed to save updated data for key '{key}': {set_error}
                    return False, error
            except Exception as e:
                return False, "205"
        else: #Cannot update. No existing data found for key '{key}'.
            return False, "206"
        
    async def delete_(self, key: str) -> tuple[bool, None, tuple[str, str] | None]: #status, error
        if not self.r:
            return False, "200"
        try:
            result = await self.r.delete(key)
            if result == 1:
                return True, None
            else:
                return False, "207"
        except RedisError:
            return False, "203"
        except Exception as e:
            return False, "208"