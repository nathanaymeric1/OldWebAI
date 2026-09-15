import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel
from validator import SQLValidationError, validate_sql_query

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "fdj_draws.db"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)


class ChatRequest(BaseModel):
    prompt: str


@app.post("/api/chat")
def chat(req: ChatRequest):
    try:
        # Step 1: AI1 generates SQL
        sql_prompt = (
            "You are a SQLite expert. Convert this request into a SQL query for the table 'draws' "
            "(columns: date_de_tirage, boule_1, boule_2, boule_3, boule_4, boule_5, numero_chance). "
            f"Return ONLY the raw SQL query, nothing else. Request: {req.prompt}"
        )

        res1 = client.chat.completions.create(
            model="cohere/north-mini-code:free",
            messages=[{"role": "user", "content": sql_prompt}],
            temperature=0.0,
        )

        # Defensive checks for AI1 response
        if not res1 or not res1.choices:
            raise HTTPException(
                status_code=502,
                detail="AI1 returned an empty response from OpenRouter.",
            )

        raw_sql = res1.choices[0].message.content or ""
        raw_sql = (
            raw_sql.strip().replace("```sql", "").replace("```", "").strip()
        )

        if not raw_sql:
            raise HTTPException(
                status_code=502, detail="AI1 failed to generate a SQL string."
            )

        # Step 2: Validate & Execute against SQLite
        safe_sql = validate_sql_query(raw_sql)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(safe_sql)
        db_results = cursor.fetchall()
        conn.close()

        # Step 3: AI2 Synthesizes response
        synth_prompt = (
            f"The user asked: '{req.prompt}'. "
            f"The database returned this raw data: {db_results}. "
            "Provide a friendly, concise answer based on these database results."
        )

        res2 = client.chat.completions.create(
            model="nvidia/nemotron-3-super-120b-a12b:free",
            messages=[{"role": "user", "content": synth_prompt}],
            temperature=0.7,
        )

        # Defensive checks for AI2 response
        if not res2 or not res2.choices:
            raise HTTPException(
                status_code=502,
                detail="AI2 returned an empty response from OpenRouter.",
            )

        reply = (
            res2.choices[0].message.content or "No answer could be generated."
        )

        return {"reply": reply, "model": "cohere-to-nemotron-pipeline"}

    except SQLValidationError as err:
        raise HTTPException(
            status_code=400, detail=f"SQL Security Error: {str(err)}"
        )
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Server Error: {str(err)}")