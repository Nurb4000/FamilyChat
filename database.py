# database.py
import os
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, User, Room, Post, Reply, PrivateMessageRoom, PrivateMessage

def init_database():
    # Create database engine
    engine = create_engine('sqlite:///family_chat.db')
    # Create all tables
    Base.metadata.create_all(engine)
    # Migration: Add sort_order column to rooms table if not present
    try:
        conn = engine.connect()
        conn.execute(text("PRAGMA table_info(rooms)"))
        rows = conn.execute(text("PRAGMA table_info(rooms)")).fetchall()
        columns = [row[1] for row in rows]
        if 'sort_order' not in columns:
            conn.execute(text("ALTER TABLE rooms ADD COLUMN sort_order INTEGER DEFAULT 0"))
            conn.commit()
            print("Added sort_order column to rooms table")
        conn.close()
    except Exception as e:
        print(f"Migration note: {e}")
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    # Check if admin user exists, if not create it
    admin_user = session.query(User).filter_by(username='admin').first()
    if not admin_user:
        from werkzeug.security import generate_password_hash
        admin = User(
            username='admin',
            password=generate_password_hash('admin'),
            email='admin@familychat.local',
            is_admin=True,
            enabled=True
        )
        session.add(admin)
        session.commit()
        print("Admin user created: admin/admin")
    # Check if default rooms exist
    rooms = session.query(Room).all()
    if not rooms:
        # Create some default rooms
        default_rooms = [
            Room(name='Family Events', description='Planned family events', sort_order=1),
            Room(name='General Discussion', description='Talk about anything and everything, but keep it cordial', sort_order=2),
            Room(name='News', description='Board news, and important world and local events', sort_order=3),
            Room(name='Music', description='Discuss music and artists. No DISCO or RAP! That isn\'t music! :)', sort_order=4),
            Room(name='The Zoo', description='All about our pets and wild animals.', sort_order=5),
            Room(name='Technology', description='Discuss tech stuff.', sort_order=6),
        ]
        for room in default_rooms:
            session.add(room)
        session.commit()
        print("Default rooms created")
    session.close()
    return engine

if __name__ == '__main__':
    init_database()
