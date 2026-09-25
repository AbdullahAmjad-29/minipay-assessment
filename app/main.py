import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import psycopg2
from app.database import get_connection
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="MiniPay API")





class CustomerCreate(BaseModel):
    customer_ref: str
    name: str


class PaymentCreate(BaseModel):
    customer_id: int
    amount: float


@app.get("/health")
def health():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"database unavailable: {str(e)}")


@app.post("/api/customers", status_code=201)
def create_customer(customer: CustomerCreate):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO customers (customer_ref, name) VALUES (%s, %s) RETURNING id, customer_ref, name, created_at;",
            (customer.customer_ref, customer.name),
        )
        row = cur.fetchone()
        conn.commit()
        return {"id": row[0], "customer_ref": row[1], "name": row[2], "created_at": row[3]}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=409, detail=f"customer_ref '{customer.customer_ref}' already exists")
    finally:
        cur.close()
        conn.close()


@app.post("/api/payments", status_code=201)
def create_payment(
    payment: PaymentCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    conn = get_connection()
    cur = conn.cursor()
    try:
        if idempotency_key:
            cur.execute(
                "SELECT id, transaction_ref, customer_id, amount, status, created_at FROM transactions WHERE idempotency_key = %s;",
                (idempotency_key,),
            )
            existing = cur.fetchone()
            if existing:
                return {
                    "id": existing[0], "transaction_ref": existing[1], "customer_id": existing[2],
                    "amount": float(existing[3]), "status": existing[4], "created_at": existing[5],
                }

        cur.execute("SELECT id FROM customers WHERE id = %s;", (payment.customer_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail=f"customer_id {payment.customer_id} not found")

        if payment.amount <= 0:
            raise HTTPException(status_code=422, detail="amount must be greater than 0")

        transaction_ref = f"TXN{uuid.uuid4().hex[:12].upper()}"
        cur.execute(
            """INSERT INTO transactions (transaction_ref, customer_id, amount, status, created_at, idempotency_key)
               VALUES (%s, %s, %s, 'PROCESSING', %s, %s)
               RETURNING id, transaction_ref, customer_id, amount, status, created_at;""",
            (transaction_ref, payment.customer_id, payment.amount, datetime.utcnow(), idempotency_key),
        )
        row = cur.fetchone()
        conn.commit()
        return {
            "id": row[0], "transaction_ref": row[1], "customer_id": row[2],
            "amount": float(row[3]), "status": row[4], "created_at": row[5],
        }
    finally:
        cur.close()
        conn.close()


@app.get("/api/payments/{transaction_ref}")
def get_payment(transaction_ref: str):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, transaction_ref, customer_id, amount, status, created_at, completed_at FROM transactions WHERE transaction_ref = %s;",
            (transaction_ref,),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"transaction '{transaction_ref}' not found")
        return {
            "id": row[0], "transaction_ref": row[1], "customer_id": row[2],
            "amount": float(row[3]), "status": row[4], "created_at": row[5], "completed_at": row[6],
        }
    finally:
        cur.close()
        conn.close()


@app.get("/api/customers/{customer_id}/payments")
def get_customer_payments(customer_id: int):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM customers WHERE id = %s;", (customer_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail=f"customer_id {customer_id} not found")

        cur.execute(
            "SELECT id, transaction_ref, amount, status, created_at FROM transactions WHERE customer_id = %s ORDER BY created_at DESC;",
            (customer_id,),
        )
        rows = cur.fetchall()
        return [
            {"id": r[0], "transaction_ref": r[1], "amount": float(r[2]), "status": r[3], "created_at": r[4]}
            for r in rows
        ]
    finally:
        cur.close()
        conn.close()
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
