from socketio.async_server import AsyncServer
from typing import NoReturn
import asyncio
import uuid
#Client Event Clusters Connection Handling Manager

class CECCHManager:
    def __init__(self, gateway: AsyncServer, concurrency: int = 10, batch_size: int = 100):
        self.gateway = gateway
        self.concurrency = concurrency
        self.batch_size = batch_size
        self.queue = asyncio.Queue()

    async def start(self) -> None:
        for _ in range(self.concurrency):
            asyncio.create_task(self.__server())

    async def __server(self) -> NoReturn:
        while True:
            sid, clusters = await self.queue.get()
            try: await self.__join_batched(sid, clusters)
            except Exception as e: print(f"Error on joining rooms for {sid}: {e}")
            self.queue.task_done()

    async def __join_batched(self, sid, clusters: list) -> None:
        for _ in range(0, len(clusters), self.batch_size):
            chunk = clusters[_:_+self.batch_size]
            await asyncio.gather(*[
                self.gateway.enter_room(sid, cluster) for cluster in chunk
            ])

    async def load(self, sid, clusters: list) -> None:
        await self.queue.put((sid, clusters))