from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from pwdlib import PasswordHash
from app.core.config import settings

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)

def create_token(subject: str, token_type: str, expires: timedelta) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": subject, "type": token_type, "iat": now, "exp": now + expires}, settings.secret_key, algorithm=settings.algorithm)

def create_access_token(user_id: int) -> str:
    return create_token(str(user_id), "access", timedelta(minutes=settings.access_token_expire_minutes))

def create_refresh_token(user_id: int, jti: str) -> str:
    return jwt.encode({"sub": str(user_id), "type": "refresh", "jti": jti, "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)}, settings.secret_key, algorithm=settings.algorithm)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
