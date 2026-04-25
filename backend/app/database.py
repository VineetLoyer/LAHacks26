import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import MONGODB_URI, DB_NAME

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    client = AsyncIOMotorClient(MONGODB_URI, tlsCAFile=certifi.where())
    db = client[DB_NAME]
    # Create indexes
    await db.sessions.create_index("code", unique=True)
    await db.checkins.create_index("session_id")
    await db.questions.create_index("session_id")
    await db.clusters.create_index("session_id")
    await db.verifications.create_index([("session_id", 1), ("nullifier_hash", 1)], unique=True)
    print("Connected to MongoDB")


async def close_db():
    global client
    if client:
        client.close()
        print("Disconnected from MongoDB")


def get_db():
    return db
