#!/usr/bin/env python3
"""
Auth Service - REFACTORED to use shared modules
Port: 8001
Purpose: Authentication, Authorization, User Management

This is a fully refactored version showing best practices for using shared modules.
Compare with main.py to see the reduction in code duplication.
"""

from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt
import os

# ============================================================================
# IMPORT FROM SHARED MODULES - No Duplication!
# ============================================================================

from shared.core.database import get_db, engine
from shared.core.config import settings
from shared.models import User, UserRole
from shared.auth_utils import (
    setup_logging,
    log_request,
    log_error,
    get_current_user,
)

# ============================================================================
# SERVICE CONFIGURATION
# ============================================================================

SERVICE_NAME = "auth-service"
SERVICE_PORT = 8001

# Setup logging
logger = setup_logging(SERVICE_NAME)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================================================================
# PYDANTIC MODELS (Request/Response)
# ============================================================================

class UserCreate(BaseModel):
    """User creation request"""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "viewer"


class UserResponse(BaseModel):
    """User response"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Login request"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class PasswordChange(BaseModel):
    """Password change request"""
    old_password: str
    new_password: str


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Authentication Service",
    description="Handles authentication, authorization, and user management",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(user_id: int, username: str, email: str, role: str) -> tuple[str, str]:
    """
    Create access and refresh tokens
    Returns: (access_token, refresh_token)
    """
    # Access token
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_payload = {
        "sub": str(user_id),
        "username": username,
        "email": email,
        "role": role,
        "type": "access",
        "exp": datetime.now(timezone.utc) + access_token_expires,
        "iat": datetime.now(timezone.utc),
    }
    access_token = jwt.encode(
        access_payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    # Refresh token
    refresh_token_expires = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + refresh_token_expires,
        "iat": datetime.now(timezone.utc),
    }
    refresh_token = jwt.encode(
        refresh_payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return access_token, refresh_token


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    log_request(logger, request, None, f"User registration attempt: {user_data.username}")

    try:
        # Check if user exists
        existing_user = db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )

        # Create user
        hashed_password = hash_password(user_data.password)
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=user_data.role,
            active=True,
            created_at=datetime.now(timezone.utc)
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        log_request(logger, request, new_user.id, f"User registered successfully: {new_user.username}")
        return new_user

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log_error(logger, request, None, e, "User registration failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Login and get access token"""
    log_request(logger, request, None, f"Login attempt: {login_data.username}")

    try:
        # Find user
        user = db.query(User).filter(User.username == login_data.username).first()

        if not user or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )

        if not user.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        # Create tokens
        access_token, refresh_token = create_access_token(
            user.id, user.username, user.email, user.role
        )

        log_request(logger, request, user.id, f"Login successful: {user.username}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.from_orm(user)
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, request, None, e, "Login failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user information"""
    log_request(logger, request, current_user.id, "Fetching current user info")

    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.put("/me/password")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change current user's password"""
    log_request(logger, request, current_user.id, "Password change attempt")

    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify old password
        if not verify_password(password_data.old_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect password")

        # Update password
        user.hashed_password = hash_password(password_data.new_password)
        db.commit()

        log_request(logger, request, current_user.id, "Password changed successfully")
        return {"message": "Password updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log_error(logger, request, current_user.id, e, "Password change failed")
        raise HTTPException(status_code=500, detail="Password change failed")


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List all users (admin only would check role here)"""
    log_request(logger, request, current_user.id, "Listing users")

    users = db.query(User).offset(skip).limit(limit).all()
    return users


# ============================================================================
# REGISTER ROUTES
# ============================================================================

app.include_router(router)


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info(f"🚀 {SERVICE_NAME} starting up...")
    logger.info(f"📊 Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}")
    logger.info(f"🔐 JWT Algorithm: {settings.JWT_ALGORITHM}")
    logger.info(f"✅ {SERVICE_NAME} ready on port {SERVICE_PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info(f"👋 {SERVICE_NAME} shutting down...")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=True,
        log_level="info"
    )
