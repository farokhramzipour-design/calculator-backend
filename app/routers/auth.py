from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.rate_limit import rate_limiter
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.core.deps import get_db_session
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(payload: RegisterRequest, request: Request, session=Depends(get_db_session)):
    rate_limiter.check(request)
    repo = UserRepository(session)
    existing = await repo.get_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = await repo.create(payload.email, hash_password(payload.password))
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, session=Depends(get_db_session)):
    rate_limiter.check(request)
    repo = UserRepository(session)
    user = await repo.get_by_email(payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, request: Request):
    rate_limiter.check(request)
    from app.core.security import decode_token

    try:
        decoded = decode_token(payload.refresh_token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc
    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    subject = decoded.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return TokenResponse(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


@router.post("/logout")
async def logout(request: Request):
    rate_limiter.check(request)
    return {"status": "ok"}
