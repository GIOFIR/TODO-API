from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional
import uvicorn
import asyncpg
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = "postgresql://postgres:8652364@localhost:5432/todoApp"

# Lifespan event handler for database connection
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create connection pool
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    print("\t\tDatabase pool created")
    
    # Create tables
    await create_tables()
    
    yield
    
    # Shutdown: Close connection pool
    await db_pool.close()
    print("\t\tDatabase pool closed")
    
# Database table creation
async def create_tables():
    async with db_pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id SERIAL PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                completed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("\t\tTables created successfully")

# Pydantic models for request
class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="TODO title")
    description: Optional[str] = Field(None, max_length=1000, description="TODO description")
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if not v or v.isspace():
            raise ValueError('Title cannot be empty or just whitespace')
        
        # Remove extra whitespace
        v = v.strip()
        
        # Check for basic HTML/script injection
        if '<' in v or '>' in v:
            raise ValueError('Title cannot contain HTML tags')
            
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if v is not None:
            v = v.strip()
            # Allow empty description after strip
            if not v:
                return None
                
            # Check for basic HTML/script injection  
            if '<script' in v.lower() or '</script>' in v.lower():
                raise ValueError('Description cannot contain script tags')
                
        return v

# Pydantic model for response
class TodoResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    completed: bool
    created_at: datetime

