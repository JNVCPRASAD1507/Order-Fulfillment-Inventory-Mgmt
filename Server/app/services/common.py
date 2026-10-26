from sqlalchemy.orm import Session
from app.models import AuditLog, Notification

def audit(db: Session, user_id, action, entity, entity_id=None, metadata=None, ip=None):
    db.add(AuditLog(user_id=user_id,action=action,entity=entity,entity_id=str(entity_id) if entity_id else None,metadata_json=metadata,ip_address=ip))

def notify(db: Session, user_id, title, message):
    if user_id: db.add(Notification(user_id=user_id,title=title,message=message))
