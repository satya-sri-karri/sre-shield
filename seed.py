import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import asyncio
from backend.database.connection import init_db
from backend.database.seed_data import seed_database
from backend.memory.hindsight_engine import hindsight

async def main():
    print("1. Initializing DB tables...")
    await init_db()
    print("2. Seeding database with historical incidents and runbooks...")
    await seed_database()
    print("3. Pre-warming Hindsight Agent Memory...")
    await hindsight.initialize()
    print("SUCCESS: Database and Hindsight Memory Engine fully seeded!")

if __name__ == "__main__":
    asyncio.run(main())
