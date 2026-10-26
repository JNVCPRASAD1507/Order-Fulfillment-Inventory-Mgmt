from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Inventory, InventoryTransaction, Product, Warehouse, TxType
from app.core.errors import DomainError, NotFoundError
from app.services.common import audit, notify

def get_or_create(db, product_id, warehouse_id, lock=False):
    q=select(Inventory).where(Inventory.product_id==product_id,Inventory.warehouse_id==warehouse_id)
    if lock: q=q.with_for_update()
    row=db.execute(q).scalar_one_or_none()
    if not row:
        row=Inventory(product_id=product_id,warehouse_id=warehouse_id); db.add(row); db.flush()
    return row

def record(db,user_id,inv,typ,qty,ref_entity=None,ref_id=None,metadata=None):
    db.add(InventoryTransaction(product_id=inv.product_id,warehouse_id=inv.warehouse_id,transaction_type=typ,quantity=qty,reference_entity=ref_entity,reference_id=str(ref_id) if ref_id else None,user_id=user_id,metadata_json=metadata))

def reserve(db,user_id,product_id,warehouse_id,qty,order_id):
    inv=get_or_create(db,product_id,warehouse_id,True)
    if inv.available_quantity < qty: raise DomainError("INSUFFICIENT_INVENTORY",f"Insufficient inventory for product {product_id}",409)
    inv.available_quantity-=qty; inv.reserved_quantity+=qty
    record(db,user_id,inv,TxType.RESERVATION,qty,"order",order_id); audit(db,user_id,"Inventory Reserved","inventory",inv.id,{"quantity":qty,"order_id":order_id})

def release(db,user_id,product_id,warehouse_id,qty,order_id):
    inv=get_or_create(db,product_id,warehouse_id,True)
    if inv.reserved_quantity < qty: raise DomainError("INVALID_RESERVATION","Reserved quantity is insufficient",409)
    inv.reserved_quantity-=qty; inv.available_quantity+=qty
    record(db,user_id,inv,TxType.RELEASE,qty,"order",order_id); audit(db,user_id,"Inventory Released","inventory",inv.id,{"quantity":qty,"order_id":order_id})

def adjust(db,user_id,data):
    inv=get_or_create(db,data.product_id,data.warehouse_id,True); old=inv.available_quantity; new=old+data.quantity
    if new<0: raise DomainError("NEGATIVE_INVENTORY","Inventory cannot become negative",409)
    inv.available_quantity=new; record(db,user_id,inv,TxType.ADJUSTMENT,data.quantity,"adjustment",None,{"previous":old,"new":new,"reason":data.reason}); audit(db,user_id,"Inventory Adjusted","inventory",inv.id,{"previous":old,"new":new,"reason":data.reason}); return inv

def transfer(db,user_id,data):
    if data.from_warehouse_id==data.to_warehouse_id: raise DomainError("INVALID_INVENTORY_TRANSFER","Source and destination warehouses must differ",400)
    # deterministic lock order prevents common deadlocks between opposite transfers
    ids=sorted([data.from_warehouse_id,data.to_warehouse_id]); invs={}
    for wid in ids: invs[wid]=get_or_create(db,data.product_id,wid,True)
    src=invs[data.from_warehouse_id]; dst=invs[data.to_warehouse_id]
    if src.available_quantity<data.quantity: raise DomainError("INSUFFICIENT_INVENTORY","Insufficient source inventory",409)
    src.available_quantity-=data.quantity; dst.available_quantity+=data.quantity
    record(db,user_id,src,TxType.TRANSFER_OUT,data.quantity,"warehouse_transfer",None,{"to":data.to_warehouse_id}); record(db,user_id,dst,TxType.TRANSFER_IN,data.quantity,"warehouse_transfer",None,{"from":data.from_warehouse_id}); audit(db,user_id,"Inventory Transferred","inventory",src.id,{"to":data.to_warehouse_id,"quantity":data.quantity}); return src,dst
