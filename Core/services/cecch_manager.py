from socketio.async_server import AsyncServer
from sqlalchemy.orm.collections import InstrumentedList
from typing import NoReturn
import asyncio
import uuid
#Client Event Clusters Connection Handling Manager

class CECCHManager:
    def __init__(self,
            gateway: AsyncServer,
            group_cluster_index: str,
            room_cluster_index: str,
            concurrency: int = 10,
            batch_size: int = 100,
        ):
        self.gateway = gateway
        self.concurrency = concurrency
        self.batch_size = batch_size
        self.group_cluster_index = group_cluster_index
        self.room_cluster_index = room_cluster_index
        self.queue = asyncio.Queue()

    async def start(self) -> None:
        for _ in range(self.concurrency):
            asyncio.create_task(self.__server())

    async def __server(self) -> NoReturn:
        while True:
            sid, clusters = await self.queue.get()
            try: await self.__join_batched(sid, clusters)
            except Exception as e: print(f"Error on joining rooms for {sid}: {e}") #change to logger
            self.queue.task_done()

    async def __join_batched(self, sid, clusters: InstrumentedList) -> None:
        for _ in range(0, len(clusters), self.batch_size):
            chunk = clusters[_:_+self.batch_size]
            await asyncio.gather(*[
                self.gateway.enter_room(sid, f"{self.group_cluster_index}{cluster.id}") for cluster in chunk
            ])

    async def join_groups(self, sid, clusters: InstrumentedList) -> bool:
        try:
            await self.queue.put((sid, clusters))
            return False #as status = ...
        except: return True

    async def join_group(self, sid, group_id) -> bool:
        try:
            self.gateway.enter_room(sid, f"{self.group_cluster_index}{group_id}")
            return True
        except: return False

    async def join_room(self, sid, room_id) -> bool:
        try:
            self.gateway.enter_room(sid, f"{self.room_cluster_index}{room_id}")
            return True
        except: return False

    async def leave_group(self, sid, group_id) -> bool:
        try:
            self.gateway.leave_room(sid, f"{self.group_cluster_index}{group_id}")
            return True
        except: return False

    async def leave_room(self, sid, room_id) -> bool:
        try:
            self.gateway.leave_room(sid, f"{self.room_cluster_index}{room_id}")
            return True
        except: return False