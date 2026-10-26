# Order Fulfillment & Inventory Management Platform

Production-oriented FastAPI REST API for an order fulfillment system with PostgreSQL, SQLAlchemy, Alembic, JWT authentication, RBAC, warehouse authorization, inventory reservations, transactional transfers, order state transitions, notifications, audit logging, idempotency storage, reporting, Docker and Pytest.

## 1. Architecture

```text
Client / Postman / Frontend
          |
          v
      FastAPI Routes
          |
   Dependencies / JWT / RBAC
          |
          v
       Services
   /        |        \
Auth   Orders/Inventory   Audit/Notify
          |
          v
      SQLAlchemy ORM
          |
          v
      PostgreSQL
```

Business rules belong in services. Routes validate HTTP input, authorize the request and call services. PostgreSQL is the source of truth.

## 2. Main business flow

```text
Register -> Login -> Access Token
                     |
Customer -> Create Order
                     |
                     v
             DB transaction begins
                     |
          Lock inventory row FOR UPDATE
                     |
       Check available >= requested qty
                     |
      available -= qty; reserved += qty
                     |
        create inventory transaction
                     |
          create order + order items
                     |
       audit + notification + commit
```

### Concurrency strategy
Inventory reservation locks the exact `(product_id, warehouse_id)` inventory row using PostgreSQL `SELECT ... FOR UPDATE`. Two concurrent orders therefore serialize on the same inventory row. The second transaction sees the first transaction's committed quantity and fails with `INSUFFICIENT_INVENTORY` when stock is exhausted. Inventory transfer locks source/destination rows in deterministic warehouse-id order to reduce deadlock risk.

## 3. Roles

- `admin`: global management
- `warehouse_manager`: authorized warehouse inventory/fulfillment operations
- `fulfillment_agent`: processes orders in authorized warehouses
- `customer`: own orders and returns

Warehouse membership is stored in `warehouse_users` and checked for resource authorization.

## 4. Requirements

- Python 3.12+
- PostgreSQL 15+
- Docker Desktop optional

## 5. Local Windows PowerShell setup

```powershell
cd order_fulfillment_inventory_platform
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with your PostgreSQL credentials.

Create the database:

```sql
CREATE DATABASE order_platform;
```

Run migrations:

```powershell
alembic upgrade head
python seed.py
```

Start API:

```powershell
uvicorn app.main:app --reload
```

Open Swagger: `http://127.0.0.1:8000/docs`
Open ReDoc: `http://127.0.0.1:8000/redoc`
Health: `http://127.0.0.1:8000/health`

## 6. Docker

```powershell
docker compose up --build
```

The API will be on port 8000 and PostgreSQL on 5432. The API container runs `alembic upgrade head` before starting Uvicorn.

## 7. Seed account

After `python seed.py`:

- Email: `admin@example.com`
- Password: `Admin@12345`

Change the password immediately in any non-demo environment.

## 8. Authentication flow

### Register
`POST /api/auth/register`

```json
{
  "email": "customer@example.com",
  "full_name": "Customer One",
  "password": "Customer@12345",
  "role": "customer"
}
```

### Login
`POST /api/auth/login`

```json
{"email":"customer@example.com","password":"Customer@12345"}
```

Copy `access_token` and send:

```text
Authorization: Bearer <access_token>
```

### Refresh
`POST /api/auth/refresh`

```json
{"refresh_token":"<refresh token>"}
```

Refresh-token rotation revokes the old refresh token and creates a new one.

### Logout
`POST /api/auth/logout`

```json
{"refresh_token":"<refresh token>"}
```

## 9. API endpoint guide

### Authentication
| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | `/api/auth/register` | Public | Register |
| POST | `/api/auth/login` | Public | Login |
| POST | `/api/auth/refresh` | Public | Rotate refresh token |
| POST | `/api/auth/logout` | Auth | Revoke refresh token |
| GET | `/api/auth/me` | Auth | Current user |
| POST | `/api/auth/change-password` | Auth | Change password |

### Products
| Method | Endpoint | Access |
|---|---|---|
| POST | `/api/products` | Admin |
| GET | `/api/products` | Auth |
| GET | `/api/products/{id}` | Auth |
| PATCH | `/api/products/{id}` | Admin |
| POST | `/api/products/{id}/activate` | Admin |
| POST | `/api/products/{id}/deactivate` | Admin |

Create example:

```json
{"sku":"SKU-2001","name":"Laptop Bag","description":"Demo","category_id":1,"price":1200,"cost_price":700}
```

### Warehouses
| Method | Endpoint | Access |
|---|---|---|
| POST | `/api/warehouses` | Admin |
| GET | `/api/warehouses` | Auth |
| GET | `/api/warehouses/{id}` | Authorized |
| PATCH | `/api/warehouses/{id}` | Admin |
| POST | `/api/warehouses/{id}/activate` | Admin |
| POST | `/api/warehouses/{id}/deactivate` | Admin |
| POST | `/api/warehouses/{id}/users/{user_id}` | Admin/Manager |

