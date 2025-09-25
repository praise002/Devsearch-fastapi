from datetime import datetime, timedelta

from redis import asyncio as aioredis

from src.config import Config

token_blocklist = aioredis.from_url(Config.REDIS_URL)


async def add_jti_to_blocklist(jti: str) -> None:
    await token_blocklist.set(
        name=jti,
        value="",
        # ex=REFRESH_TOKEN_EXPIRY
        ex=7776000,
    )


async def token_in_blacklist(jti: str) -> bool:
    jti = await token_blocklist.get(jti)
    return jti is not None

async def store_token(user_id: str, jti: str, expires_in: timedelta):
    pass

async def is_token_blacklisted(user_id: str, jti: str) -> bool:
    pass

def blacklist_all_user_tokens(user_id: str):
    pass