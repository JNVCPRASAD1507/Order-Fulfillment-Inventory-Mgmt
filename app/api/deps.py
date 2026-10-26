from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode_token
from app.core.errors import DomainError
from app.models import User, Role, IdempotencyKey

def db(): return Depends(get_db)

def current_user(request: Request, db: Session=Depends(get_db)):
    auth=request.headers.get("Authorization","")
    if not auth.startswith("Bearer "): raise DomainError("UNAUTHORIZED","Authentication required",401)
    try: payload=decode_token(auth.split(" ",1)[1])
    except Exception: raise DomainError("UNAUTHORIZED","Invalid or expired token",401)
    if payload.get("type")!="access": raise DomainError("UNAUTHORIZED","Invalid access token",401)
    u=db.get(User,int(payload["sub"]))
    if not u or not u.is_active: raise DomainError("UNAUTHORIZED","User is inactive or missing",401)
    return u

def roles(*allowed):
    def dep(user=Depends(current_user)):
        if user.role not in allowed: raise DomainError("FORBIDDEN","Insufficient role",403)
        return user
    return dep

def idem_header(x_idempotency_key: str|None=Header(default=None)): return x_idempotency_key

def warehouse_access(db,user,warehouse_id):
    from app.models import WarehouseUser, Role
    if user.role==Role.ADMIN: return True
    return bool(db.query(WarehouseUser).filter_by(user_id=user.id,warehouse_id=warehouse_id).first())
