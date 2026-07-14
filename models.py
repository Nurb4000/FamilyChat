# models.py
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
Base = declarative_base()

# Association table for room-user permissions
room_user_association = Table('room_user_permissions', Base.metadata,
    Column('room_id', Integer, ForeignKey('rooms.id')),
    Column('user_id', Integer, ForeignKey('users.id'))
)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False) # Changed to not nullable
    is_admin = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True) # NEW: Enabled flag for login restriction
    pending = Column(Boolean, default=False) # NEW: Pending signup flag
    last_login = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow) # NEW: Track last page view
    created_at = Column(DateTime, default=datetime.utcnow)
    def __repr__(self):
        return f"<User(username='{self.username}', is_admin={self.is_admin}, enabled={self.enabled}, pending={self.pending})>"

class Room(Base):
    __tablename__ = 'rooms'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    private = Column(Boolean, default=False)  # NEW: Private room flag
    is_private_message_room = Column(Boolean, default=False)  # NEW: Flag for private message rooms
    sort_order = Column(Integer, default=0)  # NEW: Manual sort order for room tiles
    # Relationships
    posts = relationship("Post", back_populates="room", lazy='selectin')
    authorized_users = relationship("User", secondary=room_user_association, back_populates="authorized_rooms")
    def __repr__(self):
        return f"<Room(name='{self.name}', private={self.private}, is_private_message_room={self.is_private_message_room})>"

class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    image_filename = Column(String(255)) # Store image filename
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    room_id = Column(Integer, ForeignKey('rooms.id'))
    # Relationships
    user = relationship("User", lazy='selectin')
    room = relationship("Room", back_populates="posts")
    replies = relationship("Reply", back_populates="post", lazy='selectin')
    def __repr__(self):
        return f"<Post(title='{self.title}')>"

class Reply(Base):
    __tablename__ = 'replies'
    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    image_filename = Column(String(255)) # Store image filename
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    post_id = Column(Integer, ForeignKey('posts.id'))
    # Relationships
    user = relationship("User", lazy='selectin')
    post = relationship("Post", back_populates="replies")
    def __repr__(self):
        return f"<Reply(content='{self.content[:50]}...')>"

class PrivateMessageRoom(Base):
    __tablename__ = 'private_message_rooms'
    id = Column(Integer, primary_key=True)
    user1_id = Column(Integer, ForeignKey('users.id'))
    user2_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    # Relationships
    user1 = relationship("User", foreign_keys=[user1_id])
    user2 = relationship("User", foreign_keys=[user2_id])
    messages = relationship("PrivateMessage", back_populates="room", lazy='selectin')

class PrivateMessage(Base):
    __tablename__ = 'private_messages'
    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    image_filename = Column(String(255)) # Store image filename
    created_at = Column(DateTime, default=datetime.utcnow)
    sender_id = Column(Integer, ForeignKey('users.id'))
    room_id = Column(Integer, ForeignKey('private_message_rooms.id'))
    read = Column(Boolean, default=False)
    # Relationships
    sender = relationship("User")
    room = relationship("PrivateMessageRoom", back_populates="messages")

# Add relationship to User model
User.authorized_rooms = relationship("Room", secondary=room_user_association, back_populates="authorized_users")