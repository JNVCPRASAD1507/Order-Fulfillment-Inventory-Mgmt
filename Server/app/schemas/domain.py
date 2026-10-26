from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from app.models.entities import Status, OrderStatus, PaymentStatus, ReturnStatus, TxType
class ProductIn(BaseModel): sku:str; name:str; description:str|None=None; category_id:int|None=None; price:Decimal=Field(ge=0); cost_price:Decimal=Field(ge=0)
class ProductOut(ProductIn): model_config=ConfigDict(from_attributes=True); id:int; status:Status
class WarehouseIn(BaseModel): name:str; location:str; capacity:int=Field(gt=0)
class WarehouseOut(WarehouseIn): model_config=ConfigDict(from_attributes=True); id:int; status:Status
class InventoryAdjustIn(BaseModel): product_id:int; warehouse_id:int; quantity:int; reason:str=Field(min_length=2); idempotency_key:str|None=None
class InventoryTransferIn(BaseModel): product_id:int; from_warehouse_id:int; to_warehouse_id:int; quantity:int=Field(gt=0); reason:str="transfer"; idempotency_key:str|None=None
class InventoryOut(BaseModel): model_config=ConfigDict(from_attributes=True); id:int; product_id:int; warehouse_id:int; available_quantity:int; reserved_quantity:int; damaged_quantity:int; reorder_level:int
class OrderItemIn(BaseModel): product_id:int; quantity:int=Field(gt=0); discount:Decimal=Field(default=0,ge=0); tax:Decimal=Field(default=0,ge=0)
class OrderIn(BaseModel): warehouse_id:int; items:list[OrderItemIn]=Field(min_length=1); idempotency_key:str|None=None
class OrderItemOut(OrderItemIn): model_config=ConfigDict(from_attributes=True); id:int; unit_price:Decimal; total:Decimal
class OrderOut(BaseModel): id:int; order_number:str; customer_id:int; warehouse_id:int; total_amount:Decimal; status:OrderStatus; payment_status:PaymentStatus; items:list[OrderItemOut]=[]
class StatusIn(BaseModel): status:OrderStatus
class AssignIn(BaseModel): agent_id:int
class ReturnIn(BaseModel): order_id:int; reason:str; items:list[OrderItemIn]=Field(min_length=1)
class ReturnStatusIn(BaseModel): status:ReturnStatus
