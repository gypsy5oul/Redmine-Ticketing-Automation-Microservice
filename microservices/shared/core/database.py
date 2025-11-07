#!/usr/bin/env python3
"""
Shared Database Connection Management for Microservices
This module provides database connectivity independent of the monolithic backend
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from redis import Redis
from redis.connection import ConnectionPool
from typing import Generator
import logging
import os

logger = logging.getLogger(__name__)

# Configuration from environment variables (no dependency on config module)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://devops_user:devops_password_change_this@postgres:5432/devops_tickets"
)
DATABASE_POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "20"))
DATABASE_MAX_OVERFLOW = int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))

# PostgreSQL Setup
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=DATABASE_POOL_SIZE,
    max_overflow=DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis Setup
try:
    redis_pool = ConnectionPool.from_url(
        REDIS_URL,
        max_connections=REDIS_MAX_CONNECTIONS,
        decode_responses=True,
    )
    redis_client = Redis(connection_pool=redis_pool)
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Redis features will be disabled.")
    redis_client = None


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_redis() -> Redis:
    """Dependency for getting Redis client"""
    if redis_client is None:
        raise RuntimeError("Redis client is not available")
    return redis_client


async def init_db():
    """Initialize database tables (async version for FastAPI)"""
    try:
        Base.metadata.create_all(bind=engine)
        _apply_post_schema_migrations()
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


def init_db_sync():
    """Initialize database tables (sync version for standalone scheduler)"""
    try:
        Base.metadata.create_all(bind=engine)
        _apply_post_schema_migrations()
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


async def close_db():
    """Close database connections (async version for FastAPI)"""
    try:
        engine.dispose()
        if redis_client:
            redis_client.close()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Error closing database: {e}")


def close_db_sync():
    """Close database connections (sync version for standalone scheduler)"""
    try:
        engine.dispose()
        if redis_client:
            redis_client.close()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Error closing database: {e}")


def _apply_post_schema_migrations() -> None:
    """
    Apply lightweight schema adjustments that need to run even if Alembic migrations
    have not yet been executed (e.g., new optional columns).
    """
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE ticket_history "
                    "ADD COLUMN IF NOT EXISTS requester_name VARCHAR(255)"
                )
            )
    except Exception as migration_error:
        logger.error("❌ Failed to apply post-schema migrations: %s", migration_error)
        raise
