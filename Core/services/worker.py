from sqlalchemy import ForeignKey, String, Boolean, DateTime, Date, Table, Column, Integer, func, desc, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, selectinload
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime, timedelta, date
from typing import Optional
from random import uniform
from typing import List
import time

class Base(DeclarativeBase):
    pass

client_group_relationship = Table(
    'cgrel', Base.metadata,
    Column('client_id', String, ForeignKey('client.id'), primary_key=True),
    Column('group_id', String, ForeignKey('group.id'), primary_key=True)
)

friend_relationship = Table(
    'frrel', Base.metadata,
    Column('client_id', String, ForeignKey('client.id'), primary_key=True),
    Column('friend_id', String, ForeignKey('client.id'), primary_key=True)
)

client_role_relationship = Table(
    'crrel', Base.metadata,
    Column('client_id', String, ForeignKey('client.id'), primary_key=True),
    Column('role_id', String, ForeignKey('role.id'), primary_key=True)
)

class Client(Base):
    __tablename__ = "client"

    username: Mapped[str] = mapped_column(String(10))
    nickname: Mapped[str] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(30))
    password_hashed: Mapped[str]
    date_of_birth: Mapped[date]
    about_me: Mapped[str] = mapped_column(String(200), nullable=True)
    avatar_url: Mapped[str] = mapped_column(String(100), nullable=True)
    color_theme: Mapped[str] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    id : Mapped[str] = mapped_column(String(36), primary_key=True)

    token: Mapped[str]
    token_expires_at: Mapped[datetime] = mapped_column(DateTime) #datetime.now(datetime.timezone.utc) + timedelta(hours=...)
    last_login: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(datetime.timezone.utc))

    friends = relationship("Client", secondary=friend_relationship, back_populates="friends")
    groups = relationship("Group", secondary=client_group_relationship, back_populates="members")
    roles = relationship("Role", secondary=client_group_relationship, back_populates="assignees")
    owned_groups: Mapped[List["Group"]] = relationship("Group", back_populates="owner", foreign_keys="Group.owner_id")
    created_spaces: Mapped[List["Space"]] = relationship("Space", back_populates="creator", foreign_keys="Space.cretor_id")
    created_rooms: Mapped[List["Room"]] = relationship("Room", back_populates="creator", foreign_keys="Room.creator_id")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="author", foreign_keys="Message.author_id")

class Group(Base):
    __tablename__ = "group"

    owner_id: Mapped[str] = mapped_column(ForeignKey('client.id'))

    name: Mapped[str] = mapped_column(String(20))
    about_group: Mapped[str] = mapped_column(String(300), nullable=True)
    icon_url: Mapped[str] = mapped_column(String(100), nullable=True)
    nsfw: Mapped[bool] = mapped_column(Boolean(create_constraint=False), default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    id : Mapped[str] = mapped_column(String(36), primary_key=True)

    #settings
    content_filter: Mapped[bool] = mapped_column(Boolean(create_constraint=False), default=False)
    content_filter_level: Mapped[str] = mapped_column(String(10), default="low")

    members = relationship("Client", secondary=client_group_relationship, back_populates="groups")
    owner: Mapped["Client"] = relationship("Client", back_populates="owned_groups", foreign_keys=[owner_id])
    roles: Mapped[List["Role"]] = relationship("Role", back_populates="group", foreign_keys="Role.group_id")
    permissions: Mapped[List["Permission"]] = relationship("Permission", back_populates="group", foreign_keys="Permission.group_id")
    spaces: Mapped[List["Space"]] = relationship("Space", back_populates="group", foreign_keys="Space.group_id")
    rooms: Mapped[List["Room"]] = relationship("Room", back_populates="group", foreign_keys="Room.group_id")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="group", foreign_keys="Message.group_id")

class Space(Base):
    __tablename__ = "space"

    group_id: Mapped[str] = mapped_column(ForeignKey('group.id'))
    creator_id: Mapped[str] = mapped_column(ForeignKey('client.id'))

    name: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    id : Mapped[str] = mapped_column(String(36), primary_key=True)
    
    creator: Mapped["Client"] = relationship("Client", back_populates="created_spaces", foreign_keys=[creator_id])
    rooms: Mapped[List["Room"]] = relationship("Room", back_populates="space", foreign_keys="Room.space_id")

