from sqlalchemy import ForeignKey, String, Boolean, DateTime, Date, Table, Column, Integer, func, desc, JSON, BIGINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, selectinload
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.exc import DatabaseError, OperationalError, IntegrityError, ProgrammingError
from datetime import datetime, timezone, date
from typing import Optional
from random import uniform
from typing import List
from functools import wraps
from typing import Any
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    id : Mapped[str] = mapped_column(String(36), primary_key=True)

    refresh_token: Mapped[str]
    last_login: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    friends = relationship("Client", 
        secondary=friend_relationship, 
        primaryjoin=id==friend_relationship.c.client_id,
        secondaryjoin=id==friend_relationship.c.friend_id,
        backref="friended_by",
    )
    groups = relationship("Group", secondary=client_group_relationship, back_populates="members")
    roles = relationship("Role", secondary=client_role_relationship, back_populates="assignees")
    owned_groups: Mapped[List["Group"]] = relationship("Group", back_populates="owner", foreign_keys="Group.owner_id")
    created_spaces: Mapped[List["Space"]] = relationship("Space", back_populates="creator", foreign_keys="Space.creator_id")
    created_rooms: Mapped[List["Room"]] = relationship("Room", back_populates="creator", foreign_keys="Room.creator_id")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="author", foreign_keys="Message.author_id")

class Group(Base):
    __tablename__ = "group"

    owner_id: Mapped[str] = mapped_column(ForeignKey('client.id'))

    name: Mapped[str] = mapped_column(String(20))
    global_name: Mapped[str] = mapped_column(String(20))
    about_group: Mapped[str] = mapped_column(String(300), nullable=True)
    icon_url: Mapped[str] = mapped_column(String(100), nullable=True)
    nsfw: Mapped[bool] = mapped_column(Boolean(create_constraint=False), default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    id : Mapped[str] = mapped_column(String(36), primary_key=True)

    #settings
    content_filter: Mapped[bool] = mapped_column(Boolean(create_constraint=False), default=False)
    content_filter_level: Mapped[str] = mapped_column(String(10), default="low")

    members = relationship("Client", secondary=client_group_relationship, back_populates="groups")
    owner: Mapped["Client"] = relationship("Client", back_populates="owned_groups", foreign_keys=[owner_id])
    roles: Mapped[List["Role"]] = relationship("Role", back_populates="group", foreign_keys="Role.group_id", cascade="all, delete-orphan")
    spaces: Mapped[List["Space"]] = relationship("Space", back_populates="group", foreign_keys="Space.group_id", cascade="all, delete-orphan")
    rooms: Mapped[List["Room"]] = relationship("Room", back_populates="group", foreign_keys="Room.group_id", cascade="all, delete-orphan")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="group", foreign_keys="Message.group_id", cascade="all, delete-orphan")

class Space(Base):
    __tablename__ = "space"

    group_id: Mapped[str] = mapped_column(ForeignKey('group.id'))
    creator_id: Mapped[str] = mapped_column(ForeignKey('client.id', ondelete="SET NULL"), nullable=True)

    name: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    id : Mapped[str] = mapped_column(String(36), primary_key=True)
    
    group: Mapped["Group"] = relationship("Group", back_populates="spaces", foreign_keys=[group_id])
    creator: Mapped["Client"] = relationship("Client", back_populates="created_spaces", foreign_keys=[creator_id])
    rooms: Mapped[List["Room"]] = relationship("Room", back_populates="space", foreign_keys="Room.space_id")

class Room(Base):
    __tablename__ = "room"

    group_id: Mapped[str] = mapped_column(ForeignKey('group.id'))
    space_id: Mapped[str] = mapped_column(ForeignKey('space.id', ondelete="SET NULL"), nullable=True)
    creator_id: Mapped[str] = mapped_column(ForeignKey('client.id', ondelete="SET NULL"), nullable=True)

    name: Mapped[str] = mapped_column(String(20))
    about_room: Mapped[str] = mapped_column(String(150), nullable=True)
    nsfw: Mapped[bool] = mapped_column(Boolean(create_constraint=False), default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    group: Mapped["Group"] = relationship("Group", back_populates="rooms", foreign_keys=[group_id])
    space: Mapped["Space"] = relationship("Space", back_populates="rooms", foreign_keys=[space_id])
    creator: Mapped["Client"] = relationship("Client", back_populates="created_rooms", foreign_keys=[creator_id])
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="room", foreign_keys="Message.room_id", cascade="all, delete-orphan")
    role_to_room_permissions: Mapped[List["RoleToRoomPermission"]] = relationship("RoleToRoomPermission", back_populates="room", foreign_keys="RoleToRoomPermission.room_id", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "message"

    group_id: Mapped[str] = mapped_column(ForeignKey('group.id'))
    room_id: Mapped[str] = mapped_column(ForeignKey('room.id'))
    author_id: Mapped[str] = mapped_column(ForeignKey('client.id', ondelete="SET NULL"), nullable=True)

    sent_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    group: Mapped["Group"] = relationship("Group", back_populates="roles", foreign_keys=[group_id])
    global_permissions: Mapped[List["GlobalPermission"]] = relationship("GlobalPermission", back_populates="role", foreign_keys="GlobalPermissions.role_id", cascade="all, delete-orphan")
    role_to_room_permissions: Mapped[List["RoleToRoomPermission"]] = relationship("RoleToRoomPermission", back_populates="role", foreign_keys="RoleToRoomPermission.role_id", cascade="all, delete-orphan")
    assignees = relationship("Client", secondary=client_role_relationship, back_populates="roles")

class GlobalPermission(Base):
    __tablename__ = "global_permission"

    role_id: Mapped[str] = mapped_column(ForeignKey('role.id'))

    name: Mapped[str] = mapped_column(String(20))
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    role: Mapped["Role"] = relationship("Role", back_populates="global_permissions", foreign_keys=[role_id])

class RoleToRoomPermission(Base):
    __tablename__ = "role_to_room_permission"

    room_id: Mapped[str] = mapped_column(ForeignKey('room.id'))
    role_id: Mapped[str] = mapped_column(ForeignKey('role.id'))

    name: Mapped[str] = mapped_column(String(20))
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    role: Mapped["Role"] = relationship("Role", back_populates="role_to_room_permissions", foreign_keys=[role_id])
    room: Mapped["Role"] = relationship("Room", back_populates="role_to_room_permissions", foreign_keys=[room_id])

#Add room_id for rooms to be fetched

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
    -VIEW_ROOM
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

    Keep in mind that some permissions can be of both categories.

"""

class Worker:
    def __init__(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", echo=False) #make True for precise logging
        self.session = sessionmaker(bind=self.engine, class_=AsyncSession, expire_on_commit=False)

    async def start(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

#Session wrapper
def throw_db_error(code: str):
    return {
        "status": False,
        "body": None,
        "error": code,
    }


def worker_session(func, session):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            async with session() as ss:
                async with ss.begin():
                    return await func(self, *args, session=ss, **kwargs)
        except OperationalError as e:
            await ss.rollback()
            if not "timeout" in str(e).lower():
                return throw_db_error("101")
            return throw_db_error("100")
        
        except IntegrityError as e:
            await ss.rollback()
            return throw_db_error("102")
        
        except ProgrammingError as e:
            await ss.rollback()
            return throw_db_error("103")
        
        except DatabaseError:
            await ss.rollback()
            return throw_db_error("104")
    return wrapper