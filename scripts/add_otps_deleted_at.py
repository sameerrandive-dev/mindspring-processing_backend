import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import asyncio
from sqlalchemy import text
from app.infrastructure.database.session import engine


async def add_column():
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE otps ADD COLUMN IF NOT EXISTS deleted_at timestamp with time zone NULL;"
        ))
        print("ALTER TABLE executed: ensured otps.deleted_at exists")


if __name__ == '__main__':
    asyncio.run(add_column())