class Room(Base):
    __tablename__ = "room"

    group_id: Mapped[str] = mapped_column(ForeignKey('group.id'))
    space_id: Mapped[str] = mapped_column(ForeignKey('space.id'), nullable=True)
    creator_id: Mapped[str] = mapped_column(ForeignKey('client.id'))

    name: Mapped[str] = mapped_column(String(20))
    about_room: Mapped[str] = mapped_column(String(150), nullable=True)
    nsfw: Mapped[bool] = mapped_column(Boolean(create_constraint=False), default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    group: Mapped["Group"] = relationship("Group", back_populates="rooms", foreign_keys=[group_id])
    space: Mapped["Space"] = relationship("Space", back_populates="rooms", foreign_keys=[space_id])
    creator: Mapped["Client"] = relationship("Client", back_populates="created_rooms", foreign_keys=[creator_id])
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="room", foreign_keys="Message.room_id")

class Message(Base):
    __tablename__ = "message"

    group_id: Mapped[str] = mapped_column(ForeignKey('group.id'))
    room_id: Mapped[str] = mapped_column(ForeignKey('room.id'))
    author_id: Mapped[str] = mapped_column(ForeignKey('client.id'))

    sent_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    content: Mapped[str] = mapped_column(String(1200))
    edited: Mapped[bool] = mapped_column(Boolean(create_constraint=False), default=False)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    group: Mapped["Group"] = relationship("Group", back_populates="messages", foreign_keys=[group_id])
    room: Mapped["Room"] = relationship("Room", back_populates="messages", foreign_keys=[room_id])
    author: Mapped["Client"] = relationship("Client", back_populates="messages", foreign_keys=[author_id])

class Role(Base):
    __tablename__ = "role"

    group_id: Mapped[str] = mapped_column(ForeignKey('group.id'))

    name: Mapped[str] = mapped_column(String(20))
    color: Mapped[str] = mapped_column(String(7), default="#FFFFFF") #HEX only! heh.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    group: Mapped["Group"] = relationship("Group", back_populates="roles", foreign_keys=[group_id])
    permissions: Mapped[List["Permission"]] = relationship("Permission", back_populates="role", foreign_keys="Permission.role_id")
    assignees = relationship("Client", secondary=client_group_relationship, back_populates="roles")

class Permission(Base):
    __tablename__ = "permission"

    group_id: Mapped[str] = mapped_column(ForeignKey('group.id'))
    role_id: Mapped[str] = mapped_column(ForeignKey('role.id'))
    room_id: Mapped[str] = mapped_column(ForeignKey('room.id'), nullable=True)

    body: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    group: Mapped["Group"] = relationship("Group", back_populates="permissions", foreign_keys=[group_id])
    role: Mapped["Group"] = relationship("Role", back_populates="permissions", foreign_keys=[role_id])
    room: Mapped["Group"] = relationship("Room", back_populates="assigned_permissions", foreign_keys=[room_id])

"""
PERMISSIONS

= GLOBAL:
    - CREATE_SPACES
    - CREATE_ROOMS
    - SEND_MESSAGES
    - MANAGE_ROOMS
    - MANAGE_SPACES
    - VIEW_SPACES (overrides view_rooms, meaning that if set to FALSE, neither spaces nor rooms will be displayed)
    - VIEW_ROOMS
    - MANAGE_GROUP *
    - CO_OWNER * (FULL ACCESS)
    - CREATE_ROLES
    - SEND_MEDIA (.img .jpg. .gif .mp4 etc media attachements won't be allowed is set to FALSE)
    - ATTACH_FILES (overrides send_media as no attachements will be allowed if set to FALSE)
    - BAN (this be obvious :> )
    - KICK (this as well :> )

= ROOMS (per role permissions):
    - SEND_MESSAGES
    - SEND_MEDIA (same as in GLOBAL)
    - ATTACH_FILES (same as in GLOBAL)

= PERMISSIONS
This is pretty simple:
    {
        "permission": "MANAGE_GROUP",
        "global": True,
    }

    or

    {
        "permission": "SEND_MESSAGES",
        "global": False,
    }

    Keep in mind that some permissions can be in both categories.

"""

class Worker:
    def __init__(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", echo=True)
        self.session = sessionmaker(bind=self.engine, class_=AsyncSession, expire_on_commit=False)

    async def start(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

async def event_executer(func):
    async def wrapper(request, client, operation_name, session):
        try:
            async with session() as ssn:
                async with ssn.begin():
                    result = await func(request, client, ssn)
            return result
        except: return {"operation": operation_name, "status": False, "error": "Oops... It seems that our server is in trouble, dev team got notified!"}
    return wrapper

    
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

    """