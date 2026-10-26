from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Numeric, Text, JSON, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

def now(): return datetime.now(timezone.utc)

class Role(str, Enum): ADMIN="admin"; WAREHOUSE_MANAGER="warehouse_manager"; FULFILLMENT_AGENT="fulfillment_agent"; CUSTOMER="customer"
class Status(str, Enum): ACTIVE="active"; INACTIVE="inactive"
class OrderStatus(str, Enum): PENDING="pending"; CONFIRMED="confirmed"; PROCESSING="processing"; PACKED="packed"; SHIPPED="shipped"; DELIVERED="delivered"; CANCELLED="cancelled"; FAILED="failed"; RETURNED="returned"
class PaymentStatus(str, Enum): PENDING="pending"; PAID="paid"; FAILED="failed"; REFUNDED="refunded"
class ReturnStatus(str, Enum): REQUESTED="requested"; APPROVED="approved"; REJECTED="rejected"; RECEIVED="received"; REFUNDED="refunded"
class TxType(str, Enum): PURCHASE="purchase"; SALE="sale"; RESERVATION="reservation"; RELEASE="release"; ADJUSTMENT="adjustment"; TRANSFER_IN="transfer_in"; TRANSFER_OUT="transfer_out"; RETURN="return"; DAMAGE="damage"

class User(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(primary_key=True); email: Mapped[str]=mapped_column(String(255),unique=True,index=True); full_name: Mapped[str]=mapped_column(String(120)); password_hash: Mapped[str]=mapped_column(String(255)); role: Mapped[Role]=mapped_column(default=Role.CUSTOMER); is_active: Mapped[bool]=mapped_column(Boolean,default=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class RefreshToken(Base):
    __tablename__="refresh_tokens"
    id: Mapped[int]=mapped_column(primary_key=True); jti: Mapped[str]=mapped_column(String(64),unique=True,index=True); user_id: Mapped[int]=mapped_column(ForeignKey("users.id")); expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True)); revoked_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
class Category(Base):
    __tablename__="categories"
    id: Mapped[int]=mapped_column(primary_key=True); name: Mapped[str]=mapped_column(String(100),unique=True); is_active: Mapped[bool]=mapped_column(Boolean,default=True)
class Product(Base):
    __tablename__="products"
    id: Mapped[int]=mapped_column(primary_key=True); sku: Mapped[str]=mapped_column(String(80),unique=True,index=True); name: Mapped[str]=mapped_column(String(180)); description: Mapped[str|None]=mapped_column(Text); category_id: Mapped[int|None]=mapped_column(ForeignKey("categories.id")); price: Mapped[Decimal]=mapped_column(Numeric(12,2)); cost_price: Mapped[Decimal]=mapped_column(Numeric(12,2)); status: Mapped[Status]=mapped_column(default=Status.ACTIVE); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
    __table_args__=(CheckConstraint("price >= 0"), CheckConstraint("cost_price >= 0"))
class Warehouse(Base):
    __tablename__="warehouses"
    id: Mapped[int]=mapped_column(primary_key=True); name: Mapped[str]=mapped_column(String(120)); location: Mapped[str]=mapped_column(String(255)); status: Mapped[Status]=mapped_column(default=Status.ACTIVE); capacity: Mapped[int]=mapped_column(Integer); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
class WarehouseUser(Base):
    __tablename__="warehouse_users"
    id: Mapped[int]=mapped_column(primary_key=True); warehouse_id: Mapped[int]=mapped_column(ForeignKey("warehouses.id",ondelete="CASCADE")); user_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE")); __table_args__=(UniqueConstraint("warehouse_id","user_id"),)
class Inventory(Base):
    __tablename__="inventory"
    id: Mapped[int]=mapped_column(primary_key=True); product_id: Mapped[int]=mapped_column(ForeignKey("products.id")); warehouse_id: Mapped[int]=mapped_column(ForeignKey("warehouses.id")); available_quantity: Mapped[int]=mapped_column(Integer,default=0); reserved_quantity: Mapped[int]=mapped_column(Integer,default=0); damaged_quantity: Mapped[int]=mapped_column(Integer,default=0); reorder_level: Mapped[int]=mapped_column(Integer,default=0); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now); __table_args__=(UniqueConstraint("product_id","warehouse_id"),CheckConstraint("available_quantity >= 0"),CheckConstraint("reserved_quantity >= 0"))
