import sqlite3
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from validator import SQLValidationError, validate_sql_query

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# Configure the OpenAI client to use OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

class ChatRequest(BaseModel):
    prompt: str

@app.post("/api/chat")
def chat(req: ChatRequest):
    try:
        # Step 1: AI1 generates SQL (Temperature 0 for determinism)
        sql_prompt = f"You are a SQLite expert. Convert this request to a SQL query for the table 'draws' (columns: date_de_tirage, boule_1, boule_2, boule_3, boule_4, boule_5, numero_chance). Return ONLY the raw SQL query, nothing else. Request: {req.prompt}"
        
        res1 = client.chat.completions.create(
            model="thinkingmachines/inkling-small:free",
            messages=[{"role": "user", "content": sql_prompt}],
            temperature=0.0,
        )
        
        # Clean markdown formatting if AI1 includes it
        raw_sql = res1.choices[0].message.content.strip().replace("```sql", "").replace("```", "")
        
        # Step 2: Validate & Execute
        safe_sql = validate_sql_query(raw_sql)
        conn = sqlite3.connect("fdj_draws.db")
        cursor = conn.cursor()
        cursor.execute(safe_sql)
        db_results = cursor.fetchall()
        conn.close()

        # Step 3: AI2 Synthesizes the final answer
        synth_prompt = f"The user asked: '{req.prompt}'. The database returned this data: {db_results}. Write a brief, friendly response answering their question."
        
        res2 = client.chat.completions.create(
            model="nvidia/nemotron-3-super-120b-a12b:free",
            messages=[{"role": "user", "content": synth_prompt}],
            temperature=0.7,
        )

        return {
            "reply": res2.choices[0].message.content,
            "model": "inkling-to-nemotron-pipeline"
        }

    except SQLValidationError as err:
        raise HTTPException(status_code=400, detail=f"SQL Security Error: {str(err)}")
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Server Error: {str(err)}")