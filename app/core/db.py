from __future__ import annotations
import uuid
import os
from datetime import datetime, timezone
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseOAuthAccountTableUUID, SQLAlchemyBaseUserTableUUID
from sqlalchemy import (Column, Integer, String, Text, ForeignKey, Boolean, DateTime, JSON, Float)
from sqlalchemy.orm import declarative_base, Mapped, relationship
from sqlalchemy.ext.asyncio import (create_async_engine, async_sessionmaker, AsyncSession)
from sqlalchemy.dialects.postgresql import UUID
from dotenv import load_dotenv
import asyncio

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# ------------------------------------------------------------------
# 1. ENGINE FIX: statement_cache_size=0 prevents DuplicatePreparedStatementError
#    during uvicorn --reload (asyncpg cache collisions).
# ------------------------------------------------------------------
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"statement_cache_size": 0}
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


# ============================================================
# USER  (fastapi-users compatible)
# ============================================================
class User(SQLAlchemyBaseUserTableUUID, Base):
    """User model for fastapi-users.

    Inherits from SQLAlchemyBaseUserTableUUID which provides:
      - id (UUID primary key)
      - email (indexed, unique)
      - hashed_password
      - is_active, is_superuser, is_verified
    """
    __tablename__ = "users"

    # OAuth fields (optional)
    oauth_provider = Column(String, nullable=True)
    oauth_account_id = Column(String, nullable=True)

    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        "OAuthAccount", back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )

    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc)
    )


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    __tablename__ = "oauth_accounts"

    user_id = Column(ForeignKey("users.id"), nullable=False)

    user: Mapped["User"] = relationship(
        "User",
        back_populates="oauth_accounts"
    )


# ============================================================
# PROBLEM
# ============================================================

class Problem(Base):
    __tablename__ = "problems"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    problem_name = Column(String, nullable=False)
    core_problem = Column(Text, nullable=False)
    system = Column(String, nullable=False)

    causal_mechanism = Column(Text, nullable=False)

    failure_mode_A = Column(Text, nullable=False)
    failure_mode_B = Column(Text, nullable=False)

    failure_mode_A_mechanism = Column(Text, nullable=False)
    failure_mode_B_mechanism = Column(Text, nullable=False)

    contradiction = Column(Text, nullable=False)

    business_impact = Column(Text, nullable=False)

    solution_mechanism = Column(Text, nullable=False)
    solution_actor = Column(Text, nullable=False)

    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc)
    )


# ============================================================
# CONTEXT
# ============================================================

class Context(Base):
    __tablename__ = "contexts"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    problem_id = Column(
        UUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    industry = Column(String, nullable=False)
    company_size = Column(String, nullable=False)

    decision_actor = Column(String, nullable=False)

    extra = Column(Text)

    constraints = Column(JSON, nullable=False)

    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc)
    )


# ============================================================
# REASONING STATE  (multiple per context allowed)
# ============================================================

class ReasoningState(Base):
    __tablename__ = "reasoning_states"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    context_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contexts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    failure_mode_A = Column(Text)
    failure_mode_B = Column(Text)

    valid = Column(Boolean, default=False)
    selected = Column(Boolean, default=False)

    score = Column(Float)
    scores = Column(JSON)

    confidence = Column(Float)

    output_json = Column(JSON)

    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc)
    )


# ============================================================
# SUBJECT  (one per reasoning state)
# ============================================================

class SubjectTrace(Base):
    __tablename__ = "subject_traces"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    context_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contexts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    reasoning_state_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reasoning_states.id", ondelete="CASCADE"),
        index=True,
        unique=True
    )

    subject_text = Column(Text, nullable=False)

    score = Column(Float)
    scores = Column(JSON)

    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc)
    )


# ============================================================
# HOOK  (one per reasoning state)
# ============================================================

class HookTrace(Base):
    __tablename__ = "hook_traces"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    context_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contexts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )


    reasoning_state_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reasoning_states.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    hook_text = Column(Text, nullable=False)

    score = Column(Float)
    scores = Column(JSON)

    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc)
    )


# ============================================================
# TENSION  (one per reasoning state)
# ============================================================

class TensionTrace(Base):
    __tablename__ = "tension_traces"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    context_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contexts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    reasoning_state_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reasoning_states.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    tension_text = Column(Text, nullable=False)

    score = Column(Float)
    scores = Column(JSON)

    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc)
    )


# ============================================================
# TRANSITION QUESTION  (one per reasoning state)
# ============================================================

class TransitionQuestion(Base):
    __tablename__ = "transition_questions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    context_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contexts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    reasoning_state_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reasoning_states.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    question_text = Column(Text, nullable=False)

    score = Column(Float)
    scores = Column(JSON)

    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc)
    )


# ============================================================
# AUTHORITY  (one per reasoning state)
# ============================================================

class AuthorityTrace(Base):
    __tablename__ = "authority_traces"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    context_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contexts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    reasoning_state_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reasoning_states.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    authority_text = Column(Text, nullable=False)

    score = Column(Float)
    scores = Column(JSON)

    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc)
    )


# ============================================================
# CTA  (one per reasoning state)
# ============================================================

class CtaTrace(Base):
    __tablename__ = "cta_traces"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    context_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contexts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    reasoning_state_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reasoning_states.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    cta_text = Column(Text, nullable=False)

    score = Column(Float)
    scores = Column(JSON)

    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc)
    )


# ============================================================
# FINAL EMAIL  (one per reasoning state)
# ============================================================

class FinalEmail(Base):
    __tablename__ = "final_emails"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    context_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contexts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    reasoning_state_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reasoning_states.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    final_email = Column(Text, nullable=False)

    total_latency = Column(Float)
    total_cost = Column(Float)

    total_input_tokens = Column(Integer)
    total_output_tokens = Column(Integer)

    overall_score = Column(Float)

    overall_scores = Column(JSON)

    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc)
    )


# ============================================================
# STAGE ATTEMPTS  (many per reasoning state)
# ============================================================

class StageAttempt(Base):
    __tablename__ = "stage_attempts"

    attempt_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    context_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contexts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    reasoning_state_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reasoning_states.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    stage_name = Column(Text, nullable=False)

    attempt_number = Column(Integer, nullable=False)

    status = Column(Text, nullable=False)

    failure_reason = Column(Text)
    failure_mode = Column(Text)

    valid = Column(Boolean)
    selected = Column(Boolean)

    score = Column(Float)
    scores = Column(JSON)

    confidence = Column(Float)

    latency = Column(Float)

    cost = Column(Float)

    input_tokens = Column(Integer)
    output_tokens = Column(Integer)

    model_name = Column(Text)

    output_text = Column(Text)

    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc)
    )


# ============================================================
# INIT
# ============================================================

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def get_db():
    """
    FastAPI dependency that yields an async SQLAlchemy session.
    Handles disconnects gracefully.
    """

    session: AsyncSession = AsyncSessionLocal()

    try:
        yield session
        await session.commit()

    except asyncio.CancelledError:
        try:
            await session.rollback()
        except asyncio.CancelledError:
            pass

        raise

    except Exception:
        await session.rollback()
        raise

    finally:
        try:
            await session.close()
        except asyncio.CancelledError:
            pass