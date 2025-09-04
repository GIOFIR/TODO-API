import asyncio
import os
from pathlib import Path
import asyncpg
from typing import List

# Database connection settings
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:8652364@localhost:5432/todoApp"
)

class MigrationManager:
    def __init__(self, database_url: str = DATABASE_URL):
        self.database_url = database_url
        self.migrations_dir = Path(__file__).parent / "migrations"
    
    async def create_migrations_table(self, conn):
        """Create migrations tracking table"""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) UNIQUE NOT NULL,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    async def get_executed_migrations(self, conn) -> List[str]:
        """Get list of already executed migrations"""
        rows = await conn.fetch("SELECT filename FROM migrations ORDER BY id")
        return [row['filename'] for row in rows]
    
    async def get_pending_migrations(self, conn) -> List[Path]:
        """Get list of migrations that haven't been executed yet"""
        executed = await self.get_executed_migrations(conn)
        all_migrations = sorted(self.migrations_dir.glob("*.sql"))
        
        pending = []
        for migration_file in all_migrations:
            if migration_file.name not in executed:
                pending.append(migration_file)
        
        return pending
    
    async def run_migration(self, conn, migration_file: Path):
        """Execute a single migration"""
        print(f"Running migration: {migration_file.name}")
        
        # Read file content
        sql_content = migration_file.read_text(encoding='utf-8')
        
        # Execute SQL
        await conn.execute(sql_content)
        
        # Mark migration as executed
        await conn.execute(
            "INSERT INTO migrations (filename) VALUES ($1)",
            migration_file.name
        )
        
        print(f"✅ Migration {migration_file.name} completed successfully")
    
    async def migrate(self):
        """Execute all pending migrations"""
        conn = await asyncpg.connect(self.database_url)
        
        try:
            # Create migrations table
            await self.create_migrations_table(conn)
            
            # Get pending migrations
            pending_migrations = await self.get_pending_migrations(conn)
            
            if not pending_migrations:
                print("✅ No pending migrations")
                return
            
            print(f"Found {len(pending_migrations)} pending migrations")
            
            # Execute each migration separately
            for migration_file in pending_migrations:
                await self.run_migration(conn, migration_file)
            
            print("🎉 All migrations completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise
        finally:
            await conn.close()
    
    async def status(self):
        """Display migrations status"""
        conn = await asyncpg.connect(self.database_url)
        
        try:
            await self.create_migrations_table(conn)
            
            executed = await self.get_executed_migrations(conn)
            pending = await self.get_pending_migrations(conn)
            
            print("📊 Migration Status:")
            print(f"✅ Executed: {len(executed)}")
            for migration in executed:
                print(f"   - {migration}")
            
            print(f"⏳ Pending: {len(pending)}")
            for migration in pending:
                print(f"   - {migration.name}")
                
        finally:
            await conn.close()

# Helper functions for terminal usage
async def migrate():
    """Run migrations"""
    manager = MigrationManager()
    await manager.migrate()

async def migration_status():
    """Check migrations status"""
    manager = MigrationManager()
    await manager.status()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "migrate":
            asyncio.run(migrate())
        elif command == "status":
            asyncio.run(migration_status())
        else:
            print("Usage: python migrate.py [migrate|status]")
    else:
        asyncio.run(migrate())