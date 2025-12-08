import asyncio
import numpy as np
from asyncio import Semaphore

async def __flop(clients: list[str]):
    for _ in clients:
        pass
        #print("Client flopped")

async def __batch_worker(semaphore: Semaphore, clients: list[str]):
    async with semaphore:
        await __flop(clients)

async def __batch_update(clients: list[str]):
    clients = np.array(clients)
    semaphore  = Semaphore(20)
    tasks = [__batch_worker(semaphore, batch) for batch in np.array_split(clients, len(clients) // 100)]
    print(tasks)
    await asyncio.gather(*tasks)


clients = ["yyey737ry737whreueuhfhheifiq3uriq3"] * 9000
asyncio.run(__batch_update(clients))