class TodosWithPagination(BaseModel):
    todos: list[TodoResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int

# Pydantic model Patch
class TodoPatch(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000) 
    completed: Optional[bool] = None
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if v is not None:
            if not v or v.isspace():
                raise ValueError('Title cannot be empty or just whitespace')
            
            v = v.strip()
            
            if '<' in v or '>' in v:
                raise ValueError('Title cannot contain HTML tags')
                
        return v
    
    @field_validator('description')
    @classmethod 
    def validate_description(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                return None
                
            if '<script' in v.lower() or '</script>' in v.lower():
                raise ValueError('Description cannot contain script tags')
                
        return v

# Pydantic model Put
class TodoPut(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    completed: bool = False
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if not v or v.isspace():
            raise ValueError('Title cannot be empty or just whitespace')
        
        v = v.strip()
        
        if '<' in v or '>' in v:
            raise ValueError('Title cannot contain HTML tags')
            
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                return None
                
            if '<script' in v.lower() or '</script>' in v.lower():
                raise ValueError('Description cannot contain script tags')
                
        return v


# Custom exception classes
class TodoNotFoundError(Exception):
    def __init__(self, todo_id: int):
        self.todo_id = todo_id
        super().__init__(f"TODO with id {todo_id} not found")

class DatabaseError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# Create FastAPI application
app = FastAPI(title="TODO API", version="1.0.0", lifespan=lifespan)

# Global exception handlers
@app.exception_handler(TodoNotFoundError)
async def todo_not_found_handler(request: Request, exc: TodoNotFoundError):
    logger.warning(f"TODO not found: {exc.todo_id}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "TODO Not Found",
            "message": f"TODO with id {exc.todo_id} does not exist"
        }
    )

@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    logger.error(f"Database error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Database Error",
            "message": "An internal database error occurred"
        }
    )

# Enhanced helper function to get TODO with better error handling
async def get_todo_or_raise(conn, todo_id: int):
    """Get TODO by ID or raise TodoNotFoundError"""
    try:
        row = await conn.fetchrow('SELECT * FROM todos WHERE id = $1', todo_id)
        if row is None:
            raise TodoNotFoundError(todo_id)
        return row
    except Exception as e:
        if isinstance(e, TodoNotFoundError):
            raise
        logger.error(f"Database error while fetching TODO {todo_id}: {str(e)}")
        raise DatabaseError(f"Failed to fetch TODO: {str(e)}")
    
# checks connection to database
@app.get("/test-db")
async def test_database():
    try:
        # Create a simple connection to test
        conn = await asyncpg.connect(DATABASE_URL)
        # Run a simple query
        result = await conn.fetchval("SELECT version()")
        # Close the connection  
        await conn.close()
        return {"status": "success", "database_version": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
# Simple root endpoint
@app.get("/")
def read_root():
    return {"message": "Hello World"}

# Get all TODOs
@app.get("/todos", response_model=TodosWithPagination)
async def get_todos(
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page")
):
    async with db_pool.acquire() as conn:
        # Build the base query and count query
        base_query = "SELECT * FROM todos"
        count_query = "SELECT COUNT(*) FROM todos"
        conditions = []
        values = []
        param_count = 1
        
        # Add completion filter
        if completed is not None:
            conditions.append(f"completed = ${param_count}")
            values.append(completed)
            param_count += 1
        
        # Add search filter
        if search is not None:
            conditions.append(f"(title ILIKE ${param_count} OR description ILIKE ${param_count})")
            values.append(f"%{search}%")
            param_count += 1
        
        # Add WHERE clause if we have conditions
        where_clause = ""
        if conditions:
            where_clause = f" WHERE {' AND '.join(conditions)}"
        
        # Get total count
        count_result = await conn.fetchval(count_query + where_clause, *values)
        total_count = count_result or 0
        
        # Calculate pagination
        offset = (page - 1) * page_size
        total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
        
        # Build final query with pagination
        final_query = f"{base_query}{where_clause} ORDER BY created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
        pagination_values = values + [page_size, offset]
        
        # Execute query
        rows = await conn.fetch(final_query, *pagination_values)
        todos = [TodoResponse(**row) for row in rows]
        
        return TodosWithPagination(
            todos=todos,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
# Get a specific TODO by ID
@app.get("/todos/{todo_id}", response_model=TodoResponse)
async def get_todo(todo_id: int):
    async with db_pool.acquire() as conn:
        row = await get_todo_or_raise(conn, todo_id)
        return TodoResponse(**row)
    
# Create a new TODO
@app.post("/todos", response_model=TodoResponse)
async def create_todo(todo: TodoCreate):
    async with db_pool.acquire() as conn:
        # Insert the new TODO and return it
        row = await conn.fetchrow('''
            INSERT INTO todos (title, description) 
            VALUES ($1, $2) 
            RETURNING id, title, description, completed, created_at
        ''', todo.title, todo.description)
        
        return TodoResponse(**row)

# put endpoint
@app.put("/todos/{todo_id}", response_model=TodoResponse)
async def replace_todo(todo_id: int, todo_put: TodoPut):
    async with db_pool.acquire() as conn:
        # Check if the TODO exists
        existing_todo = await conn.fetchrow('SELECT * FROM todos WHERE id = $1', todo_id)
        if existing_todo is None:
            raise HTTPException(status_code=404, detail="TODO not found")
        
        # Replace ALL fields
        updated_row = await conn.fetchrow('''
            UPDATE todos 
            SET title = $1, description = $2, completed = $3
            WHERE id = $4
            RETURNING id, title, description, completed, created_at
        ''', todo_put.title, todo_put.description, todo_put.completed, todo_id)
        
        return TodoResponse(**updated_row)
    
# Update the existing TODO
@app.patch("/todos/{todo_id}", response_model=TodoResponse)
async def update_todo(todo_id: int, todo_update: TodoPatch):
    async with db_pool.acquire() as conn:
        # check if the TODO exists
        existing_todo = await conn.fetchrow('SELECT * FROM todos WHERE id = $1', todo_id)
        if existing_todo is None:
            raise HTTPException(status_code=404, detail="TODO not found")
        
        # Build the update query dynamically based on provided fields
        update_fields = []
        values = []
        param_count = 1
        
        if todo_update.title is not None:
            update_fields.append(f"title = ${param_count}")
            values.append(todo_update.title)
            param_count += 1
            
        if todo_update.description is not None:
            update_fields.append(f"description = ${param_count}")
            values.append(todo_update.description)
            param_count += 1
            
        if todo_update.completed is not None:
            update_fields.append(f"completed = ${param_count}")
            values.append(todo_update.completed)
            param_count += 1
        
        # If no fields to update, return the existing todo
        if not update_fields:
            return TodoResponse(**existing_todo)
        
        # Add the todo_id as the last parameter
        values.append(todo_id)
        
        # Execute the update
        query = f"""
            UPDATE todos 
            SET {', '.join(update_fields)} 
            WHERE id = ${param_count}
            RETURNING id, title, description, completed, created_at
        """
        
        updated_row = await conn.fetchrow(query, *values)
        return TodoResponse(**updated_row)

# Delete endpoint
@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int):
    async with db_pool.acquire() as conn:
        # This will automatically raise TodoNotFoundError if not found
        await get_todo_or_raise(conn, todo_id)
        
        try:
            await conn.execute('DELETE FROM todos WHERE id = $1', todo_id)
            logger.info(f"TODO {todo_id} deleted successfully")
            return {"message": f"TODO {todo_id} deleted successfully"}
        except Exception as e:
            logger.error(f"Failed to delete TODO {todo_id}: {str(e)}")
            raise DatabaseError(f"Failed to delete TODO: {str(e)}")
    
# Run the server
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
