# app/routes/todos.py
from fastapi import APIRouter, Query, Depends
from typing import Optional
from app.models.schemas import TodosWithPagination, TodoResponse, TodoCreate, TodoPatch, TodoPut, TodoStats
from app.models.user import UserResponse
from app.core.auth import get_active_user
from app.crud import todos as crud
from app.database.database import get_db_pool

router = APIRouter()

@router.get("/", response_model=TodosWithPagination)
async def get_todos(
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    current_user: UserResponse = Depends(get_active_user)
):
    """Get user's todos with pagination and filtering"""
    return await crud.list_todos(current_user.id, completed, search, page, page_size)

@router.get("/stats", response_model=TodoStats)
async def get_todo_stats(current_user: UserResponse = Depends(get_active_user)):
    """Get user's todo statistics"""
    pool = get_db_pool()
    async with pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_todos,
                COUNT(CASE WHEN completed = true THEN 1 END) as completed_todos,
                COUNT(CASE WHEN completed = false THEN 1 END) as pending_todos
            FROM todos 
            WHERE user_id = $1
        """, current_user.id)
        
        total = stats['total_todos'] or 0
        completed = stats['completed_todos'] or 0
        pending = stats['pending_todos'] or 0
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        return TodoStats(
            total_todos=total,
            completed_todos=completed,
            pending_todos=pending,
            completion_rate=round(completion_rate, 2)
        )

@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(
    todo_id: int,
    current_user: UserResponse = Depends(get_active_user)
):
    """Get a specific todo"""
    return await crud.get_todo(todo_id, current_user.id)

@router.post("/", response_model=TodoResponse, status_code=201)
async def create_todo(
    todo: TodoCreate,
    current_user: UserResponse = Depends(get_active_user)
):
    """Create a new todo"""
    return await crud.create_todo(todo, current_user.id)

@router.put("/{todo_id}", response_model=TodoResponse)
async def replace_todo(
    todo_id: int, 
    todo_put: TodoPut,
    current_user: UserResponse = Depends(get_active_user)
):
    """Replace a todo (PUT operation)"""
    return await crud.replace_todo(todo_id, todo_put, current_user.id)

@router.patch("/{todo_id}", response_model=TodoResponse)
async def update_todo(
    todo_id: int, 
    todo_update: TodoPatch,
    current_user: UserResponse = Depends(get_active_user)
):
    """Update a todo (PATCH operation)"""
    return await crud.update_todo(todo_id, todo_update, current_user.id)

@router.delete("/{todo_id}")
async def delete_todo(
    todo_id: int,
    current_user: UserResponse = Depends(get_active_user)
):
    """Delete a todo"""
    return await crud.delete_todo(todo_id, current_user.id)

@router.patch("/{todo_id}/toggle", response_model=TodoResponse)
async def toggle_todo_completion(
    todo_id: int,
    current_user: UserResponse = Depends(get_active_user)
):
    """Toggle todo completion status"""
    # First get the current todo
    current_todo = await crud.get_todo(todo_id, current_user.id)
    
    # Create patch with opposite completion status
    patch = TodoPatch(completed=not current_todo.completed)
    
    return await crud.update_todo(todo_id, patch, current_user.id)