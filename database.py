from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Create database file in your project folder
Base = declarative_base()
import os

# Use PostgreSQL on Render, SQLite locally
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///jambuster.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# ============================================
# USER TABLE
# ============================================
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_premium = Column(Integer, default=0)
    premium_expiry = Column(DateTime, nullable=True)
    is_admin = Column(Integer, default=0)      # 🔥 ADD THIS LINE
    last_active = Column(DateTime, default=datetime.utcnow)  # 🔥 ADD THIS LINE
# ============================================
# CHAT HISTORY TABLE
# ============================================
class ChatHistory(Base):
    __tablename__ = 'chat_history'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    subject = Column(String)
    user_message = Column(Text)
    ai_response = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Create the database tables
Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
