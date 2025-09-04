# cli.py - Command line tools for the TODO API
import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.database.migrate import MigrationManager
from app.database.database import init_db, close_db
from app.crud.users import create_user
from app.models.user import UserCreate

async def run_migrations():
    """Run database migrations"""
    print("🚀 Running migrations...")
    manager = MigrationManager()
    await manager.migrate()

async def migration_status():
    """Check migration status"""
    print("📊 Checking migration status...")
    manager = MigrationManager()
    await manager.status()

async def create_test_user():
    """Create a test user for development"""
    print("👤 Creating test user...")
    
    await init_db()
    
    try:
        test_user = UserCreate(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        
        user = await create_user(test_user)
        print(f"✅ Test user created successfully!")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   ID: {user.id}")
        
    except Exception as e:
        print(f"❌ Failed to create test user: {e}")
    finally:
        await close_db()

async def reset_database():
    """Reset database - WARNING: This will delete all data!"""
    print("⚠️  WARNING: This will delete ALL data in the database!")
    confirm = input("Type 'YES' to confirm: ")
    
    if confirm != "YES":
        print("❌ Operation cancelled")
        return
    
    from app.database.database import DATABASE_URL
    import asyncpg
    
    print("🗑️  Resetting database...")
    
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Drop all tables
        await conn.execute("DROP TABLE IF EXISTS migrations CASCADE")
        await conn.execute("DROP TABLE IF EXISTS todos CASCADE")
        await conn.execute("DROP TABLE IF EXISTS users CASCADE")
        
        print("✅ Database reset complete")
        
    except Exception as e:
        print(f"❌ Failed to reset database: {e}")
    finally:
        await conn.close()

def show_help():
    """Show available commands"""
    print("""
🛠️  TODO API CLI Tools

Available commands:
  migrate          Run database migrations
  status           Check migration status
  create-test-user Create a test user for development
  reset-db         Reset database (WARNING: Deletes all data!)
  help            Show this help message

Usage:
  python cli.py <command>

Examples:
  python cli.py migrate
  python cli.py status
  python cli.py create-test-user
""")

async def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command == "migrate":
            await run_migrations()
        elif command == "status":
            await migration_status()
        elif command == "create-test-user":
            await create_test_user()
        elif command == "reset-db":
            await reset_database()
        elif command in ["help", "-h", "--help"]:
            show_help()
        else:
            print(f"❌ Unknown command: {command}")
            show_help()
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())