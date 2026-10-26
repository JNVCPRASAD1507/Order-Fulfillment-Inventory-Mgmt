from fastapi import APIRouter, Depends, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.db.session import get_db
from app.models import *
from app.schemas.auth import *
from app.schemas.domain import *
from app.schemas.common import Message
from app.api.deps import current_user, roles, warehouse_access
from app.core.errors import DomainError, NotFoundError, ForbiddenError
from app.services import auth as auth_svc
from app.services import inventory as inv_svc
from app.services import orders as order_svc
from app.services.common import audit, notify
from datetime import datetime
from uuid import uuid4

router = APIRouter(tags=["Api Endpoints Routes"] )


def commit(db):
    db.commit()


@router.post("/auth/register", response_model=UserOut)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    u = auth_svc.register(db, data)
    audit(db, u.id, "Registration", "user", u.id)
    commit(db)
    return u


@router.post("/auth/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    u, at, rt = auth_svc.login(db, data)
    audit(db, u.id, "Login", "user", u.id)
    commit(db)
    return TokenOut(access_token=at, refresh_token=rt)


@router.post("/auth/refresh", response_model=TokenOut)
def refresh(data: RefreshIn, db: Session = Depends(get_db)):
    at, rt = auth_svc.refresh(db, data.refresh_token)
    commit(db)
    return TokenOut(access_token=at, refresh_token=rt)


@router.post("/auth/logout", response_model=Message)
def logout(data: RefreshIn, db: Session = Depends(get_db), user=Depends(current_user)):
    try:
        p = auth_svc.decode_token(data.refresh_token)
    except:
        p = {}
    if p.get("jti"):
        row = db.query(RefreshToken).filter_by(jti=p["jti"], user_id=user.id).first()
        if row:
            row.revoked_at = datetime.utcnow()
            audit(db, user.id, "Logout", "user", user.id)
            commit(db)
    return Message(message="Logged out")


@router.get("/auth/me", response_model=UserOut)
def me(user=Depends(current_user)):
    return user


@router.post("/auth/change-password", response_model=Message)
def change_password(
    data: ChangePasswordIn, db: Session = Depends(get_db), user=Depends(current_user)
):
    if not auth_svc.verify_password(data.current_password, user.password_hash):
        raise DomainError("INVALID_PASSWORD", "Current password is incorrect", 400)
    user.password_hash = auth_svc.hash_password(data.new_password)
    audit(db, user.id, "Password Changed", "user", user.id)
    commit(db)
    return Message(message="Password changed")


@router.post("/products", response_model=ProductOut)
def create_product(
    data: ProductIn, db=Depends(get_db), user=Depends(roles(Role.ADMIN))
):
    if db.query(Product).filter_by(sku=data.sku).first():
        raise DomainError("DUPLICATE_SKU", "SKU already exists", 409)
    p = Product(**data.model_dump())
    db.add(p)
    db.flush()
    audit(db, user.id, "Product Created", "product", p.id)
    commit(db)
    return p


@router.get("/products", response_model=list[ProductOut])
def list_products(
    db=Depends(get_db), status: Status | None = None, skip: int = 0, limit: int = 50
):
    q = db.query(Product)
    q = q.filter(Product.status == status) if status else q
    return q.offset(skip).limit(min(limit, 100)).all()


@router.get("/products/{id}", response_model=ProductOut)
def get_product(id: int, db=Depends(get_db)):
    p = db.get(Product, id)
    if not p:
        raise NotFoundError("Product not found")
    return p


@router.patch("/products/{id}", response_model=ProductOut)
def update_product(
    id: int, data: ProductIn, db=Depends(get_db), user=Depends(roles(Role.ADMIN))
):
    p = db.get(Product, id)
    if not p:
        raise NotFoundError("Product not found")
    for k, v in data.model_dump().items():
        setattr(p, k, v)
    audit(db, user.id, "Product Updated", "product", id)
    commit(db)
    return p


@router.post("/products/{id}/activate", response_model=ProductOut)
def activate_product(id: int, db=Depends(get_db), user=Depends(roles(Role.ADMIN))):
    p = db.get(Product, id)
    p.status = Status.ACTIVE
    commit(db)
    return p


@router.post("/products/{id}/deactivate", response_model=ProductOut)
def deactivate_product(id: int, db=Depends(get_db), user=Depends(roles(Role.ADMIN))):
    p = db.get(Product, id)
    p.status = Status.INACTIVE
    commit(db)
    return p


@router.post("/warehouses", response_model=WarehouseOut)
def create_warehouse(
    data: WarehouseIn, db=Depends(get_db), user=Depends(roles(Role.ADMIN))
):
    w = Warehouse(**data.model_dump())
    db.add(w)
    commit(db)
    return w


@router.get("/warehouses", response_model=list[WarehouseOut])
def list_warehouses(db=Depends(get_db), user=Depends(current_user)):
    return db.query(Warehouse).all()


@router.get("/warehouses/{id}", response_model=WarehouseOut)
def get_warehouse(id: int, db=Depends(get_db), user=Depends(current_user)):
    w = db.get(Warehouse, id)
    if not w:
        raise NotFoundError("Warehouse not found")
    if not warehouse_access(db, user, id) and user.role != Role.ADMIN:
        raise ForbiddenError("Warehouse access denied")
    return w


@router.patch("/warehouses/{id}", response_model=WarehouseOut)
def update_warehouse(
    id: int, data: WarehouseIn, db=Depends(get_db), user=Depends(roles(Role.ADMIN))
):
    w = db.get(Warehouse, id)
    if not w:
        raise NotFoundError("Warehouse not found")
    for k, v in data.model_dump().items():
        setattr(w, k, v)
    commit(db)
    return w


@router.post("/warehouses/{id}/activate", response_model=WarehouseOut)
def activate_wh(id: int, db=Depends(get_db), user=Depends(roles(Role.ADMIN))):
    w = db.get(Warehouse, id)
    w.status = Status.ACTIVE
    commit(db)
    return w


@router.post("/warehouses/{id}/deactivate", response_model=WarehouseOut)
def deactivate_wh(id: int, db=Depends(get_db), user=Depends(roles(Role.ADMIN))):
    w = db.get(Warehouse, id)
    w.status = Status.INACTIVE
    commit(db)
    return w


@router.post("/warehouses/{id}/users/{user_id}", response_model=Message)
def assign_wh_user(
    id: int,
    user_id: int,
    db=Depends(get_db),
    user=Depends(roles(Role.ADMIN, Role.WAREHOUSE_MANAGER)),
):
    if user.role == Role.WAREHOUSE_MANAGER and not warehouse_access(db, user, id):
        raise ForbiddenError("Warehouse access denied")
    if not db.query(WarehouseUser).filter_by(warehouse_id=id, user_id=user_id).first():
        db.add(WarehouseUser(warehouse_id=id, user_id=user_id))
        commit(db)
    return Message(message="User assigned to warehouse")


@router.get("/inventory", response_model=list[InventoryOut])
def inventory(
    db=Depends(get_db),
    user=Depends(current_user),
    warehouse_id: int | None = None,
    product_id: int | None = None,
    low_stock: bool = False,
    out_of_stock: bool = False,
):
    q = db.query(Inventory)
    if warehouse_id:
        if not warehouse_access(db, user, warehouse_id):
            raise ForbiddenError("Warehouse access denied")
        q = q.filter(Inventory.warehouse_id == warehouse_id)
    if product_id:
        q = q.filter(Inventory.product_id == product_id)
    if low_stock:
        q = q.filter(Inventory.available_quantity <= Inventory.reorder_level)
    if out_of_stock:
        q = q.filter(Inventory.available_quantity == 0)
    if user.role not in {Role.ADMIN, Role.CUSTOMER}:
        pass
    return q.all()


@router.get("/inventory/low-stock", response_model=list[InventoryOut])
def low_stock(db=Depends(get_db), user=Depends(current_user)):
    return (
        db.query(Inventory)
        .filter(Inventory.available_quantity <= Inventory.reorder_level)
        .all()
    )


@router.get("/inventory/{product_id}", response_model=list[InventoryOut])
def product_inventory(product_id: int, db=Depends(get_db), user=Depends(current_user)):
    return db.query(Inventory).filter_by(product_id=product_id).all()


@router.post("/inventory/adjust", response_model=InventoryOut)
def adjust(
    data: InventoryAdjustIn,
    db=Depends(get_db),
    user=Depends(roles(Role.ADMIN, Role.WAREHOUSE_MANAGER)),
):
    if not warehouse_access(db, user, data.warehouse_id):
        raise ForbiddenError("Warehouse access denied")
    inv = inv_svc.adjust(db, user.id, data)
    commit(db)
    return inv


@router.post("/inventory/transfer", response_model=list[InventoryOut])
def transfer(
    data: InventoryTransferIn,
    db=Depends(get_db),
    user=Depends(roles(Role.ADMIN, Role.WAREHOUSE_MANAGER)),
):
    if not warehouse_access(db, user, data.from_warehouse_id):
        raise ForbiddenError("Source warehouse access denied")
    if not warehouse_access(db, user, data.to_warehouse_id):
        raise ForbiddenError("Destination warehouse access denied")
    a, b = inv_svc.transfer(db, user.id, data)
    commit(db)
    return [a, b]


@router.post("/orders", response_model=OrderOut)
def create_order(data: OrderIn, db=Depends(get_db), user=Depends(roles(Role.CUSTOMER))):
    order = order_svc.create_order(db, user.id, data)
    commit(db)
    db.refresh(order)
    return serialize_order(db, order)


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    db=Depends(get_db),
    user=Depends(current_user),
    status: OrderStatus | None = None,
    warehouse_id: int | None = None,
    customer_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
):
    q = db.query(Order)
    if user.role == Role.CUSTOMER:
        q = q.filter(Order.customer_id == user.id)
    elif warehouse_id:
        if not warehouse_access(db, user, warehouse_id):
            raise ForbiddenError("Warehouse access denied")
        q = q.filter(Order.warehouse_id == warehouse_id)
    if status:
        q = q.filter(Order.status == status)
    if customer_id and user.role != Role.CUSTOMER:
        q = q.filter(Order.customer_id == customer_id)
    return [
        serialize_order(db, o)
        for o in q.order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(min(page_size, 100))
        .all()
    ]


