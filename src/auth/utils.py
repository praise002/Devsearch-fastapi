import logging
import random
import uuid
from datetime import datetime, timedelta

import jwt
from passlib.context import CryptContext
from sqlmodel import select

from src.config import Config
from src.db.models import Otp

pwd_context = CryptContext(schemes=["bcrypt"])
ACCESS_TOKEN = Config.ACCESS_TOKEN_EXPIRY


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_data: dict, expiry: timedelta = None, refresh: bool = False
):
    payload = {}

    payload["user"] = user_data
    # prod
    # payload['exp'] = datetime.now() + (expiry if expiry is not None else timedelta(seconds=ACCESS_TOKEN_EXPIRY))
    # dev
    payload["exp"] = datetime.now() + (
        expiry if expiry is not None else timedelta(days=1)
    )
    payload["jti"] = str(uuid.uuid4())
    payload["refresh"] = refresh

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


def invalidate_previous_otps(user, session):
    statement = select(Otp).where(Otp.user_id == user.id)
    results = session.exec(statement).all()
    for otp in results:
        session.delete(otp)
    session.commit()


def generate_otp(user, session):
    otp_value = random.randint(100000, 999999)
    # Save the OTP to the Otp model
    otp = Otp(user_id=user.id, otp=otp_value)
    session.add(otp)
    session.commit()
    session.refresh(otp)
    return otp_value
