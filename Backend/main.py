import sqlite3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    # Hardcoded test query to verify pipeline end-to-end
    conn = sqlite3.connect("fdj_draws.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT date_de_tirage, boule_1, boule_2, boule_3, boule_4, boule_5 FROM draws ORDER BY date_de_tirage DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()

    return {
        "reply": f"Received prompt: '{req.prompt}'. Latest draw date: {row[0]}, Numbers: {row[1:]}",
        "model": "system-test",
    }