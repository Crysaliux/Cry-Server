import socketio
import asyncio
import uuid

class CCHSManager:
    def __init__(self, gateway: socketio.AsyncServer, active_servers: int = 10):
        self.gateway = gateway
        self.active_servers = active_servers
        self.cchs_all = []

    def start(self):
        for _ in range(self.active_servers):
            instance_ = CCHServer(uuid.uuid4())
            self.cchs_all.append(instance_)

    def load(self, rooms: list, sid):
        dists = [[] for _ in range(self.active_servers)]
        for _, room in enumerate(rooms): dists[_ % self.active_servers].append(room)
        for server, dist in zip(self.cchs_all, dists): server.delegate(dist, sid)

class CCHServer:
    def __init__(self, id: str, gateway: socketio.AsyncServer):
        self.id = id
        self.gateway = gateway

    def delegate(self, rooms: list, sid):
        asyncio.create_task(self.__delegate(rooms, sid))

    async def __delegate(self, rooms: list, sid):
        if rooms:
            for room in rooms: await self.gateway.enter_room(sid, room)