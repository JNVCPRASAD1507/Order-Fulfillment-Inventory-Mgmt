from decimal import Decimal
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import *
from app.core.errors import DomainError, NotFoundError, ForbiddenError
from app.services.inventory import reserve, release
from app.services.common import audit, notify
TRANSITIONS={OrderStatus.PENDING:{OrderStatus.CONFIRMED,OrderStatus.CANCELLED,OrderStatus.FAILED},OrderStatus.CONFIRMED:{OrderStatus.PROCESSING,OrderStatus.CANCELLED,OrderStatus.FAILED},OrderStatus.PROCESSING:{OrderStatus.PACKED,OrderStatus.CANCELLED,OrderStatus.FAILED},OrderStatus.PACKED:{OrderStatus.SHIPPED},OrderStatus.SHIPPED:{OrderStatus.DELIVERED},OrderStatus.DELIVERED:{OrderStatus.RETURNED},OrderStatus.FAILED:set(),OrderStatus.CANCELLED:set(),OrderStatus.RETURNED:set()}

def create_order(db,user_id,data):
    wh=db.get(Warehouse,data.warehouse_id)
    if not wh or wh.status!=Status.ACTIVE: raise DomainError("WAREHOUSE_UNAVAILABLE","Warehouse unavailable",409)
    order=Order(order_number=f"ORD-{uuid4().hex[:12].upper()}",customer_id=user_id,warehouse_id=data.warehouse_id,total_amount=0)
    db.add(order); db.flush(); total=Decimal("0")
    for item in data.items:
        p=db.execute(select(Product).where(Product.id==item.product_id,Product.status==Status.ACTIVE)).scalar_one_or_none()
        if not p: raise DomainError("PRODUCT_INACTIVE",f"Product {item.product_id} is inactive or missing",409)
        line=(p.price*item.quantity)-item.discount+item.tax
        oi=OrderItem(order_id=order.id,product_id=p.id,quantity=item.quantity,unit_price=p.price,discount=item.discount,tax=item.tax,total=line); db.add(oi); total+=line
        reserve(db,user_id,p.id,wh.id,item.quantity,order.id)
    order.total_amount=total; db.add(OrderStatusHistory(order_id=order.id,old_status=None,new_status=order.status.value,user_id=user_id)); audit(db,user_id,"Order Created","order",order.id); notify(db,user_id,"Order Created",f"Order {order.order_number} was created"); return order

def set_status(db,user,order,status):
    if status not in TRANSITIONS[order.status]: raise DomainError("INVALID_ORDER_STATUS",f"Cannot transition {order.status.value} to {status.value}",409)
    old=order.status
    if status==OrderStatus.CANCELLED:
        if old in {OrderStatus.PACKED,OrderStatus.SHIPPED,OrderStatus.DELIVERED}: raise DomainError("INVALID_ORDER_STATUS","Order can no longer be cancelled",409)
        for item in db.query(OrderItem).filter(OrderItem.order_id==order.id): release(db,user.id,item.product_id,order.warehouse_id,item.quantity,order.id)
    order.status=status; db.add(OrderStatusHistory(order_id=order.id,old_status=old.value,new_status=status.value,user_id=user.id)); audit(db,user.id,"Order Status Changed","order",order.id,{"from":old.value,"to":status.value})
    if status==OrderStatus.CANCELLED: notify(db,order.customer_id,"Order Cancelled",f"Order {order.order_number} was cancelled")
    return order

def assign(db,user,order,agent_id):
    agent=db.get(User,agent_id)
    if not agent or agent.role!=Role.FULFILLMENT_AGENT or not agent.is_active: raise DomainError("INVALID_AGENT","Inactive or invalid fulfillment agent",409)
    access=db.query(WarehouseUser).filter(WarehouseUser.user_id==agent_id,WarehouseUser.warehouse_id==order.warehouse_id).first()
    if not access and user.role!=Role.ADMIN: raise ForbiddenError("Agent is not authorized for this warehouse")
    db.add(OrderAssignment(order_id=order.id,agent_id=agent_id,assigned_by=user.id)); audit(db,user.id,"Order Assigned","order",order.id,{"agent_id":agent_id}); notify(db,agent_id,"Order Assigned",f"Order {order.order_number} was assigned to you"); return agent
