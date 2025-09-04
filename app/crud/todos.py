# app/crud/todos.py
import logging
from typing import Optional
from app.database.database import get_db_pool
from app.models.schemas import TodoResponse, TodosWithPagination, TodoCreate, TodoPatch, TodoPut
from app.exceptions.custom_exceptions import TodoNotFoundError, DatabaseError

logger = logging.getLogger(__name__)

async def get_todo_or_raise(conn, todo_id: int, user_id: Optional[int] = None):
    """Get todo or raise exception if not found"""
    try:
        if user_id is not None:
            # Check if todo belongs to user
            row = await conn.fetchrow(
                'SELECT * FROM todos WHERE id = $1 AND user_id = $2', 
                todo_id, user_id
            )
        else:
            # Get any todo (for admin use)
            row = await conn.fetchrow('SELECT * FROM todos WHERE id = $1', todo_id)
        
        if row is None:
            raise TodoNotFoundError(todo_id)
        return row
    except Exception as e:
        if isinstance(e, TodoNotFoundError):
            raise
        logger.error(f"Database error while fetching TODO {todo_id}: {str(e)}")
        raise DatabaseError(f"Failed to fetch TODO: {str(e)}")

async def list_todos(
    user_id: int,
    completed: Optional[bool],
    search: Optional[str],
    page: int,
    page_size: int
) -> TodosWithPagination:
    """List todos for a specific user with pagination"""
    pool = get_db_pool()

    async with pool.acquire() as conn:
        try:
            base_query = "SELECT * FROM todos WHERE user_id = $1"
            count_query = "SELECT COUNT(*) FROM todos WHERE user_id = $1"
            conditions = []
            values = [user_id]
            param_count = 2

            if completed is not None:
                conditions.append(f"completed = ${param_count}")
                values.append(completed)
                param_count += 1

            if search is not None:
                conditions.append(f"(title ILIKE ${param_count} OR description ILIKE ${param_count})")
                values.append(f"%{search}%")
                param_count += 1

            where_clause = f" AND {' AND '.join(conditions)}" if conditions else ""

            total_count = await conn.fetchval(count_query + where_clause, *values) or 0
            offset = (page - 1) * page_size
            total_pages = (total_count + page_size - 1) // page_size

            final_query = f"{base_query}{where_clause} ORDER BY created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
            pagination_values = values + [page_size, offset]

            rows = await conn.fetch(final_query, *pagination_values)
            todos = [TodoResponse(**row) for row in rows]

            return TodosWithPagination(
                todos=todos,
                total_count=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            )
        except Exception as e:
            logger.error(f"Database error while listing todos for user {user_id}: {str(e)}")
            raise DatabaseError(f"Failed to list todos: {str(e)}")

async def get_todo(todo_id: int, user_id: int) -> TodoResponse:
    """Get a specific todo for a user"""
    pool = get_db_pool()
    async with pool.acquire() as conn:
        row = await get_todo_or_raise(conn, todo_id, user_id)
        return TodoResponse(**row)

async def create_todo(todo: TodoCreate, user_id: int) -> TodoResponse:
    """Create a new todo for a user"""
    pool = get_db_pool()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow('''
                INSERT INTO todos (title, description, user_id)
                VALUES ($1, $2, $3)
                RETURNING id, title, description, completed, created_at, user_id
            ''', todo.title, todo.description, user_id)
            return TodoResponse(**row)
        except Exception as e:
            logger.error(f"Database error while creating todo for user {user_id}: {str(e)}")
            raise DatabaseError(f"Failed to create todo: {str(e)}")

async def replace_todo(todo_id: int, data: TodoPut, user_id: int) -> TodoResponse:
    """Replace a todo (PUT operation)"""
    pool = get_db_pool()
    async with pool.acquire() as conn:
        try:
            # Ensure todo exists and belongs to user
            await get_todo_or_raise(conn, todo_id, user_id)
            
            updated_row = await conn.fetchrow(
                '''
                UPDATE todos
                SET title = $1, description = $2, completed = $3
                WHERE id = $4 AND user_id = $5
                RETURNING id, title, description, completed, created_at, user_id
                ''',
                data.title, data.description, data.completed, todo_id, user_id
            )
            return TodoResponse(**updated_row)
        except Exception as e:
            if isinstance(e, TodoNotFoundError):
                raise
            logger.error(f"Database error while replacing todo {todo_id}: {str(e)}")
            raise DatabaseError(f"Failed to update todo: {str(e)}")

async def update_todo(todo_id: int, patch: TodoPatch, user_id: int) -> TodoResponse:
    """Update a todo (PATCH operation)"""
    pool = get_db_pool()
    async with pool.acquire() as conn:
        try:
            existing = await get_todo_or_raise(conn, todo_id, user_id)

            update_fields = []
            values = []
            param_count = 1

            if patch.title is not None:
                update_fields.append(f"title = ${param_count}")
                values.append(patch.title)
                param_count += 1

            if patch.description is not None:
                update_fields.append(f"description = ${param_count}")
                values.append(patch.description)
                param_count += 1

            if patch.completed is not None:
                update_fields.append(f"completed = ${param_count}")
                values.append(patch.completed)
                param_count += 1

            if not update_fields:
                return TodoResponse(**existing)

            values.extend([todo_id, user_id])
            query = f"""
                UPDATE todos
                SET {', '.join(update_fields)}
                WHERE id = ${param_count} AND user_id = ${param_count + 1}
                RETURNING id, title, description, completed, created_at, user_id
            """
            updated_row = await conn.fetchrow(query, *values)
            return TodoResponse(**updated_row)
        except Exception as e:
            if isinstance(e, TodoNotFoundError):
                raise
            logger.error(f"Database error while updating todo {todo_id}: {str(e)}")
            raise DatabaseError(f"Failed to update todo: {str(e)}")

async def delete_todo(todo_id: int, user_id: int) -> dict:
    """Delete a todo"""
    pool = get_db_pool()
    async with pool.acquire() as conn:
        try:
            await get_todo_or_raise(conn, todo_id, user_id)
            
            result = await conn.execute(
                'DELETE FROM todos WHERE id = $1 AND user_id = $2', 
                todo_id, user_id
            )
            
            if result == "DELETE 0":
                raise TodoNotFoundError(todo_id)
                
            logger.info(f"TODO {todo_id} deleted successfully by user {user_id}")
            return {"message": f"TODO {todo_id} deleted successfully"}
        except Exception as e:
            if isinstance(e, TodoNotFoundError):
                raise
            logger.error(f"Failed to delete TODO {todo_id}: {str(e)}")
            raise DatabaseError(f"Failed to delete TODO: {str(e)}")