import os
from fastapi import FastAPI, APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from httpx_oauth.integrations.fastapi import OAuth2AuthorizeCallback
from httpx_oauth.oauth2 import OAuth2Token
from fastapi_users import models
from fastapi_users.authentication import Strategy
from fastapi_users.exceptions import UserAlreadyExists
from fastapi_users.jwt import decode_jwt
from fastapi_users.manager import BaseUserManager
from fastapi_users.router.common import ErrorCode, ErrorModel
import jwt

from app.core.db import engine, Base
from app.api.routes import router
from app.api.auth import fastapi_users, auth_backend, google_oauth_client, SECRET
from app.models.user_models import UserRead, UserCreate, UserUpdate


# ============================================================
# CONFIG
# ============================================================
STATE_TOKEN_AUDIENCE = "fastapi-users:oauth-state"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
    print("engine emptied")


app = FastAPI(lifespan=lifespan)

# ============================================================
# CORS
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# STANDARD AUTH ROUTES
# ============================================================
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# ============================================================
# GOOGLE OAUTH — custom callback that sets cookie + redirects
# ============================================================

# 1. Generate the default OAuth router
google_oauth_router = fastapi_users.get_oauth_router(
    google_oauth_client,
    auth_backend,
    SECRET,
    redirect_url="http://localhost:8000/auth/google/callback",
    associate_by_email=True,
    is_verified_by_default=True,
)

# 2. Strip the built-in /callback so we can replace it
google_oauth_router.routes = [
    route for route in google_oauth_router.routes
    if not (hasattr(route, "path") and route.path.endswith("/callback"))
]

# 3. Re-implement callback: identical logic, but set cookie AND redirect
oauth_callback_router = APIRouter()

oauth2_authorize_callback = OAuth2AuthorizeCallback(
    google_oauth_client,
    redirect_url="http://localhost:8000/auth/google/callback",
)


@oauth_callback_router.get(
    "/callback",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorModel,
            "content": {
                "application/json": {
                    "examples": {
                        "INVALID_STATE_TOKEN": {
                            "summary": "Invalid state token.",
                            "value": None,
                        },
                        ErrorCode.LOGIN_BAD_CREDENTIALS: {
                            "summary": "User is inactive.",
                            "value": {"detail": ErrorCode.LOGIN_BAD_CREDENTIALS},
                        },
                    }
                }
            },
        },
    },
)
async def google_oauth_callback(
    request: Request,
    access_token_state: tuple[OAuth2Token, str] = Depends(oauth2_authorize_callback),
    user_manager: BaseUserManager[models.UP, models.ID] = Depends(fastapi_users.get_user_manager),
    strategy: Strategy[models.UP, models.ID] = Depends(auth_backend.get_strategy),
):
    token, state = access_token_state

    # Validate CSRF state token
    try:
        decode_jwt(state, SECRET, [STATE_TOKEN_AUDIENCE])
    except jwt.DecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    # Get Google account info
    account_id, account_email = await google_oauth_client.get_id_email(token["access_token"])

    if account_email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.OAUTH_NOT_AVAILABLE_EMAIL,
        )

    # Run fastapi-users oauth logic (create/link user)
    try:
        user = await user_manager.oauth_callback(
            google_oauth_client.name,
            token["access_token"],
            account_id,
            account_email,
            token.get("expires_at"),
            token.get("refresh_token"),
            request,
            associate_by_email=True,
            is_verified_by_default=True,
        )
    except UserAlreadyExists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.OAUTH_USER_ALREADY_EXISTS,
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.LOGIN_BAD_CREDENTIALS,
        )

    # ===================================================================
    # CRITICAL FIX: Actually log the user in so the cookie gets set
    # ===================================================================
    # This generates the JWT AND creates the Set-Cookie header via transport
    login_response = await auth_backend.login(strategy, user)

    # Also grab the raw token to pass to frontend via URL
    jwt_token = await strategy.write_token(user)

    # Build redirect response and copy the Set-Cookie header into it
    redirect = RedirectResponse(
        url=f"{FRONTEND_URL}/login?token={jwt_token}",
        status_code=302,
    )

    # Copy Set-Cookie header(s) from the login response
    for header_name, header_value in login_response.headers.items():
        if header_name.lower() == "set-cookie":
            redirect.headers.append("set-cookie", header_value)

    return redirect


# 4. Mount both routers
app.include_router(google_oauth_router, prefix="/auth/google", tags=["auth"])
app.include_router(oauth_callback_router, prefix="/auth/google", tags=["auth"])

# ============================================================
# API ROUTES
# ============================================================
app.include_router(router, prefix="/api")
# Check what client_id is actually being used
print(f"Google OAuth client_id: {google_oauth_client.client_id}")