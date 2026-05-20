from sqlmodel import Relationship, SQLModel, Field, Column
import uuid
from typing import Optional, List
import sqlalchemy.dialects.postgresql as pg
from datetime import datetime
from enum import Enum
from sqlalchemy import ForeignKey


class UserRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class AuditAction(str, Enum):
    BOARD_CREATED = "board_created"
    BOARD_UPDATED = "board_updated"
    BOARD_ARCHIVED = "board_archived"
    BOARD_DUPLICATED = "board_duplicated"
    BOARD_DELETED = "board_deleted"
    MEMBER_ADDED = "member_added" 
    MEMBER_REMOVED = "member_removed" 
    MEMBER_ROLE_CHANGED = "member_role_changed"
    MEMBER_LEFT = "member_left"
    REQUEST_SENT = "request_sent" 
    REQUEST_APPROVED = "request_approved"
    REQUEST_REJECTED = "request_rejected"
    INVITE_SENT = "invite_sent"
    INVITE_ACCEPTED = "invite_accepted"
    INVITE_REVOKED = "invite_revoked"


class NotificationType(str, Enum):
    REQUEST_RECEIVED = "request_received"
    REQUEST_APPROVED = "request_approved"
    REQUEST_REJECTED = "request_rejected"
    INVITE_RECEIVED = "invite_received"
    INVITE_ACCEPTED = "invite_accepted"
    MEMBER_REMOVED = "member_removed"
    ROLE_CHANGED = "role_changed"
    BOARD_ARCHIVED = "board_archived"
    MESSAGE_RECEIVED = "message_received"


class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class User(SQLModel, table=True):
    __tablename__ = "users"

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, nullable=False, primary_key=True),
    )
    username: str = Field(min_length=3, max_length=15, unique=True)
    password_hash: str = Field(exclude=True)
    email: str = Field(min_length=4)
    first_name: str = Field(min_length=2, max_length=15, unique=True)
    last_name: str = Field(min_length=2, max_length=15)
    is_verified: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(pg.TIMESTAMP)
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(pg.TIMESTAMP)
    )
    user_boards: List["BoardUser"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"lazy": "selectin",
                                                       "cascade": "all, delete-orphan",
                                                       "passive_deletes": True,}
    )


class Board(SQLModel, table=True):
    __tablename__ = "boards"

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, nullable=False, primary_key=True),
    )
    owner_uid: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID, ForeignKey("users.uid", ondelete="CASCADE"), nullable=True)
    )
    board_title: str = Field(min_length=3, max_length=20)
    board_description: Optional[str] = Field(min_length=10, max_length=255)
    archived: bool = Field(default=False)
    public: bool = Field(default=False)
    board_users: List["BoardUser"] = Relationship(
        back_populates="board", sa_relationship_kwargs={"lazy": "selectin",
                                                        "cascade": "all, delete-orphan",
                                                        "passive_deletes": True,}
    )


class BoardUser(SQLModel, table=True):
    __tablename__ = "boardusers"

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, nullable=False, primary_key=True),
    )
    user_uid: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID, ForeignKey("users.uid", ondelete="CASCADE"), nullable=True)
    )
    board_uid: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID, ForeignKey("boards.uid", ondelete="CASCADE"), nullable=True)
    )
    user: Optional["User"] = Relationship(back_populates="user_boards")
    board: Optional["Board"] = Relationship(back_populates="board_users")
    role: UserRole = Field(default=UserRole.MEMBER)


class Audit(SQLModel, table=True):
    __tablename__ = "audits"

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, nullable=False, primary_key=True),
    )
    user_uid: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID, ForeignKey("users.uid", ondelete="CASCADE"), nullable=True)
    )
    board_uid: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID, ForeignKey("boards.uid", ondelete="CASCADE"), nullable=True)
    )
    target_uid: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID, ForeignKey("users.uid", ondelete="SET NULL"), nullable=True)
    )
    action: AuditAction
    created_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(pg.TIMESTAMP)
    )


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, nullable=False, primary_key=True),
    )
    user_uid: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID, ForeignKey("users.uid", ondelete="CASCADE"), nullable=True)
    )
    board_uid: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID, ForeignKey("boards.uid", ondelete="CASCADE"), nullable=True)
    )
    message_content: Optional[str] = Field(default=None)
    message_type: NotificationType
    is_read: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(pg.TIMESTAMP)
    )


class Invitation(SQLModel, table=True):
    __tablename__ = "invitations"

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, nullable=False, primary_key=True),
    )
    user_uid: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID, ForeignKey("users.uid", ondelete="CASCADE"), nullable=True)
    )
    recipient_uid: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID, ForeignKey("users.uid", ondelete="CASCADE"), nullable=True)
    )
    board_uid: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID, ForeignKey("boards.uid", ondelete="CASCADE"), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(pg.TIMESTAMP)
    )
    accepted: bool = Field(default=False)


class Request(SQLModel, table=True):
    __tablename__ = "requests"

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, nullable=False, primary_key=True),
    )
    user_uid: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID, ForeignKey("users.uid", ondelete="CASCADE"), nullable=True)
    )
    board_uid: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID, ForeignKey("boards.uid", ondelete="CASCADE"), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(pg.TIMESTAMP)
    )
    status: RequestStatus = Field(default=RequestStatus.PENDING)