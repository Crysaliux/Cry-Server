"""
The emitter module handles real time media exchange and broadcasting.

v0.0.1 beta
"""
from socketio.async_server import AsyncServer

class Emitter:
    def __init__(self, socket: AsyncServer):
        self.s = socket
        self.body = {}
        self.cluster_id = ""

    def init_(self, cluster_id: str, body: dict) -> None: #Clear typing later.
        self.body, self.cluster_id = body, cluster_id

    async def broadcast(self, event: str, status: bool = True, error: str | None = None):
        await self.gateway.emit(event, {
            "status": status,
            "body": self.body,
            "error": error,
        }, room=self.cluster_id)