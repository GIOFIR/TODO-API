# app/main.py
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database.database import init_db, close_db
from app.database.migrate import MigrationManager
from app.routes.todos import router as todos_router
from app.routes.health import router as health_router
from app.routes.auth import router as auth_router  
from app.exceptions.handlers import register_exception_handlers
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting application...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Run migrations
    try:
        migration_manager = MigrationManager()
        await migration_manager.migrate()
        logger.info("Migrations completed")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        # Don't fail the startup, just log the error
        # In production, you might want to fail here
    
    yield
    
    # Cleanup
    await close_db()
    logger.info("Application shutdown complete")

app = FastAPI(
    title="TODO API",
    description="A comprehensive TODO API with user authentication",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health_router, tags=["Health"])
app.include_router(auth_router, prefix="/auth", tags=["Authentication"]) 
app.include_router(todos_router, prefix="/todos", tags=["Todos"])

# Register exception handlers
register_exception_handlers(app)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to TODO API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/test-db"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)