@router.get("/orders/{id}", response_model=OrderOut)
def get_order(id: int, db=Depends(get_db), user=Depends(current_user)):
    o = db.get(Order, id)
    if not o:
        raise NotFoundError("Order not found")
    if user.role == Role.CUSTOMER and o.customer_id != user.id:
        raise ForbiddenError("Order access denied")
    if user.role in {
        Role.WAREHOUSE_MANAGER,
        Role.FULFILLMENT_AGENT,
    } and not warehouse_access(db, user, o.warehouse_id):
        raise ForbiddenError("Warehouse access denied")
    return serialize_order(db, o)


@router.post("/orders/{id}/status", response_model=OrderOut)
def status_order(
    id: int, data: StatusIn, db=Depends(get_db), user=Depends(current_user)
):
    o = db.get(Order, id)
    if not o:
        raise NotFoundError("Order not found")
    if user.role == Role.CUSTOMER and data.status != OrderStatus.CANCELLED:
        raise ForbiddenError("Customers cannot perform this transition")
    if user.role in {
        Role.WAREHOUSE_MANAGER,
        Role.FULFILLMENT_AGENT,
    } and not warehouse_access(db, user, o.warehouse_id):
        raise ForbiddenError("Warehouse access denied")
    order_svc.set_status(db, user, o, data.status)
    commit(db)
    return serialize_order(db, o)


