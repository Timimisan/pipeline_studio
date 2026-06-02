from uuid import UUID
from pydantic import ConfigDict
from fastapi_users.schemas import BaseUser, BaseUserCreate, BaseUserUpdate


# ============================================================
# USER SCHEMAS (required by fastapi-users)
# ============================================================

class UserRead(BaseUser[UUID]):
    """Schema for reading user data (returned by /auth/me and /users/me)."""
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseUserCreate):
    """Schema for user registration (POST /auth/register).

    Inherits from BaseUserCreate which provides:
    - email: EmailStr
    - password: str
    - create_update_dict() method (required by UserManager.create())
    """
    pass


class UserUpdate(BaseUserUpdate):
    """Schema for updating user (PATCH /users/me).

    Inherits from BaseUserUpdate which provides:
    - password: Optional[str] = None
    - email: Optional[EmailStr] = None
    - create_update_dict() method
    """
    pass