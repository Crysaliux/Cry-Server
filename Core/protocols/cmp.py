import asyncio
import json

class CMP:
    def __init__(self):
        self.active_connections = {}
        self.proc_lock = asyncio.Lock()

    async def connect(self, client_id: int, socket: dict):
        async with self.proc_lock:
            self.active_connections[client_id] = socket

    async def disconnect(self, client_id: int):
        async with self.proc_lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
    
    async def broadcast(self, request, clients): #clients - instances of Client.
        async with self.proc_lock:
            for client in clients:
                try:
                    await self.active_connections[client.id].send_text(json.dumps(request))
                except: pass
    
    async def notify(self, request, id):
        async with self.proc_lock:
            try:
                await self.active_connections[id].send_text(json.dumps(request))
                return True
            except: return False