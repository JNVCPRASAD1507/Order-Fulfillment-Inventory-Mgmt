from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy.orm import Session
from app.models import User, RefreshToken, Role
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.config import settings
from app.core.errors import DomainError

def register(db: Session, data):
    if db.query(User).filter(User.email==data.email).first(): raise DomainError("EMAIL_EXISTS","Email already registered",409)
    u=User(email=data.email,full_name=data.full_name,password_hash=hash_password(data.password),role=data.role)
    db.add(u); db.flush(); return u

def login(db: Session, data):
    u=db.query(User).filter(User.email==data.email).first()
    if not u or not verify_password(data.password,u.password_hash): raise DomainError("INVALID_CREDENTIALS","Invalid credentials",401)
    if not u.is_active: raise DomainError("USER_INACTIVE","Inactive users cannot authenticate",403)
    jti=uuid4().hex; rt=create_refresh_token(u.id,jti)
    db.add(RefreshToken(jti=jti,user_id=u.id,expires_at=datetime.now(timezone.utc)+timedelta(days=settings.refresh_token_expire_days)))
    return u, create_access_token(u.id), rt

def refresh(db: Session, token: str):
    try: payload=decode_token(token)
    except Exception: raise DomainError("INVALID_REFRESH_TOKEN","Invalid refresh token",401)
    if payload.get("type")!="refresh": raise DomainError("INVALID_REFRESH_TOKEN","Invalid refresh token",401)
    row=db.query(RefreshToken).filter(RefreshToken.jti==payload.get("jti")).first()
    if not row or row.revoked_at or row.expires_at < datetime.now(timezone.utc): raise DomainError("REFRESH_REVOKED","Refresh token revoked or expired",401)
    row.revoked_at=datetime.now(timezone.utc); jti=uuid4().hex; new=create_refresh_token(row.user_id,jti); db.add(RefreshToken(jti=jti,user_id=row.user_id,expires_at=datetime.now(timezone.utc)+timedelta(days=settings.refresh_token_expire_days)))
    return create_access_token(row.user_id), new
