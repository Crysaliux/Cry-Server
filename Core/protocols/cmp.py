import asyncio

class CMP:
    def __init__(self):
        self.active_connections = {}
        self.active_endpoints = {}
        self.proc_lock = asyncio.Lock()

    async def connect(self, client_id: int, value: dict):
        async with self.proc_lock:
            self.active_connections[client_id] = value

    async def disconnect(self, client_id: int):
        async with self.proc_lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]

    async def update(self, client_id: int, value: str):
        async with self.proc_lock:
            if client_id in self.active_connections:
                self.active_connections[client_id] = value
    
    async def add_channel(self, channel_id: int):
        async with self.proc_lock:
            self.active_endpoints[channel_id] = []

    async def add_channel_receiver(self, channel_id: int, client_id: int):
        async with self.proc_lock:
            if client_id in self.active_connections and channel_id in self.active_endpoints:
                self.active_endpoints[channel_id].append(client_id)

    async def message_broadcast(self, id: int, icon_path: str, content: str, author_name: str, author_id: int, channel_id: int, group_id: int): 
        async with self.proc_lock:
            if channel_id in self.active_endpoints:
                for client_id in self.active_endpoints[channel_id]:
                    try:
                        await self.active_connections[client_id]["socket"].send_text({
                            "request": "DisplayMessage", 
                            "id": id,
                            "icon_path": icon_path,
                            "content": content,
                            "author_name": author_name,
                            "author_id": author_id,
                            "channel_id": channel_id,
                            "group_id": group_id,
                        })
                    except:
                        pass

    async def message_broadcast_removal(self, id: int, channel_id: int):
        async with self.proc_lock:
            if channel_id in self.active_endpoints:
                for client_id in self.active_endpoints[channel_id]:
                    try:
                        await self.active_connections[client_id]["socket"].send_text({
                            "request": "RemoveMessage", 
                            "channel_id": channel_id,
                            "id": id,
                        })
                    except:
                        pass

    async def message_broadcast_edit(self, id: int, channel_id: int, new_content: str):
        async with self.proc_lock:
            if channel_id in self.active_endpoints:
                for client_id in self.active_endpoints[channel_id]:
                    try:
                        await self.active_connections[client_id]["socket"].send_text({
                            "request": "EditMessage", 
                            "channel_id": channel_id,
                            "new_content": new_content,
                            "id": id,
                        })
                    except:
                        pass

    async def channel_broadcast_creation(self, id: int, name: str, group):
        async with self.proc_lock:
            for member in group.members:
                try:
                    await self.active_connections[member.id]["socket"].send_text({
                        "request": "DisplayChannel", 
                        "group_id": group.id,
                        "name": name,
                        "id": id,
                    })
                except:
                    pass

    async def private_channel_broadcast_creation(self, id: int, name: str, client_id: int, co_client_id: int):
        async with self.proc_lock:
            try:
                await self.active_connections[co_client_id]["socket"].send_text({
                    "request": "DisplayPrivateChannel",
                    "co_client_id": client_id,
                    "name": name,
                    "id": id,
                })
            except:
                pass

    async def channel_broadcast_removal(self, id: int, group):
        async with self.proc_lock:
            for member in group.members:
                try:
                    await self.active_connections[member.id]["socket"].send_text({
                        "request": "RemoveChannel", 
                        "group_id": group.id,
                        "id": id,
                    })
                except:
                    pass

    async def private_channel_broadcast_removal(self, id: int, client_id: int, co_client_id: int):
        async with self.proc_lock:
            try:
                await self.active_connections[co_client_id]["socket"].send_text({
                    "request": "RemovePrivateChannel",
                    "co_client_id": client_id,
                    "id": id,
                })
            except:
                pass

    async def channel_broadcast_edit(self, id: int, new_name: str, group):
        async with self.proc_lock:
            for member in group.members:
                try:
                    await self.active_connections[member.id]["socket"].send_text({
                        "request": "RemoveChannel", 
                        "group_id": group.id,
                        "new_name": new_name,
                        "id": id,
                    })
                except:
                    pass

    async def group_broadcast_removal(self, id: int, group):
        async with self.proc_lock:
            for member in group.members:
                try:
                    await self.active_connections[member.id]["socket"].send_text({
                        "request": "RemoveGroup",
                        "id": id,
                    })
                except:
                    pass