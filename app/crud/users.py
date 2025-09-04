import logging
from typing import Optional
from app.database.database import get_db_pool
from app.models.user import UserCreate, UserResponse
from app.core.security import get_password_hash, verify_password
from app.exceptions.custom_exceptions import DatabaseError

logger = logging.getLogger(__name__)

class UserAlreadyExistsError(Exception):
    def __init__(self, field: str, value: str):
        self.field = field
        self.value = value
        super().__init__(f"User with {field} '{value}' already exists")

class UserNotFoundError(Exception):
    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"User '{identifier}' not found")

async def create_user(user: UserCreate) -> UserResponse:
    """Create a new user"""
    pool = get_db_pool()
    assert pool is not None, "DB pool is not initialized"
    
    async with pool.acquire() as conn:
        try:
            # Check if user exists with same username or email
            existing_user = await conn.fetchrow(
                'SELECT username, email FROM users WHERE username = $1 OR email = $2',
                user.username, user.email
            )
            
            if existing_user:
                if existing_user['username'] == user.username:
                    raise UserAlreadyExistsError("username", user.username)
                else:
                    raise UserAlreadyExistsError("email", user.email)
            
            # Hash the password
            hashed_password = get_password_hash(user.password)
            
            # Create the user
            row = await conn.fetchrow('''
                INSERT INTO users (username, email, hashed_password)
                VALUES ($1, $2, $3)
                RETURNING id, username, email, is_active, created_at
            ''', user.username, user.email, hashed_password)
            
            logger.info(f"User {user.username} created successfully")
            return UserResponse(**row)
            
        except Exception as e:
            if isinstance(e, UserAlreadyExistsError):
                raise
            logger.error(f"Database error while creating user {user.username}: {str(e)}")
            raise DatabaseError(f"Failed to create user: {str(e)}")

async def get_user_by_username(username: str) -> Optional[dict]:
    """Get user by username - includes hashed password for authentication"""
    pool = get_db_pool()
    assert pool is not None, "DB pool is not initialized"
    
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                'SELECT * FROM users WHERE username = $1 AND is_active = TRUE',
                username
            )
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Database error while fetching user {username}: {str(e)}")
            raise DatabaseError(f"Failed to fetch user: {str(e)}")

async def authenticate_user(username: str, password: str) -> Optional[UserResponse]:
    """Authenticate user and return user details"""
    user_data = await get_user_by_username(username)
    if not user_data:
        return None
    
    # Check password
    if not verify_password(password, user_data['hashed_password']):
        return None
    
    # Return user without hashed password
    return UserResponse(
        id=user_data['id'],
        username=user_data['username'],
        email=user_data['email'],
        is_active=user_data['is_active'],
        created_at=user_data['created_at']
    )

async def get_user_by_id(user_id: int) -> Optional[UserResponse]:
    """Get user by ID"""
    pool = get_db_pool()
    assert pool is not None, "DB pool is not initialized"
    
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                'SELECT id, username, email, is_active, created_at FROM users WHERE id = $1 AND is_active = TRUE',
                user_id
            )
            return UserResponse(**row) if row else None
        except Exception as e:
            logger.error(f"Database error while fetching user ID {user_id}: {str(e)}")
            raise DatabaseError(f"Failed to fetch user: {str(e)}")