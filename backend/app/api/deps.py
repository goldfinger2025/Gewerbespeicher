"""
API Dependencies
Shared dependencies for API endpoints
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.crud import user as user_crud


# Security scheme
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UUID:
    """
    Extract user ID from JWT token.
    Raises HTTPException if token is invalid or blacklisted.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ungültiges Authentifizierungstoken",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials

        # Check if token is blacklisted (logout)
        from app.api.v1.endpoints.auth import is_token_blacklisted
        if is_token_blacklisted(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token wurde invalidiert. Bitte erneut anmelden.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Check token type
        token_type = payload.get("type")
        if token_type != "access":
            raise credentials_exception

        # Get user ID from token
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception

        # Handle both old format (user-xxx) and new UUID format
        if user_id_str.startswith("user-"):
            # Legacy format - extract or convert
            raise credentials_exception

        return UUID(user_id_str)

    except (JWTError, ValueError):
        raise credentials_exception


async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from database.
    Raises HTTPException if user not found or inactive.
    """
    user = await user_crud.get_user_by_id(db, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzer nicht gefunden",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Benutzer ist deaktiviert",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Alias for get_current_user that ensures user is active"""
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and verify they are an admin.
    Raises HTTPException if not admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin-Berechtigung erforderlich",
        )
    return current_user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Optionally get current user if token is provided.
    Returns None if no valid token.
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        if payload.get("type") != "access":
            return None

        user_id_str = payload.get("sub")
        if not user_id_str or user_id_str.startswith("user-"):
            return None

        user_id = UUID(user_id_str)
        user = await user_crud.get_user_by_id(db, user_id)

        if user and user.is_active:
            return user

    except (JWTError, ValueError):
        pass

    return None
