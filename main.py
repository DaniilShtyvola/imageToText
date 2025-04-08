
import os
import jwt
import secrets
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./users.db")

Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user")
    subscription_status = Column(String, default="inactive")
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    session_duration = Column(Float, nullable=True)
    activity_count_last_30_days = Column(Integer, default=0)
    is_blocked = Column(Integer, default=0) 
    block_reason = Column(String, nullable=True)
    blocked_by = Column(String, nullable=True)  
    blocked_at = Column(DateTime, nullable=True)

Base.metadata.create_all(bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db: Session, name: str):
    return db.query(User).filter(User.name == name).first()

def create_user(db: Session, name: str, password: str, role: str = "user"):
    user = User(name=name, hashed_password=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def count_user_activity_in_last_30_days(user: User, db: Session):
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    activity_count = db.query(User).filter(User.id == user.id, User.last_login > thirty_days_ago).count()
    return activity_count

def update_activity_count(user: User, db: Session):
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    login_count = db.query(User).filter(User.id == user.id, User.last_login > thirty_days_ago).count()
    user.activity_count_last_30_days = login_count
    db.commit()

class UserResponse(BaseModel):
    name: str
    password: str
    role: str
    subscription_status: str
    block_reason: Optional[str] = None 
    blocked_by: Optional[str] = None 
    blocked_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    name: str
    password: str
    role: str = "user"

class SubscriptionUpdate(BaseModel):
    subscription_status: str

class BlockUserRequest(BaseModel):
    is_blocked: bool
    block_reason: Optional[str] = None

@app.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    if get_user(db, user.name):
        raise HTTPException(status_code=400, detail="User already exists")
    create_user(db, user.name, user.password, user.role)
    return {"message": "User registered"}

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    if user.is_blocked:
        block_info = {
            "blocked_by": user.blocked_by,
            "block_reason": user.block_reason,
            "blocked_at": user.blocked_at
        }
        raise HTTPException(
            status_code=403, 
            detail=f"User is blocked. Details: Blocked by: {block_info['blocked_by']}, Reason: {block_info['block_reason']}, Time: {block_info['blocked_at']}"
        )

    now = datetime.utcnow()
    if user.last_login:
        user.session_duration = (now - user.last_login).total_seconds()

    user.last_login = now
    db.commit()

    update_activity_count(user, db)

    access_token = create_access_token(data={"sub": user.name, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        name: str = payload.get("sub")
        role: str = payload.get("role")
        if name is None or role is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user = get_user(db, name)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        if user.is_blocked:
            raise HTTPException(status_code=403, detail="User is blocked")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"name": current_user.name, "role": current_user.role}

@app.get("/subscription_status/{username}")
async def get_subscription_status(username: str, db: Session = Depends(get_db)):
    user = get_user(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"username": user.name, "subscription_status": user.subscription_status}

@app.get("/users", response_model=list[UserResponse])
async def get_all_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can view all users")
    users = db.query(User).all()
    return [
        {"name": user.name, "password": user.hashed_password, "role": user.role, "subscription_status": user.subscription_status}
        for user in users
    ]

@app.get("/analytics")
def get_analytics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    users = db.query(User).all()
    return [
        {
            "username": user.name,
            "registered_at": user.registered_at,
            "last_login": user.last_login,
            "session_duration": user.session_duration,
            "activity_last_30_days": user.activity_count_last_30_days,
        }
        for user in users
    ]

@app.get("/analytics/{username}")
def get_user_analytics(username: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    target_user = get_user(db, username)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Only admin")

    return {
        "username": target_user.name,
        "registered_at": target_user.registered_at,
        "last_login": target_user.last_login,
        "session_duration": target_user.session_duration,
        "activity_last_30_days": target_user.activity_count_last_30_days
    }

@app.get("/blocked_users", response_model=list[UserResponse])
async def get_blocked_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can view blocked users")
    
    blocked_users = db.query(User).filter(User.is_blocked == 1).all() 
    return [
        {
            "name": user.name,
            "password": user.hashed_password,
            "role": user.role,
            "subscription_status": user.subscription_status,
            "block_reason": user.block_reason,
            "blocked_by": user.blocked_by,
            "blocked_at": user.blocked_at
        }
        for user in blocked_users
    ]

@app.put("/update_subscription/{username}")
async def update_subscription(username: str, update_data: SubscriptionUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can update subscriptions")
    user = get_user(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.subscription_status = update_data.subscription_status
    db.commit()
    return {"message": f"Subscription status updated to {update_data.subscription_status}"}

@app.put("/block_user/{username}")
async def block_user(username: str, request: BlockUserRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can block users")
    user = get_user(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_blocked = 1 if request.is_blocked else 0
    user.block_reason = request.block_reason
    user.blocked_by = current_user.name  
    user.blocked_at = datetime.utcnow() 
    db.commit()

    status_text = "blocked" if request.is_blocked else "unblocked"
    return {"message": f"User {username} has been {status_text} by {current_user.name} with reason: {request.block_reason if request.block_reason else 'No reason provided'}"}
