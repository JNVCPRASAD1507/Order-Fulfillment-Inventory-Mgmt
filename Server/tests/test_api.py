import os
os.environ.setdefault('DATABASE_URL','sqlite:///./test.db')
os.environ.setdefault('SECRET_KEY','test-secret')
# Production uses PostgreSQL. These tests are intentionally import/smoke tests unless TEST_DATABASE_URL is supplied.

def test_project_imports():
    from app.main import app
    assert app.title.startswith('Order Fulfillment')

def test_order_transition_matrix():
    from app.services.orders import TRANSITIONS
    from app.models import OrderStatus
    assert OrderStatus.PROCESSING in TRANSITIONS[OrderStatus.CONFIRMED]
    assert OrderStatus.PROCESSING not in TRANSITIONS[OrderStatus.DELIVERED]
