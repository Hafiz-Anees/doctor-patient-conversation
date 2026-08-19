"""
security.py — JWT creation and FastAPI dependency for protected routes.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, DEMO_USERS

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class TokenData(BaseModel):
    email: str
    role: str
    name: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub", "")
        role: str = payload.get("role", "")
        name: str = payload.get("name", "")
        if not email:
            raise credentials_exception
        return TokenData(email=email, role=role, name=name)
    except JWTError:
        raise credentials_exception


def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    return verify_token(token)


def require_role(*roles: str):
    """Factory: returns a dependency that enforces one of the given roles."""

    def _check(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {list(roles)}",
            )
        return current_user

    return _check


# Convenience dependencies
require_nurse  = require_role("nurse", "admin")
require_doctor = require_role("doctor", "admin")
require_admin  = require_role("admin")
