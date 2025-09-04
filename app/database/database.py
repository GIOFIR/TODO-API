# app/database/database.py
import asyncpg
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://postgres:8652364@localhost:5432/todoApp"

db_pool: Optional[asyncpg.Pool] = None

async def init_db() -> None:
    """Initialize database connection pool"""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
        logger.info("Database pool created successfully")
    except Exception as e:
        logger.error(f"Failed to create database pool: {e}")
        raise

async def close_db() -> None:
    """Close database connection pool"""
    global db_pool
    if db_pool is not None:
        await db_pool.close()
        db_pool = None
        logger.info("Database pool closed")

def get_db_pool() -> asyncpg.Pool:
    """Get the database pool"""
    if db_pool is None:
        raise RuntimeError("Database pool is not initialized. Call init_db() first.")
    return db_pool

async def fetch_db_version() -> str:
    """Fetch database version for check"""
    pool = get_db_pool()
    async with pool.acquire() as conn:
        try:
            return await conn.fetchval("SELECT version()")
        except Exception as e:
            logger.error(f"Failed to fetch database version: {e}")
            raise


# async def create_tables() -> None:
#     assert db_pool is not None, "DB pool is not initialized"
#     async with db_pool.acquire() as conn:
#         await conn.execute('''
#             CREATE TABLE IF NOT EXISTS todos (
#                 id SERIAL PRIMARY KEY,
#                 title VARCHAR(200) NOT NULL,
#                 description TEXT,
#                 completed BOOLEAN DEFAULT FALSE,
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#             )
#         ''')