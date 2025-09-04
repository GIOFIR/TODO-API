# app/exceptions/handlers.py
import logging
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from app.exceptions.custom_exceptions import TodoNotFoundError, DatabaseError

logger = logging.getLogger(__name__)

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(TodoNotFoundError)
    async def todo_not_found_handler(request, exc: TodoNotFoundError):
        logger.warning(f"TODO not found: {exc.todo_id}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "TODO Not Found",
                     "message": f"TODO with id {exc.todo_id} does not exist"}
        )

    @app.exception_handler(DatabaseError)
    async def database_error_handler(request, exc: DatabaseError):
        logger.error(f"Database error: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Database Error",
                     "message": "An internal database error occurred"}
        )
