# app/models/schemas.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="TODO title")
    description: Optional[str] = Field(None, max_length=1000, description="TODO description")

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str):
        if not v or v.isspace():
            raise ValueError('Title cannot be empty or just whitespace')
        v = v.strip()
        if '<' in v or '>' in v:
            raise ValueError('Title cannot contain HTML tags')
        return v

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]):
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if '<script' in v.lower() or '</script>' in v.lower():
                raise ValueError('Description cannot contain script tags')
        return v

class TodoPatch(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    completed: Optional[bool] = None

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: Optional[str]):
        if v is not None:
            if not v or v.isspace():
                raise ValueError('Title cannot be empty or just whitespace')
            v = v.strip()
            if '<' in v or '>' in v:
                raise ValueError('Title cannot contain HTML tags')
        return v

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]):
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if '<script' in v.lower() or '</script>' in v.lower():
                raise ValueError('Description cannot contain script tags')
        return v

class TodoPut(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    completed: bool = False

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str):
        if not v or v.isspace():
            raise ValueError('Title cannot be empty or just whitespace')
        v = v.strip()
        if '<' in v or '>' in v:
            raise ValueError('Title cannot contain HTML tags')
        return v

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]):
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if '<script' in v.lower() or '</script>' in v.lower():
                raise ValueError('Description cannot contain script tags')
        return v

class TodoResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    completed: bool
    created_at: datetime
    user_id: Optional[int] = None  # Optional for backward compatibility

    class Config:
        from_attributes = True

class TodosWithPagination(BaseModel):
    todos: list[TodoResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int

# Stats models for dashboard
class TodoStats(BaseModel):
    total_todos: int
    completed_todos: int
    pending_todos: int
    completion_rate: float

class UserTodoStats(BaseModel):
    user_id: int
    username: str
    stats: TodoStats