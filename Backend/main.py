import os
import sqlite3
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel
from sanitizer import Message, build_contextual_sql_prompt, sanitize_user_input
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
    history: Optional[List[Message]] = []


def update_conversation_context_async(user_prompt: str, ai_response: str):
    """Background task: Updates rolling context summaries asynchronously."""
    try:
        summary_prompt = (
            f"Summarize this interaction for session context: User asked '{user_prompt}', AI replied '{ai_response}'."
        )
        client.chat.completions.create(
            model="nvidia/nemotron-3-super-120b-a12b:free",
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.3,
        )
    except Exception:
        pass


@app.post("/api/chat")
def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    try:
        clean_prompt = sanitize_user_input(req.prompt)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

    # Pass user prompt AND history array to build the contextual prompt for AI1
    sql_prompt = build_contextual_sql_prompt(clean_prompt, req.history)
    
    res1 = client.chat.completions.create(
        model="cohere/north-mini-code:free",
        messages=[{"role": "user", "content": sql_prompt}],
        temperature=0.0,
    )
    
    raw_sql = (res1.choices[0].message.content or "").strip()
    
    # Handle Trick Questions / Guardrail Intercept
    if "NO_SQL_NEEDED" in raw_sql:
        reply = "I can only answer questions regarding official French Loto (FDJ) draw results stored in the database."
        background_tasks.add_task(update_conversation_context_async, clean_prompt, reply)
        return {"reply": reply, "model": "guardrail-intercept"}
    
    try:
        safe_sql = validate_sql_query(raw_sql)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(safe_sql)
        db_results = cursor.fetchall()
        conn.close()

        synth_prompt = (
            f"User asked: '{clean_prompt}'. Database query returned: {db_results if db_results else 'No records found'}. "
            "Formulate a precise, natural response. If results are empty, inform the user gracefully."
        )

        res2 = client.chat.completions.create(
            model="nvidia/nemotron-3-super-120b-a12b:free",
            messages=[{"role": "user", "content": synth_prompt}],
            temperature=0.7,
        )

        reply = res2.choices[0].message.content or "No synthesis could be generated."

        background_tasks.add_task(update_conversation_context_async, clean_prompt, reply)

        return {"reply": reply, "model": "cohere-to-nemotron-pipeline"}

    except SQLValidationError as err:
        raise HTTPException(status_code=400, detail=f"SQL Security Error: {str(err)}")
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Server Error: {str(err)}")