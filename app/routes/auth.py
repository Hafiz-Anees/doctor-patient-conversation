"""
routes/auth.py — login endpoint that returns a JWT token.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from core.config import DEMO_USERS
from core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):
    user = DEMO_USERS.get(data.email)
    if not user or user["password"] != data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_access_token({
        "sub":  data.email,
        "role": user["role"],
        "name": user["name"],
    })
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        role=user["role"],
        name=user["name"],
    )


@router.get("/me")
def get_me(current_user=None):
    # Protected in main.py via dependency injection if needed
    return {"message": "Use /auth/login to get a token"}
