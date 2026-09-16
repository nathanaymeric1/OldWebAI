from typing import List
from pydantic import BaseModel

MAX_PROMPT_LENGTH = 500

class Message(BaseModel):
    role: str
    content: str

def sanitize_user_input(prompt: str) -> str:
    clean = prompt.strip()
    if not clean:
        raise ValueError("Prompt cannot be empty.")
    if len(clean) > MAX_PROMPT_LENGTH:
        raise ValueError(
            f"Prompt exceeds maximum allowed length of {MAX_PROMPT_LENGTH} characters."
        )
    return clean

def build_contextual_sql_prompt(user_prompt: str, history: List[Message]) -> str:
    recent_history = history[-6:] if history else []
    history_str = (
        "\n".join([f"{m.role.upper()}: {m.content}" for m in recent_history])
        if recent_history
        else "No prior context."
    )

    return f"""
You are a SQLite expert translating natural language into SQL for a French Loto (FDJ) database.
Table 'draws' columns: date_de_tirage, boule_1, boule_2, boule_3, boule_4, boule_5, numero_chance.

CONVERSATION HISTORY (Read this to resolve follow-up questions):
{history_str}

CURRENT REQUEST:
USER: {user_prompt}

INSTRUCTIONS:
1. Treat CURRENT REQUEST as a continuation of CONVERSATION HISTORY. If they ask for "the next five", apply a new OFFSET or LIMIT based on their previous request.
2. Output ONLY the valid SQLite SELECT query.
3. ONLY if the CURRENT REQUEST is completely unrelated to the database (e.g., asking for weather, poetry, or unsupported lotteries), output exactly: NO_SQL_NEEDED.
4. Do not explain, do not add markdown wrapping. Output raw SQL only.
"""