@router.post("/orders/{id}/assign", response_model=Message)
def assign_order(
    id: int,
    data: AssignIn,
    db=Depends(get_db),
    user=Depends(roles(Role.ADMIN, Role.WAREHOUSE_MANAGER)),
):
    o = db.get(Order, id)
    if not o:
        raise NotFoundError("Order not found")
    if user.role != Role.ADMIN and not warehouse_access(db, user, o.warehouse_id):
        raise ForbiddenError("Warehouse access denied")
    order_svc.assign(db, user, o, data.agent_id)
    commit(db)
    return Message(message="Order assigned")


def serialize_order(db, o):
    items = db.query(OrderItem).filter_by(order_id=o.id).all()
    return OrderOut(
        id=o.id,
        order_number=o.order_number,
        customer_id=o.customer_id,
        warehouse_id=o.warehouse_id,
        total_amount=o.total_amount,
        status=o.status,
        payment_status=o.payment_status,
        items=items,
    )


@router.post("/returns", response_model=Message)
def create_return(
    data: ReturnIn, db=Depends(get_db), user=Depends(roles(Role.CUSTOMER))
):
    o = db.get(Order, data.order_id)
    if not o or o.customer_id != user.id:
        raise ForbiddenError("Order access denied")
    if o.status != OrderStatus.DELIVERED:
        raise DomainError(
            "INVALID_RETURN", "Only delivered orders can be returned", 409
        )
    r = Return(order_id=o.id, customer_id=user.id, reason=data.reason)
    db.add(r)
    db.flush()
    for x in data.items:
        db.add(ReturnItem(return_id=r.id, product_id=x.product_id, quantity=x.quantity))
    audit(db, user.id, "Return Created", "return", r.id)
    notify(db, user.id, "Return Requested", f"Return {r.id} requested")
    commit(db)
    return Message(message=f"Return {r.id} created")


