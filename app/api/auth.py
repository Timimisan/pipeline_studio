import uuid
import httpx
from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users import BaseUserManager, models, FastAPIUsers, InvalidPasswordException, exceptions
from fastapi_users.authentication import JWTStrategy, CookieTransport, AuthenticationBackend
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from httpx_oauth.clients.google import GoogleOAuth2
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import Response
from fastapi.responses import RedirectResponse

from app.core.db import User, get_db, OAuthAccount
import os

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
# ============================================================
# CONFIG
# ============================================================
SECRET = "CHANGE_THIS_TO_A_32_BYTE_RANDOM_STRING"  # Use env var in production
COOKIE_NAME = "coldemail_auth"


# ============================================================
# USER DATABASE ADAPTEr
# ============================================================
async def get_user_db(session: AsyncSession=Depends(get_db)):
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)




# ============================================================
# USER MANAGER
# ============================================================
class UserManager(BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register( self, user: models.UP, request: Request | None = None) -> None:
        print("REGISTERED", user.email)
        if user.is_verified:
            return
        return await self.request_verify(user, request)


    async def on_after_request_verify(self, user: models.UP, token: str, request: Request | None = None) -> None:
        await send_verification_email(user, token, request)

    async def on_after_verify(self, user: models.UP, request: Request | None = None) -> None:
        print(f"verification successful")

    async def on_after_login(
        self,
        user: models.UP,
        request: Request | None = None,
        response: Response | None = None,
    ) -> None:
        print("LOGEDIN", user.email)

    # ============================================================
    # PASSWORD RECOVERY
    # ============================================================
    async def on_after_forgot_password(self, user: models.UP, token: str, request: Request | None = None) -> None:
        return await send_reset_email(user, token, request)

    async def on_after_reset_password(self, user: models.UP, request: Request | None = None) -> None:
        print("password reset successful")


    # ============================================================
    # TOKEN AUTH
    # ============================================================
    def parse_id(self, user_id: str) -> uuid.UUID:
        return uuid.UUID(user_id)

    async def authenticate(self, credentials: OAuth2PasswordRequestForm) -> models.UP | None:
        try:

            user = await self.get_by_email(credentials.username)
            if user.is_verified:
                print('user verified')
            if not user.is_verified:
                return None
        except exceptions.UserNotExists:
            # Run the hasher to mitigate timing attack
            # Inspired from Django: https://code.djangoproject.com/ticket/20760
            self.password_helper.hash(credentials.password)
            return None

        verified, updated_password_hash = self.password_helper.verify_and_update(
            credentials.password, user.hashed_password
        )
        if not verified:
            return None
        # Update password hash to a more robust one if needed
        if updated_password_hash is not None:
            await self.user_db.update(user, {"hashed_password": updated_password_hash})

        return user




async def send_verification_email(user: models.UP, token: str, request: Request | None = None) -> None:
    base_url = str(request.base_url).rstrip("/") if request else "http://localhost:5173"

    #frontend_url = "http://localhost:5173"
    #link = f"{base_url}/verify-email?token={token}"
    link = f"{base_url}/verify-email?token={token}"

    async with httpx.AsyncClient() as client:
        await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}"
            },
            json={
                "from": "onboarding@resend.dev",
                "to": user.email,
                "subject": "Verify your email",
                "html": f"""
                            <h2>Verify your email</h2>
                            <p>Click the button below:</p>
                            <a href="{link}">Verify Email</a>
                        """
            }
        )

async def send_reset_email(user: models.UP, token: str, request: Request | None = None) -> None:
    base_url = str(request.base_url).rstrip("/") if request else "http://localhost:5173"

    link = f"{base_url}/reset-password?token={token}"

    async with httpx.AsyncClient() as client:
        await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}"
            },
            json={
                "from": "onboarding@resend.dev",
                "to": user.email,
                "subject": "Reset Your Password",
                "html": f"""
                            <h2>Reset your password</h2>
                            <p>Click the button below:</p>
                            <a href="{link}">Reset Password</a>
                        """
            }
        )




async def get_user_manager(user_db = Depends(get_user_db)):
    yield UserManager(user_db)

google_oauth_client = GoogleOAuth2(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    scopes=["openid", "email", "profile"],
)

# ============================================================
# TRANSPORTATION AND AUTHORIZATION
# ============================================================
cookie_transport = CookieTransport(
        cookie_name = COOKIE_NAME,
        cookie_max_age = 3600 * 24 * 7,
        cookie_secure = False, # change to True in production
        cookie_httponly = False # change to True in production
)

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds = 3600 *24 * 7)

auth_backend = AuthenticationBackend(
    name= "cookie",
    transport = cookie_transport,
    get_strategy = get_jwt_strategy
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)