import asyncio
import sys
import os
from pathlib import Path
from sqlalchemy import text

# Ensure the project root is on sys.path so `app` package imports work
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.infrastructure.database.session import engine, Base

# Import models to ensure they're registered on Base.metadata
from app.domain.models import (
    user,
    otp,
    refresh_token,
    notebook,
    source,
    chunk,
    conversation,
    message,
    quiz,
    study_guide,
    job,
    document,
    generation_history,
)


async def clear_database():
    # Collect table names from metadata and exclude Alembic migration table
    tables = [t for t in Base.metadata.tables.keys() if t != "alembic_version"]

    if not tables:
        print("No tables found to truncate.")
        return

    # Quote table names to be safe and create a single TRUNCATE statement
    quoted = ", ".join([f'"{t}"' for t in tables])

    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
        print("Truncated tables:", ", ".join(tables))


def main():
    # Safety: require explicit confirmation via CLI flag or env var
    confirm_flags = {"--yes", "-run"}
    env_confirm = os.getenv("CLEAR_DB_CONFIRM") == "1"

    if not env_confirm and not any(flag in sys.argv for flag in confirm_flags):
        print("This will TRUNCATE all database tables (except alembic_version) and reset identities.")
        print("Re-run with '--yes' or '-run', or set CLEAR_DB_CONFIRM=1 to confirm.")
        sys.exit(1)

    asyncio.run(clear_database())


if __name__ == "__main__":
    main()