@router.post("/returns/{id}/status", response_model=Message)
def return_status(
    id: int,
    data: ReturnStatusIn,
    db=Depends(get_db),
    user=Depends(roles(Role.ADMIN, Role.WAREHOUSE_MANAGER)),
):
    r = db.get(Return, id)
    if not r:
        raise NotFoundError("Return not found")
    allowed = {
        ReturnStatus.REQUESTED: {ReturnStatus.APPROVED, ReturnStatus.REJECTED},
        ReturnStatus.APPROVED: {ReturnStatus.RECEIVED},
        ReturnStatus.RECEIVED: {ReturnStatus.REFUNDED},
        ReturnStatus.REJECTED: set(),
        ReturnStatus.REFUNDED: set(),
    }
    if data.status not in allowed[r.status]:
        raise DomainError("INVALID_RETURN_STATUS", "Invalid return transition", 409)
    r.status = data.status
    audit(
        db,
        user.id,
        "Return Status Changed",
        "return",
        id,
        {"status": data.status.value},
    )
    commit(db)
    return Message(message="Return status updated")


@router.get("/notifications")
def notifications(db=Depends(get_db), user=Depends(current_user)):
    return (
        db.query(Notification)
        .filter_by(user_id=user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )


@router.patch("/notifications/{id}/read", response_model=Message)
def read_notification(id: int, db=Depends(get_db), user=Depends(current_user)):
    n = db.get(Notification, id)
    if not n or n.user_id != user.id:
        raise NotFoundError("Notification not found")
    n.is_read = True
    commit(db)
    return Message(message="Notification marked read")


@router.patch("/notifications/read-all", response_model=Message)
def read_all(db=Depends(get_db), user=Depends(current_user)):
    db.query(Notification).filter_by(user_id=user.id, is_read=False).update(
        {"is_read": True}
    )
    commit(db)
    return Message(message="All notifications marked read")


@router.get("/dashboard")
def dashboard(db=Depends(get_db), user=Depends(current_user)):
    if user.role == Role.CUSTOMER:
        base = db.query(Order).filter(Order.customer_id == user.id)
        return {
            "total_orders": base.count(),
            "active_orders": base.filter(
                Order.status.in_(
                    [
                        OrderStatus.PENDING,
                        OrderStatus.CONFIRMED,
                        OrderStatus.PROCESSING,
                        OrderStatus.PACKED,
                        OrderStatus.SHIPPED,
                    ]
                )
            ).count(),
            "completed_orders": base.filter(
                Order.status == OrderStatus.DELIVERED
            ).count(),
            "cancelled_orders": base.filter(
                Order.status == OrderStatus.CANCELLED
            ).count(),
            "total_spending": sum((x.total_amount for x in base.all()), 0),
        }
    if user.role == Role.ADMIN:
        q = db.query(Order)
        inv = db.query(Inventory)
        return {
            "total_orders": q.count(),
            "pending_orders": q.filter(Order.status == OrderStatus.PENDING).count(),
            "processing_orders": q.filter(
                Order.status == OrderStatus.PROCESSING
            ).count(),
            "completed_orders": q.filter(Order.status == OrderStatus.DELIVERED).count(),
            "cancelled_orders": q.filter(Order.status == OrderStatus.CANCELLED).count(),
            "total_revenue": db.query(func.coalesce(func.sum(Order.total_amount), 0))
            .filter(Order.status == OrderStatus.DELIVERED)
            .scalar(),
            "low_stock_products": inv.filter(
                Inventory.available_quantity <= Inventory.reorder_level
            ).count(),
            "out_of_stock_products": inv.filter(
                Inventory.available_quantity == 0
            ).count(),
        }
    warehouses = (
        db.query(WarehouseUser.warehouse_id)
        .filter(WarehouseUser.user_id == user.id)
        .all()
    )
    ids = [x[0] for x in warehouses]
    return {
        "warehouse_ids": ids,
        "pending_fulfillment": db.query(Order)
        .filter(Order.warehouse_id.in_(ids), Order.status == OrderStatus.PENDING)
        .count(),
        "processing_orders": db.query(Order)
        .filter(Order.warehouse_id.in_(ids), Order.status == OrderStatus.PROCESSING)
        .count(),
        "low_stock_items": db.query(Inventory)
        .filter(
            Inventory.warehouse_id.in_(ids),
            Inventory.available_quantity <= Inventory.reorder_level,
        )
        .count(),
    }


@router.get("/audit-logs")
def audit_logs(
    db=Depends(get_db),
    user=Depends(roles(Role.ADMIN)),
    page: int = 1,
    page_size: int = 50,
):
    return (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(min(page_size, 200))
        .all()
    )
