import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from validator import SQLValidationError, validate_sql_query

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    prompt: str


@app.post("/api/chat")
def chat(req: ChatRequest):
    # Simulated query to test validator integration
    test_generated_sql = "DELETE FROM draws WHERE id = 1"

    try:
        # Run security check
        safe_sql = validate_sql_query(test_generated_sql)

        # Execute safe query
        conn = sqlite3.connect("fdj_draws.db")
        cursor = conn.cursor()
        cursor.execute(safe_sql)
        rows = cursor.fetchall()
        conn.close()

        return {
            "reply": f"Query: `{safe_sql}`\nResults: {rows}",
            "model": "security-harness-active",
        }
    except SQLValidationError as err:
        raise HTTPException(
            status_code=400, detail=f"SQL Security Error: {str(err)}"
        )