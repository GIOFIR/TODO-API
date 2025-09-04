import asyncio
import asyncpg

async def test_connection():
    try:
        conn = await asyncpg.connect(
            host="localhost",
            database="todoApp",
            user="postgres",
            password="8652364",  
            port=5432
        )
        
        print("✅ successful connection")
        
        # version checks
        version = await conn.fetchval("SELECT version();")
        print(f"\n🐘 PostgreSQL Version: {version}\n")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ connection error: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())