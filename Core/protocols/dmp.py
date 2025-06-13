from sqlalchemy import ForeignKey, String, Boolean, DateTime, insert, select, update, delete, Table, Column, Integer, func, desc
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, selectinload
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime
from typing import Optional
from random import uniform
from typing import List
import time

class Base(DeclarativeBase):
    pass

client_group_relationship = Table(
    'cgrel', Base.metadata,
    Column('client_id', Integer, ForeignKey('client.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('group.id'), primary_key=True)
)

client_role_relationship = Table(
    'crrel', Base.metadata,
    Column('client_id', Integer, ForeignKey('client.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('role.id'), primary_key=True)
)

class Client(Base):
    __tablename__ = "client"

    username: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(30))
    password: Mapped[str] = mapped_column()
    bio: Mapped[str] = mapped_column(String(200), nullable=True)
    icon_path: Mapped[str] = mapped_column(String(100), nullable=True)
    id : Mapped[int] = mapped_column(primary_key=True)

    groups = relationship("Group", secondary=client_group_relationship, back_populates="members")
    roles = relationship("Role", secondary=client_role_relationship, back_populates="clients")
    owned_groups: Mapped[List["Group"]] = relationship("Group", back_populates="owner", foreign_keys="Group.owner_id")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="client", foreign_keys="Message.client_id")
    privates: Mapped[List["Channel"]] = relationship("Channel", back_populates="client", foreign_keys="Channel.client_id")
    blocked: Mapped[List["Block"]] = relationship("Block", back_populates="client", foreign_keys="Block.client_id")
    co_privates: Mapped[List["Channel"]] = relationship("Channel", back_populates="co_client", foreign_keys="Channel.co_client_id")
    pending_friend_requests: Mapped[List["FriendRequest"]] = relationship("FriendRequest", back_populates="co_client", foreign_keys="FriendRequest.co_client_id")
    sent_friend_requests: Mapped[List["FriendRequest"]] = relationship("FriendRequest", back_populates="client", foreign_keys="FriendRequest.client_id")

    def __repr__(self) -> str:
        return f"Client(username={self.username!r}, email={self.email!r}, password={self.password!r}, bio={self.bio!r}, icon_path={self.icon_path!r}, id={self.id!r})"
    
class FriendRequest(Base):
    __tablename__ = "friend_request"

    client_id: Mapped[int] = mapped_column(ForeignKey('client.id'))
    co_client_id: Mapped[int] = mapped_column(ForeignKey('client.id'))

    id: Mapped[int] = mapped_column(primary_key=True)

    client: Mapped["Client"] = relationship("Client", back_populates="pending_friend_requests", foreign_keys=[client_id])
    co_client: Mapped["Client"] = relationship("Client", back_populates="sent_friend_requests", foreign_keys=[co_client_id])

    def __repr__(self) -> str:
        return f"Block(blocked_client_id={self.blocked_client_id!r}, id={self.id!r})"
    
class Block(Base):
    __tablename__ = "block"

    client_id: Mapped[int] = mapped_column(ForeignKey('client.id'))

    blocked_client_id: Mapped[int]
    id: Mapped[int] = mapped_column(primary_key=True)

    client: Mapped["Client"] = relationship("Client", back_populates="blocked", foreign_keys=[client_id])

    def __repr__(self) -> str:
        return f"Block(blocked_client_id={self.blocked_client_id!r}, id={self.id!r})"

class Role(Base):
    __tablename__ = "role"

    group_id: Mapped[int] = mapped_column(ForeignKey('group.id'))

    name: Mapped[str] = mapped_column(String(10))
    rank_index: Mapped[int]
    id: Mapped[int] = mapped_column(primary_key=True)
    
    MESSAGE_SEND: Mapped[bool] = mapped_column(Boolean(create_constraint=False), default=False)
    MESSAGE_DELETE: Mapped[bool] = mapped_column(Boolean(create_constraint=False), default=False)
    MESSAGE_EDIT: Mapped[bool] = mapped_column(Boolean(create_constraint=False), default=False)
    CHANNEL_CREATE: Mapped[bool] = mapped_column(Boolean(create_constraint=False), default=False)
    CHANNEL_DELETE: Mapped[bool] = mapped_column(Boolean(create_constraint=False), default=False)
    CHANNEL_EDIT: Mapped[bool] = mapped_column(Boolean(create_constraint=False), default=False)
    GROUP_CREATE: Mapped[bool] = mapped_column(Boolean(create_constraint=False), default=False)
    GROUP_DELETE: Mapped[bool] = mapped_column(Boolean(create_constraint=False), default=False)
    GROUP_EDIT: Mapped[bool] = mapped_column(Boolean(create_constraint=False), default=False)
    
    group: Mapped["Group"] = relationship("Group", back_populates="roles", foreign_keys=[group_id])
    clients = relationship("Client", secondary=client_role_relationship, back_populates="roles")

    def __repr__(self) -> str:
        return f"Role(name={self.name!r}, id={self.id!r})"

class Group(Base):
    __tablename__ = "group"
    
    owner_id: Mapped[int] = mapped_column(ForeignKey('client.id'))

    name: Mapped[str] = mapped_column(String(10))
    desc: Mapped[str] = mapped_column(String(100), nullable=True)
    icon_path: Mapped[str] = mapped_column(String(100), nullable=True)
    id : Mapped[int] = mapped_column(primary_key=True)

    members = relationship("Client", secondary=client_group_relationship, back_populates="groups")
    owner: Mapped["Client"] = relationship("Client", back_populates="owned_groups", foreign_keys=[owner_id])
    channels: Mapped[List["Channel"]] = relationship("Channel", back_populates="group", foreign_keys="Channel.group_id")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="group", foreign_keys="Message.group_id")
    roles: Mapped[List["Role"]] = relationship("Role", back_populates="group", foreign_keys="Role.group_id")

    def __repr__(self) -> str:
        return f"Group(name={self.name!r}, desc={self.desc!r}, icon_path={self.icon_path!r}, id={self.id!r})"
    
class Channel(Base):
    __tablename__ = "channel"

    group_id: Mapped[int] = mapped_column(ForeignKey('group.id'), nullable=True)

    client_id: Mapped[int] = mapped_column(ForeignKey('client.id'), nullable=True)
    co_client_id: Mapped[int] = mapped_column(ForeignKey('client.id'), nullable=True)

    name: Mapped[str] = mapped_column(String(10))
    personal: Mapped[bool] = mapped_column(Boolean(create_constraint=False), default=False)
    id : Mapped[int] = mapped_column(primary_key=True)

    group: Mapped["Group"] = relationship("Group", back_populates="channels", foreign_keys=[group_id])

    client: Mapped["Client"] = relationship("Client", back_populates="privates", foreign_keys=[client_id])
    co_client: Mapped["Client"] = relationship("Client", back_populates="co_privates", foreign_keys=[co_client_id])

    messages: Mapped[List["Message"]] = relationship("Message", back_populates="channel", foreign_keys="Message.channel_id")
    attachements: Mapped[List["Attachement"]] = relationship("Attachement", back_populates="channel", foreign_keys="Attachement.channel_id")

    def __repr__(self) -> str:
        return f"Channel(name={self.name!r}, personal={self.personal!r}, id={self.id!r})"
    
class Message(Base):
    __tablename__ = "message"

    client_id: Mapped[int] = mapped_column(ForeignKey('client.id'))
    group_id: Mapped[int] = mapped_column(ForeignKey('group.id'), nullable=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey('channel.id'))

    content: Mapped[str] = mapped_column(String(1024))
    sent_at: Mapped[datetime] = mapped_column(default=func.now())
    id: Mapped[int] = mapped_column(primary_key=True)

    channel: Mapped["Channel"] = relationship("Channel", back_populates="messages", foreign_keys=[channel_id])
    client: Mapped["Client"] = relationship("Client", back_populates="messages", foreign_keys=[client_id])
    group: Mapped["Group"] = relationship("Group", back_populates="messages", foreign_keys=[group_id])

    def __repr__(self) -> str:
        return f"Message(content={self.content!r}, id={self.id!r})"
    
class Attachement(Base):
    __tablename__ = "attachement"

    channel_id: Mapped[int] = mapped_column(ForeignKey('channel.id'))

    path: Mapped[str] = mapped_column(String(50))
    inner_path: Mapped[str] = mapped_column(String(50))
    id: Mapped[int] = mapped_column(primary_key=True)

    channel: Mapped["Channel"] = relationship("Channel", back_populates="attachements", foreign_keys=[channel_id])

    def __repr__(self) -> str:
        return f"Attachement(path={self.path!r}, inner_path={self.inner_path!r}, id={self.id!r})"

class Dynamic(Base):
    __tablename__ = "dynamic"
    
    path: Mapped[str] = mapped_column(String(50))
    index: Mapped[str] = mapped_column(String(50))
    inner_path: Mapped[str] = mapped_column(String(50))
    id: Mapped[int] = mapped_column(primary_key=True)

    def __repr__(self) -> str:
        return f"Dynamic(path={self.path!r}, index={self.index!r}, inner_path={self.inner_path!r}, id={self.id!r})"

    
class DMP:
    def __init__(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", echo=True)
        self.session = sessionmaker(bind=self.engine, class_=AsyncSession, expire_on_commit=False)

    async def start(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    def id(self):
        time.sleep(uniform(0.300, 0.450))
        tiden = list(datetime.now().strftime("%m/%d/%Y/%H/%M/%S/%f").split("/"))
        id = 0
        for iden in tiden:
            id += int(iden) * int(tiden[-1])
        return id
    
    """
    create_client
    delete_client
    """
    
    async def create_client(self, name: str, username: str, email: str, password: str, id: int):
        try:
            created = False
            check_query = select(Client).where(Client.email == email)
            async with self.session() as session:
                async with session.begin():
                    check = await session.execute(check_query)
                    check = check.scalars().first()
                    if check is None:
                        create_query = Client(name=name, username=username, email=email, password=password, id=id)
                        session.add(create_query)
                        await session.commit()
                        created = True
            return created, id
        except: return False
    
    async def delete_client(self, id: int):
        try:
            deleted = False
            client_delete = delete(Client).where(Client.id == id).returning(Client.id)
            async with self.session() as session:
                async with session.begin():
                    check_id = await session.execute(client_delete)
                    if check_id == id:
                        deleted = True
            return deleted
        except: return False
    
    async def block_client(self, id: int, blocked_client_id: int):
        try:
            blocked = True
            check_query = select(Client).where(Client.id == blocked_client_id)
            async with self.session() as session: 
                async with session.begin():
                    check = await session.execute(check_query)
                    check = check.scalars().first()
                    if check is not None:
                        create_query = Block(client_id=id, blocked_client_id=blocked_client_id, id=self.id())
                        session.add(create_query)
                        await session.commit()
                        blocked = True
            return blocked
        except: return False

    """
    create_friend_request
    delete_friend_request
    """

    async def create_friend_request(self, id: int, client_id: int, co_client_id: int):
        try:
            async with self.session() as session:
                async with session.begin():
                    create_query = FriendRequest(client_id=client_id, co_client_id=co_client_id, id=id)
                    session.add(create_query)
                    await session.commit()
            return True
        except: return False

    async def delete_friend_request(self, id: int):
        try:
            deleted = False
            friend_request_delete = delete(FriendRequest).where(FriendRequest.id == id).returning(FriendRequest.id)
            async with self.session() as session:
                async with session.begin():
                    check_id = await session.execute(friend_request_delete)
                    if check_id == id:
                        deleted = True
            return deleted
        except: return False

    """
    create_group
    join_group
    delete_group
    """
    
    async def create_group(self, name: str, client_id: int, id: int, icon_path: str = None, desc: str = None):
        try:
            group_create_query = Group(owner_id=client_id, name=name, icon_path=icon_path, desc=desc, id=id)
            preset_id, preset_name = self.id(), f"{name}'s"
            channel_create_query = Channel(group_id=id, name=preset_name, id=preset_id)
            async with self.session() as session:
                async with session.begin():
                    session.add(group_create_query)
                    session.add(channel_create_query)
                    await session.commit()
            return True, preset_id, preset_name
        except: return False, None, None
    
    async def join_group(self, client_id: int, group_id: int):
        try:
            joined = False
            fetch_client = select(Client).where(Client.id == client_id)
            fetch_group = select(Group).options(selectinload(Group.members)).where(Group.id == group_id)
            async with self.session() as session:
                async with session.begin():
                    client = await session.execute(fetch_client)
                    client = client.scalars().first()
                    group = await session.execute(fetch_group)
                    group = group.scalars().first()
                    if client is not None and group is not None and client not in group.members:
                        group.members.append(client)
                        await session.commit()
                        joined = True
            return joined
        except: return False
    
    async def delete_group(self, id: int):
        try:
            deleted = False
            group_delete = delete(Group).where(Group.id == id).returning(Group.id)
            async with self.session() as session:
                async with session.begin():
                    check_id = await session.execute(group_delete)
                    if check_id == id:
                        deleted = True
            return deleted
        except: return False
    
    """
    create_channel
    delete_channel
    """
    
    async def create_channel(self, client_id: int, name: str, id: int, group_id: int = None, private: bool = False, co_client_id: int = None):
        try:
            created = False
            async with self.session() as session:
                async with session.begin():
                    if not private: create_query = Channel(group_id=group_id, name=name, id=id)
                    else: create_query = Channel(client_id=client_id, co_client_id=co_client_id, name=name, id=id)
                    session.add(create_query)
                    await session.commit()
                    created = True
            return created
        except: return False
    
    async def delete_channel(self, id: int):
        try:
            deleted = False
            channel_delete = delete(Channel).where(Channel.id == id).returning(Channel.id)
            async with self.session() as session:
                async with session.begin():
                    check_id = await session.execute(channel_delete)
                    if check_id == id:
                        deleted = True
            return deleted
        except: return False
    
    """
    create_role
    delete_role
    """
    
    async def create_role(self, name: str, rank_index: int, group_id: int, id: int, **permissions):
        try:
            role_create_query = Role(name=name, rank_index=rank_index, group_id=group_id, id=id, **permissions)
            async with self.session() as session:
                async with session.begin():
                    session.add(role_create_query)
                    await session.commit()
            return True
        except: return False
    
    async def delete_role(self, id: int):
        try:
            deleted = False
            role_delete = delete(Role).where(Role.id == id).returning(Role.id)
            async with self.session() as session:
                async with session.begin():
                    check_id = await session.execute(role_delete)
                    if check_id == id:
                        deleted = True
            return deleted
        except: return False
    
    """
    save_message
    delete_message
    """
    
    async def save_message(self, client_id: int, group_id: int, channel_id: int, content: str, id: int):
        try:
            saved = False
            fetch_channel = select(Channel).where(Channel.id == channel_id)
            async with self.session() as session:
                async with session.begin():
                    channel = await session.execute(fetch_channel)
                    channel = channel.scalars().first()
                    if channel is not None:
                        create_query = Message(client_id=client_id, group_id=group_id, channel_id=channel_id, content=content, id=id)
                        session.add(create_query)
                        await session.commit()
                        saved=True
            return saved
        except: return False
    
    async def delete_message(self, id: int):
        try:
            deleted = False
            message_delete = delete(Message).where(Message.id == id).returning(Message.id)
            async with self.session() as session:
                async with session.begin():
                    check_id = await session.execute(message_delete)
                    if check_id == id:
                        deleted = True
            return deleted
        except: return False

    """
    save_attachement
    delete_attachement
    """

    async def save_attachement(self, channel_id: int, path: str, inner_path: str, id: int):
        try:
            saved = False
            fetch_channel = select(Channel).where(Channel.id == channel_id)
            async with self.session() as session:
                async with session.begin():
                    channel = await session.execute(fetch_channel)
                    channel = channel.scalars().first()
                    if channel is not None:
                        create_query = Attachement(channel_id=channel_id, path=path, inner_path=inner_path, id=id)
                        session.add(create_query)
                        await session.commit()
                        saved=True
            return saved
        except: return False
    
    async def delete_attachement(self, id: int):
        try:
            deleted = False
            attachement_delete = delete(Attachement).where(Attachement.id == id).returning(Attachement.id)
            async with self.session() as session:
                async with session.begin():
                    check_id = await session.execute(attachement_delete)
                    if check_id == id:
                        deleted = True
            return deleted
        except: return False

    """
    save_dynamic
    clear_dynamic
    """

    async def save_dynamic(self, path: str, index: str, inner_path: str, id: int):
        try:
            dynamic_fetch = select(Dynamic).where(Dynamic.index == index) 
            async with self.session() as session:
                async with session.begin():
                    dynamic = await session.execute(dynamic_fetch)
                    dynamic = dynamic.scalars().first()
                    if dynamic is None:
                        create_query = Dynamic(path=path, index=index, inner_path=inner_path, id=id)
                        session.add(create_query)
                        await session.commit()
            return True
        except: return False
    
    async def delete_dynamic(self, path: str):
        try:
            dynamic_delete = delete(Dynamic).where(Dynamic.path == path)
            async with self.session() as session:
                async with session.begin():
                    await session.execute(dynamic_delete)
            return True
        except: return False

    """
    fetch_client_by_mail
    fetch_client_by_id
    fetch_client_by_username
    fetch_group_by_id
    fetch_channel_by_id
    fetch_message_by_id
    fetch_dynamic_by_session_id
    """
    
    async def fetch_client_by_mail(self, email: str):
        try:
            fetch_query = select(Client).where(Client.email == email)
            async with self.session() as session:
                async with session.begin():
                    client = await session.execute(fetch_query)
                    client = client.scalars().first()
            return client
        except: return False
    
    async def fetch_client_by_id(self, id: int):
        try:
            fetch_query = select(Client).options(selectinload(Client.groups),
                                                 selectinload(Client.roles),
                                                 selectinload(Client.blocked),
                                                 selectinload(Client.privates),
                                                 selectinload(Client.co_privates)
                                            ).where(Client.id == id)
            async with self.session() as session:
                async with session.begin():
                    client = await session.execute(fetch_query)
                    client = client.scalars().first()
            return client
        except: return False

    async def fetch_client_by_username(self, username: str):
        try:
            fetch_query = select(Client).options(selectinload(Client.groups),
                                                 selectinload(Client.roles),
                                                 selectinload(Client.blocked),
                                                 selectinload(Client.privates),
                                                 selectinload(Client.co_privates)
                                            ).where(Client.username == username)
            async with self.session() as session:
                async with session.begin():
                    client = await session.execute(fetch_query)
                    client = client.scalars().first()
            return client
        except: return False
    
    async def fetch_group_by_id(self, id: int):
        try:
            fetch_query = select(Group).options(selectinload(Group.channels),
                                                 selectinload(Group.members),
                                                 selectinload(Group.messages)
                                            ).where(Group.id == id)
            async with self.session() as session:
                async with session.begin():
                    group = await session.execute(fetch_query)
                    group = group.scalars().first()
            return group
        except: return False
    
    async def fetch_channel_by_id(self, id: int):
        try:
            fetch_query = select(Channel).where(Channel.id == id)
            async with self.session() as session:
                async with session.begin():
                    channel = await session.execute(fetch_query)
                    channel = channel.scalars().first()
            return channel
        except: return False
    
    async def fetch_message_by_id(self, id: int):
        try:
            fetch_query = select(Message).where(Message.id == id)
            async with self.session() as session:
                async with session.begin():
                    message = await session.execute(fetch_query)
                    message = message.scalars().first()
            return message
        except: return False

    async def fetch_recent_messages(self, channel_id: int):
        try:
            fetch_query = select(Message).where(Message.channel_id == channel_id).order_by(desc(Message.sent_at), desc(Message.id)).limit(50)
            async with self.session() as session:
                async with session.begin():
                    messages = await session.execute(fetch_query)
                    messages = messages.scalars().all()
            messages.reverse()
            return messages
        except: return False
    
    async def fetch_message_history(self, channel_id: int, last_loaded_timestamp: str):
        try:
            timestamp = datetime.strptime(last_loaded_timestamp, "%Y-%m-%d %H:%M:%S")
            fetch_query = select(Message).where(Message.channel_id == channel_id, Message.sent_at < timestamp).order_by(desc(Message.sent_at), desc(Message.id)).limit(50)
            async with self.session() as session:
                async with session.begin():
                    messages = await session.execute(fetch_query)
                    messages = messages.scalars().all()
            messages.reverse()
            return messages
        except: return False

    async def fetch_dynamic_by_session_id(self, session_id: str, ignored_path: str):
        try:
            fetch_query = select(Dynamic).where(Dynamic.session_id == session_id, Dynamic.path != ignored_path)
            async with self.session() as session:
                async with session.begin():
                    dynamic_files = await session.execute(fetch_query)
                    dynamic_files = dynamic_files.scalars().first()
            return dynamic_files
        except: return False