import logging
import random
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from sqlmodel import select

from src.config import Config
from src.db.models import Otp

pwd_context = CryptContext(schemes=["bcrypt"])
ACCESS_TOKEN = Config.ACCESS_TOKEN_EXPIRY
ACCESS_TOKEN = Config.REFRESH_TOKEN_EXPIRY


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_data: dict, expiry: timedelta = None):
    if expiry is None:
        # expiry = timedelta(seconds=ACCESS_TOKEN_EXPIRY)
        expiry = timedelta(days=1)

    now = datetime.now(timezone.utc)

    payload = {
        "token_type": "access",
        "exp": now + expiry,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "user": user_data,
    }

    token = jwt.encode(
        payload=payload, key=Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM
    )

    return token


def create_refresh_token(user_data: dict, expiry: timedelta = None):
    if expiry is None:
        # expiry = timedelta(seconds=REFRESH_TOKEN_EXPIRY)
        expiry = timedelta(days=90)

    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())

    payload = {
        "token_type": "refresh",
        "exp": now + expiry,
        "iat": now,  # issued at in unix timestamp
        "jti": jti,
        "user": user_data,
    }  # user_id, full_name

    token = jwt.encode(
        payload=payload, key=Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM
    )

    return token


def decode_token(token: str) -> dict:
    try:
        token_data = jwt.decode(
            jwt=token, key=Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM]
        )
        return token_data
    except jwt.PyJWTError as e:
        logging.exception(e)
        return None


async def invalidate_previous_otps(user, session):
    statement = select(Otp).where(Otp.user_id == user.id)
    results = await session.exec(statement)
    for otp in results.all():
        await session.delete(otp)
    await session.commit()


async def generate_otp(user, session):
    otp_value = random.randint(100000, 999999)
    # Save the OTP to the Otp model
    otp = Otp(user_id=user.id, otp=otp_value)
    session.add(otp)
    await session.commit()
    await session.refresh(otp)
    return otp.otp
