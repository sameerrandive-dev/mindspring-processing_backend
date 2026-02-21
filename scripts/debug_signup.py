import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import asyncio
import traceback

from app.infrastructure.database.session import AsyncSessionFactory
from app.infrastructure.container import ServiceContainer

# Ensure all model modules are imported so SQLAlchemy can resolve relationship names
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


async def main():
    async with AsyncSessionFactory() as session:
        container = ServiceContainer(db=session)
        auth = container.get_auth_service()
        try:
            user, otp = await auth.register_user(email='sameerrandive97@gmail.com', password='Passw0rd!')
            print('SUCCESS: created user id:', getattr(user, 'id', None))
            print('OTP:', otp)
        except Exception:
            print('EXCEPTION during register_user:')
            traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
