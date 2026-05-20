from passlib.context import CryptContext
from datetime import timedelta, datetime
import jwt
from src.config import Config
import uuid
import logging
from itsdangerous import URLSafeTimedSerializer

passwd_context = CryptContext(schemes=["bcrypt"])

ACCES_TOKEN_EXPIRY = 3600

token_serializer = URLSafeTimedSerializer(
    secret_key=Config.JWT_SECRET_KEY, salt="email-verification"
)

# -----


def generate_passwwd_hash(password: str) -> str:
    hash = passwd_context.hash(password)
    return hash


def verify_password(password: str, hash: str) -> bool:
    return passwd_context.verify(password, hash)


# ----


def create_acces_token(user_data: dict, expiry: timedelta = None, refresh=False):
    payload = {}
    payload["user"] = user_data
    payload["exp"] = datetime.now() + (
        expiry if expiry is not None else timedelta(seconds=ACCES_TOKEN_EXPIRY)
    )
    payload["jti"] = str(uuid.uuid4())
    payload["refresh"] = refresh
    token = jwt.encode(
        payload=payload, key=Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM
    )

    return token


def create_refresh_token(user_data: dict, expiry: timedelta = None, refresh=True):
    payload = {}
    payload["user"] = user_data
    payload["exp"] = datetime.now() + (
        expiry if expiry is not None else timedelta(seconds=ACCES_TOKEN_EXPIRY)
    )
    payload["jti"] = str(uuid.uuid4())
    payload["refresh"] = refresh
    token = jwt.encode(
        payload=payload, key=Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM
    )

    return token


def decode_token(token: str) -> dict:

    try:
        token_data = jwt.decode(
            jwt=token, key=Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM]
        )
        return token_data
    except jwt.PyJWTError as e:
        logging.exception(e)
        return None


# ---


def create_url_safe_token(data: dict):
    token = token_serializer.dumps(data)
    return token


def decode_url_safe_token(token: str):
    try:
        token_data = token_serializer.loads(token)
        return token_data
    except Exception as e:
        logging.error(e)
