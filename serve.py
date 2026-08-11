import os
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from groq import Groq
from database import SessionLocal, User, ChatHistory, get_db
from sqlalchemy.orm import Session
from sqlalchemy import func

app = FastAPI(title="JAMBuster AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================
# GROQ API KEY
# ================================================
GROQ_API_KEY = "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"
client = Groq(api_key=GROQ_API_KEY)
security = HTTPBearer()

# Simple session storage (tokens)
active_sessions = {}

# ================================================
# AUTHENTICATION FUNCTIONS
# ================================================
def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_token(username: str) -> str:
    """Create a session token"""
    token = secrets.token_hex(32)
    active_sessions[token] = username
    return token

def get_user_from_token(token: str):
    """Get username from token"""
    return active_sessions.get(token)

# ================================================
# SERVE THE WEBSITE
# ================================================
@app.get("/")
def serve_index():
    """Serve the main HTML page"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "index.html")
    return FileResponse(file_path)

# ================================================
# AUTHENTICATION ENDPOINTS
# ================================================
@app.post("/api/register")
async def register(username: str, email: str, password: str, db: Session = Depends(get_db)):
    """Register a new user"""
    existing_user = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing_user:
        return {"success": False, "error": "Username or email already exists"}
    
    new_user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        created_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"success": True, "message": "User created successfully"}

@app.post("/api/login")
async def login(username: str, password: str, db: Session = Depends(get_db)):
    """Login user"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return {"success": False, "error": "User not found"}
    if user.password_hash != hash_password(password):
        return {"success": False, "error": "Incorrect password"}
    
    token = create_token(username)
    return {
        "success": True,
        "token": token,
        "username": username,
        "is_premium": bool(user.is_premium)
    }

@app.post("/api/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user"""
    token = credentials.credentials
    if token in active_sessions:
        del active_sessions[token]
    return {"success": True, "message": "Logged out"}

@app.get("/api/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user info"""
    token = credentials.credentials
    username = get_user_from_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "username": user.username,
        "email": user.email,
        "is_premium": bool(user.is_premium),
        "created_at": user.created_at
    }

# ================================================
# CHAT HISTORY ENDPOINTS
# ================================================
@app.post("/api/chat/save")
async def save_chat(
    subject: str,
    user_message: str,
    ai_response: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Save a chat to history"""
    token = credentials.credentials
    username = get_user_from_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    chat = ChatHistory(
        user_id=user.id,
        subject=subject,
        user_message=user_message,
        ai_response=ai_response
    )
    db.add(chat)
    db.commit()
    return {"success": True, "message": "Chat saved"}

@app.get("/api/chat/history")
async def get_chat_history(
    limit: int = 50,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get user's chat history"""
    token = credentials.credentials
    username = get_user_from_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    chats = db.query(ChatHistory).filter(
        ChatHistory.user_id == user.id
    ).order_by(ChatHistory.timestamp.desc()).limit(limit).all()
    
    return {
        "success": True,
        "chats": [
            {
                "subject": chat.subject,
                "user_message": chat.user_message,
                "ai_response": chat.ai_response,
                "timestamp": chat.timestamp
            }
            for chat in chats
        ]
    }

@app.delete("/api/chat/history")
async def clear_chat_history(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Clear user's chat history"""
    token = credentials.credentials
    username = get_user_from_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.query(ChatHistory).filter(ChatHistory.user_id == user.id).delete()
    db.commit()
    return {"success": True, "message": "Chat history cleared"}

# ================================================
# AI CHAT ENDPOINT
# ================================================
@app.post("/api/chat")
async def chat(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Chat with AI (requires login)"""
    token = credentials.credentials
    username = get_user_from_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    body = await request.json()
    question = body.get("question")
    subject = body.get("subject", "General")
    
    if not question:
        return {"success": False, "error": "No question provided"}
    
    prompt = f"""
    You are a JAMB tutor. Answer this question in Pidgin English and simple English.
    
    Subject: {subject}
    Question: {question}
    
    Instructions:
    - Start with "Make I break this down small-small."
    - Use Nigerian examples (food, football, market)
    - Keep it simple for SS3 students
    - If it's math, show step-by-step working
    - If it's physics, explain the formula first
    - If it's chemistry, use cooking analogies
    - End with "Any other question? Just ask me o!"
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
        )
        ai_response = chat_completion.choices[0].message.content
        return {
            "success": True,
            "response": ai_response,
            "powered_by": "Groq 🇳🇬"
        }
    except Exception as e:
        return {
            "success": False,
            "response": "Omo! Something went wrong. No worry, we go fix am!",
            "error": str(e)
        }

# ================================================
# ADMIN FUNCTIONS
# ================================================
def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify user is admin"""
    token = credentials.credentials
    username = get_user_from_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    
    if not user or user.is_admin != 1:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

@app.get("/api/admin/stats")
async def get_admin_stats(admin: User = Depends(get_current_admin)):
    """Get platform statistics (admin only)"""
    db = SessionLocal()
    total_users = db.query(User).count()
    today = datetime.utcnow().date()
    new_users_today = db.query(User).filter(User.created_at >= today).count()
    premium_users = db.query(User).filter(User.is_premium == 1).count()
    total_chats = db.query(ChatHistory).count()
    chats_today = db.query(ChatHistory).filter(ChatHistory.timestamp >= today).count()
    subjects = db.query(ChatHistory.subject, func.count(ChatHistory.subject)).group_by(ChatHistory.subject).all()
    subject_stats = {subject: count for subject, count in subjects}
    week_ago = datetime.utcnow() - timedelta(days=7)
    active_users_7d = db.query(User).filter(User.last_active >= week_ago).count()
    
    growth = []
    for i in range(7, -1, -1):
        date = datetime.utcnow().date() - timedelta(days=i)
        count = db.query(User).filter(
            User.created_at >= date,
            User.created_at < date + timedelta(days=1)
        ).count()
        growth.append({"date": date.strftime("%b %d"), "count": count})
    
    db.close()
    return {
        "success": True,
        "stats": {
            "total_users": total_users,
            "new_users_today": new_users_today,
            "premium_users": premium_users,
            "active_users_7d": active_users_7d,
            "total_chats": total_chats,
            "chats_today": chats_today,
            "subject_stats": subject_stats,
            "growth": growth
        }
    }

@app.get("/api/admin/users")
async def get_all_users(limit: int = 50, admin: User = Depends(get_current_admin)):
    db = SessionLocal()
    users = db.query(User).order_by(User.created_at.desc()).limit(limit).all()
    db.close()
    return {
        "success": True,
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_premium": bool(user.is_premium),
                "is_admin": bool(user.is_admin),
                "created_at": user.created_at,
                "last_active": user.last_active
            }
            for user in users
        ]
    }

@app.post("/api/admin/upgrade/{user_id}")
async def upgrade_user(user_id: int, admin: User = Depends(get_current_admin)):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        db.close()
        return {"success": False, "error": "User not found"}
    user.is_premium = 1
    user.premium_expiry = datetime.utcnow() + timedelta(days=30)
    db.commit()
    db.close()
    return {"success": True, "message": f"User {user.username} upgraded to premium!"}

@app.post("/api/support")
async def support(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Send support email to your Gmail"""
    body = await request.json()
    name = body.get('name')
    email = body.get('email')
    subject = body.get('subject')
    message = body.get('message')
    # Email sending code here
    return {"success": True, "message": "Support request sent!"}

@app.get("/admin")
async def serve_admin():
    """Serve the admin dashboard"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "admin.html")
    return FileResponse(file_path)

@app.get("/create-admin")
async def create_admin():
    """Create admin account (REMOVE AFTER USE)"""
    db = SessionLocal()
    existing = db.query(User).filter(User.username == "admin").first()
    if existing:
        db.close()
        return {"message": "Admin already exists"}
    
    admin = User(
        username="admin",
        email="ogundipeemmanuel31@gmail.com",
        password_hash=hash_password("admin12345"),
        is_admin=1,
        is_premium=1,
        created_at=datetime.utcnow()
    )
    db.add(admin)
    db.commit()
    db.close()
    return {"message": "✅ Admin account created! Username: admin, Password: admin12345"}

@app.get("/health")
def health():
    return {"status": "Healthy", "brain": "Groq", "builder": "Ogundipe Emmanuel", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