class InventoryTransaction(Base):
    __tablename__="inventory_transactions"
    id: Mapped[int]=mapped_column(primary_key=True); product_id: Mapped[int]=mapped_column(ForeignKey("products.id")); warehouse_id: Mapped[int]=mapped_column(ForeignKey("warehouses.id")); transaction_type: Mapped[TxType]=mapped_column(); quantity: Mapped[int]=mapped_column(Integer); reference_entity: Mapped[str|None]=mapped_column(String(80)); reference_id: Mapped[str|None]=mapped_column(String(80)); user_id: Mapped[int|None]=mapped_column(ForeignKey("users.id")); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); metadata_json: Mapped[dict|None]=mapped_column(JSON)
class Order(Base):
    __tablename__="orders"
    id: Mapped[int]=mapped_column(primary_key=True); order_number: Mapped[str]=mapped_column(String(40),unique=True,index=True); customer_id: Mapped[int]=mapped_column(ForeignKey("users.id")); warehouse_id: Mapped[int]=mapped_column(ForeignKey("warehouses.id")); total_amount: Mapped[Decimal]=mapped_column(Numeric(12,2)); status: Mapped[OrderStatus]=mapped_column(default=OrderStatus.PENDING,index=True); payment_status: Mapped[PaymentStatus]=mapped_column(default=PaymentStatus.PENDING); expected_delivery_date: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
class OrderItem(Base):
    __tablename__="order_items"
    id: Mapped[int]=mapped_column(primary_key=True); order_id: Mapped[int]=mapped_column(ForeignKey("orders.id",ondelete="CASCADE")); product_id: Mapped[int]=mapped_column(ForeignKey("products.id")); quantity: Mapped[int]=mapped_column(Integer); unit_price: Mapped[Decimal]=mapped_column(Numeric(12,2)); discount: Mapped[Decimal]=mapped_column(Numeric(12,2),default=0); tax: Mapped[Decimal]=mapped_column(Numeric(12,2),default=0); total: Mapped[Decimal]=mapped_column(Numeric(12,2))
class OrderStatusHistory(Base):
    __tablename__="order_status_history"
    id: Mapped[int]=mapped_column(primary_key=True); order_id: Mapped[int]=mapped_column(ForeignKey("orders.id",ondelete="CASCADE")); old_status: Mapped[str|None]=mapped_column(String(30)); new_status: Mapped[str]=mapped_column(String(30)); user_id: Mapped[int]=mapped_column(ForeignKey("users.id")); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class OrderAssignment(Base):
    __tablename__="order_assignments"
    id: Mapped[int]=mapped_column(primary_key=True); order_id: Mapped[int]=mapped_column(ForeignKey("orders.id",ondelete="CASCADE")); agent_id: Mapped[int]=mapped_column(ForeignKey("users.id")); assigned_by: Mapped[int]=mapped_column(ForeignKey("users.id")); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Return(Base):
    __tablename__="returns"
    id: Mapped[int]=mapped_column(primary_key=True); order_id: Mapped[int]=mapped_column(ForeignKey("orders.id")); customer_id: Mapped[int]=mapped_column(ForeignKey("users.id")); status: Mapped[ReturnStatus]=mapped_column(default=ReturnStatus.REQUESTED); reason: Mapped[str]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class ReturnItem(Base):
    __tablename__="return_items"
    id: Mapped[int]=mapped_column(primary_key=True); return_id: Mapped[int]=mapped_column(ForeignKey("returns.id",ondelete="CASCADE")); product_id: Mapped[int]=mapped_column(ForeignKey("products.id")); quantity: Mapped[int]=mapped_column(Integer)
class Notification(Base):
    __tablename__="notifications"
    id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE")); title: Mapped[str]=mapped_column(String(180)); message: Mapped[str]=mapped_column(Text); is_read: Mapped[bool]=mapped_column(Boolean,default=False,index=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class AuditLog(Base):
    __tablename__="audit_logs"
    id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int|None]=mapped_column(ForeignKey("users.id")); action: Mapped[str]=mapped_column(String(100),index=True); entity: Mapped[str]=mapped_column(String(80)); entity_id: Mapped[str|None]=mapped_column(String(80)); timestamp: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True); ip_address: Mapped[str|None]=mapped_column(String(64)); metadata_json: Mapped[dict|None]=mapped_column(JSON)
class IdempotencyKey(Base):
    __tablename__="idempotency_keys"
    id: Mapped[int]=mapped_column(primary_key=True); key: Mapped[str]=mapped_column(String(128)); user_id: Mapped[int]=mapped_column(ForeignKey("users.id")); endpoint: Mapped[str]=mapped_column(String(180)); response_json: Mapped[dict|None]=mapped_column(JSON); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); __table_args__=(UniqueConstraint("key","user_id","endpoint"),)