### Inventory
| Method | Endpoint | Access |
|---|---|---|
| GET | `/api/inventory` | Auth |
| GET | `/api/inventory/{product_id}` | Auth |
| GET | `/api/inventory/low-stock` | Auth |
| POST | `/api/inventory/adjust` | Admin/Manager |
| POST | `/api/inventory/transfer` | Admin/Manager |

Adjustment:

```json
{"product_id":1,"warehouse_id":1,"quantity":100,"reason":"Initial stock","idempotency_key":"initial-001"}
```

Transfer:

```json
{"product_id":1,"from_warehouse_id":1,"to_warehouse_id":2,"quantity":20,"reason":"Rebalancing","idempotency_key":"transfer-001"}
```

### Orders
| Method | Endpoint | Access |
|---|---|---|
| POST | `/api/orders` | Customer |
| GET | `/api/orders` | Auth |
| GET | `/api/orders/{id}` | Scoped |
| POST | `/api/orders/{id}/status` | Scoped |
| POST | `/api/orders/{id}/assign` | Admin/Manager |

Create order:

```json
{
  "warehouse_id":1,
  "items":[
    {"product_id":1,"quantity":2,"discount":0,"tax":10}
  ],
  "idempotency_key":"order-2026-0001"
}
```

Order states:

```text
PENDING -> CONFIRMED -> PROCESSING -> PACKED -> SHIPPED -> DELIVERED -> RETURNED
   |          |             |
   +----------+-------------+----> CANCELLED
```

Invalid transitions return HTTP 409.

### Returns
| Method | Endpoint | Access |
|---|---|---|
| POST | `/api/returns` | Customer |
| POST | `/api/returns/{id}/status` | Admin/Manager |

Return states:

```text
REQUESTED -> APPROVED -> RECEIVED -> REFUNDED
     |
     +----> REJECTED
```

### Notifications
| Method | Endpoint | Access |
|---|---|---|
| GET | `/api/notifications` | Auth |
| PATCH | `/api/notifications/{id}/read` | Owner |
| PATCH | `/api/notifications/read-all` | Auth |

### Reporting
`GET /api/dashboard` returns role-specific dashboard metrics.

### Audit
`GET /api/audit-logs` is admin-only. Audit records are append-only through the application; no update/delete API is exposed.

## 10. Error contract

```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_INVENTORY",
    "message": "Insufficient inventory for product 1"
  }
}
```

Typical codes include:

- `INSUFFICIENT_INVENTORY` - 409
- `INVALID_ORDER_STATUS` - 409
- `INVALID_RETURN_STATUS` - 409
- `WAREHOUSE_ACCESS_DENIED` - 403
- `PRODUCT_INACTIVE` - 409
- `DUPLICATE_SKU` - 409
- `INVALID_INVENTORY_TRANSFER` - 400
- `UNAUTHORIZED` - 401
- `FORBIDDEN` - 403
- `NOT_FOUND` - 404
- `VALIDATION_ERROR` - 422

## 11. Database design

Core tables:

```text
users
roles (role is represented as a constrained application enum)
categories
products
warehouses
warehouse_users
inventory
inventory_transactions
orders
order_items
order_status_history
order_assignments
returns
return_items
notifications
audit_logs
refresh_tokens
idempotency_keys
```

Important constraints/indexes:

- unique user email
- unique product SKU
- unique product/warehouse inventory pair
- unique warehouse/user membership
- unique refresh-token JTI
- unique `(idempotency key, user, endpoint)`
- non-negative product prices
- non-negative inventory quantities
- indexed order number/status/created time
- foreign keys on all relationships

## 12. Idempotency

The schema contains `idempotency_keys` and request models accept `idempotency_key`. For a hardened production deployment, persist the request fingerprint and exact HTTP response before returning it, and reject a reused key with a different request body. This repository keeps the storage boundary explicit so the mechanism can be extended without putting business logic into route handlers.

## 13. Background jobs

Notifications are persisted synchronously with the business transaction so an order event and its notification cannot diverge. A production deployment can move delivery to Celery/Redis after commit while retaining the database notification record as the durable source.

## 14. Testing

Run:

```powershell
pytest -q
```

For full integration testing, point `DATABASE_URL` at a disposable PostgreSQL test database and add concurrent HTTP tests around the inventory reservation service.

## 15. Production deployment checklist

1. Use a managed PostgreSQL instance.
2. Generate a cryptographically random `SECRET_KEY`.
3. Store secrets in the deployment platform, never Git.
4. Run `alembic upgrade head` during release/deploy.
5. Run multiple Uvicorn workers behind a load balancer.
6. Use HTTPS.
7. Configure database connection pool sizes for the deployment capacity.
8. Add structured logs, metrics and tracing.
9. Move outbound notification delivery to Celery/Redis if email/SMS/push is required.
10. Add a separate PostgreSQL test database and CI pipeline.
11. Add rate limiting for authentication endpoints.
12. Back up PostgreSQL and test restore procedures.

## 16. Postman

Import `postman_collection.json`. Set `base_url` to `http://127.0.0.1:8000`. The collection contains the main authentication, product, warehouse, inventory, order, return, notification and dashboard requests.
