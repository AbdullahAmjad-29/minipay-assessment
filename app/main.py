from fastapi import FastAPI, HTTPException
from app.database import get_connection

app = FastAPI(title="MiniPay API")

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
