# app/routes/health.py
from fastapi import APIRouter
from app.database.database import fetch_db_version

router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Hello World"}

@router.get("/test-db")
async def test_database():
    try:
        version = await fetch_db_version()
        return {"status": "success", "database_version": version}
    except Exception as e:
        return {"status": "error", "message": str(e)}
