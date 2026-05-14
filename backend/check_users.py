import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.models.user import User
from app.core.config import settings

async def test():
    client = AsyncIOMotorClient(settings.MONGO_URL)
    await init_beanie(database=client[settings.MONGO_DB], document_models=[User])
    users = await User.find_all().to_list()
    print([(u.email, u.google_id) for u in users])

if __name__ == "__main__":
    asyncio.run(test())
