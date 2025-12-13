"""
Authentication Endpoints
Login, Register, Token Refresh
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional

from app.config import settings

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============ PYDANTIC MODELS ============

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    company_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    company_name: Optional[str] = None


# ============ HELPER FUNCTIONS ============

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ============ ENDPOINTS ============

@router.post("/register", response_model=UserResponse)
async def register(user: UserRegister):
    """
    Register a new user
    """
    # TODO: Check if email already exists in database
    # TODO: Save user to database
    
    # For MVP, return mock response
    user_id = "user-" + str(hash(user.email))[:8]
    
    return UserResponse(
        id=user_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        company_name=user.company_name
    )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """
    Login and receive JWT tokens
    """
    # TODO: Verify credentials against database
    # TODO: Check if user exists and password matches
    
    # For MVP, accept any credentials and return tokens
    user_id = "user-" + str(hash(credentials.email))[:8]
    
    access_token = create_access_token({"sub": user_id, "email": credentials.email})
    refresh_token = create_refresh_token({"sub": user_id})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token
    """
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        new_access_token = create_access_token({"sub": user_id})
        new_refresh_token = create_refresh_token({"sub": user_id})
        
        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token
        )
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/me", response_model=UserResponse)
async def get_current_user():
    """
    Get current authenticated user
    """
    # TODO: Extract user from JWT token
    # TODO: Fetch user from database
    
    return UserResponse(
        id="user-demo",
        email="demo@ews-gmbh.de",
        first_name="Demo",
        last_name="User",
        company_name="EWS GmbH"
    )
