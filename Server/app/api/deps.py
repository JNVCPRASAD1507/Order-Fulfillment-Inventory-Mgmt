from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

# from app.models.entities import WarehouseUser
from app.db.session import get_db
from app.core.security import decode_token
from app.core.errors import DomainError
from app.models import User, Role , WarehouseUser


# Swagger/OpenAPI authentication scheme
bearer_scheme = HTTPBearer(auto_error=False)


def db():
    return Depends(get_db)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise DomainError(
            "UNAUTHORIZED",
            "Authentication required",
            401,
        )

    token = credentials.credentials

    try:
        payload = decode_token(token)
    except Exception:
        raise DomainError(
            "UNAUTHORIZED",
            "Invalid or expired token",
            401,
        )

    if payload.get("type") != "access":
        raise DomainError(
            "UNAUTHORIZED",
            "Invalid access token",
            401,
        )

    user_id = payload.get("sub")

    if not user_id:
        raise DomainError(
            "UNAUTHORIZED",
            "Invalid access token",
            401,
        )

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise DomainError(
            "UNAUTHORIZED",
            "Invalid access token",
            401,
        )

    user = db.get(User, user_id)

    if not user or not user.is_active:
        raise DomainError(
            "UNAUTHORIZED",
            "User is inactive or missing",
            401,
        )

    return user


def roles(*allowed):
    def dep(user=Depends(current_user)):

        if user.role not in allowed:
            raise DomainError(
                "FORBIDDEN",
                "Insufficient role",
                403,
            )

        return user

    return dep


def idem_header(
    x_idempotency_key: str | None = Header(default=None),
):
    return x_idempotency_key


def warehouse_access(db, user, warehouse_id):

    if user.role == Role.ADMIN:
        return True

    return bool(
        db.query(WarehouseUser)
        .filter_by(
            user_id=user.id,
            warehouse_id=warehouse_id,
        )
        .first()
    )
    
    