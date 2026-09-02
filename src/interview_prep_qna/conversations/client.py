from functools import lru_cache

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from interview_prep_qna.core.config import get_settings


@lru_cache(maxsize=1)
def get_mongo_client() -> AsyncMongoClient:
    settings = get_settings()
    return AsyncMongoClient(
        settings.mongodb_uri.get_secret_value(),
        serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
    )


def get_conversation_database() -> AsyncDatabase:
    settings = get_settings()
    return get_mongo_client()[settings.mongodb_database]


async def close_mongo_client() -> None:
    if get_mongo_client.cache_info().currsize:
        await get_mongo_client().close()
        get_mongo_client.cache_clear()
