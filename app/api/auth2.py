from __future__ import annotations
from typing import Optional
import uuid
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import User, get_db

# ============================================================
# CONFIG
# ============================================================

SECRET = "CHANGE_THIS_TO_A_32_BYTE_RANDOM_STRING"  # Use env var in production
COOKIE_NAME = "coldemail_auth"


# ============================================================
# USER DATABASE ADAPTER
# ============================================================

async def get_user_db(session: AsyncSession = Depends(get_db)):
    yield SQLAlchemyUserDatabase(session, User)


# ============================================================
# USER MANAGER
# ============================================================

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


# ============================================================
# AUTHENTICATION BACKEND (httpOnly cookie)
# ============================================================

cookie_transport = CookieTransport(
    cookie_name=COOKIE_NAME,
    cookie_max_age=3600 * 24 * 7,  # 7 days
    cookie_httponly=True,
    cookie_secure=False,  # Set True in production (HTTPS only)
    cookie_samesite="lax",
)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600 * 24 * 7)


auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)


# ============================================================
# FASTAPI-USERS INSTANCE
# ============================================================

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

# Dependency to inject current user into protected routes
current_active_user = fastapi_users.current_user(active=True)