from app.db.session import SessionLocal
from app.models import User, Role, Category, Product, Warehouse, WarehouseUser, Inventory, Status
from app.core.security import hash_password

def main():
    db=SessionLocal()
    try:
        admin=db.query(User).filter_by(email='admin@example.com').first()
        if not admin:
            admin=User(email='admin@example.com',full_name='System Admin',password_hash=hash_password('Admin@12345'),role=Role.ADMIN); db.add(admin); db.flush()
        wh=db.query(Warehouse).filter_by(name='Main Warehouse').first()
        if not wh: wh=Warehouse(name='Main Warehouse',location='Hyderabad',capacity=10000,status=Status.ACTIVE); db.add(wh); db.flush()
        cat=db.query(Category).filter_by(name='General').first()
        if not cat: cat=Category(name='General'); db.add(cat); db.flush()
        if not db.query(Product).filter_by(sku='SKU-1001').first(): db.add(Product(sku='SKU-1001',name='Demo Product',category_id=cat.id,price=100,cost_price=60,status=Status.ACTIVE))
        db.commit(); print('Seeded admin@example.com / Admin@12345')
    finally: db.close()
if __name__=='__main__': main()
