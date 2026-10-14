# Windows Run Guide

## 1. PostgreSQL

Create a database in PostgreSQL:

```sql
CREATE USER fulfillment_user WITH PASSWORD 'your-password';
CREATE DATABASE fulfillment OWNER fulfillment_user;
```

## 2. Backend environment

Open PowerShell:

```powershell
cd server
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Set at least:

```env
DATABASE_URL=postgresql+psycopg2://fulfillment_user:your-password@localhost:5432/fulfillment
SECRET_KEY=replace-with-a-random-secret-at-least-32-characters-long
ACCESS_TOKEN_MINUTES=1440
REFRESH_TOKEN_DAYS=14
```

## 3. Database migration

```powershell
alembic upgrade head
```

## 4. Create admin

```powershell
python -m app.seed_admin
```

Enter the admin name, email, and password when prompted.

## 5. Run API

```powershell
uvicorn app.main:app --reload
```

Open:

- Swagger: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health: http://127.0.0.1:8000/health

## 6. First API flow

1. Login as the admin using `POST /auth/login`.
2. Create a category with `POST /categories`.
3. Create a product with `POST /products`.
4. Create a warehouse with `POST /warehouses`.
5. Create a warehouse manager with `POST /users`.
6. Add the manager to the warehouse with `POST /warehouses/{warehouse_id}/users`.
7. Add inventory with `POST /inventory/adjust`.
8. Register a customer with `POST /auth/register`.
9. Login as the customer.
10. Create an order with `POST /orders`.
11. Login as a warehouse manager/fulfillment agent and process the order.

All protected endpoints use:

```text
Authorization: Bearer <access_token>
```

Do not put database passwords, JWT secrets, or real payment credentials into
source control.
