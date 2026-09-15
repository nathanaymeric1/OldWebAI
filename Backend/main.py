import sqlite3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS for Eleventy frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/test-db")
def test_db():
    conn = sqlite3.connect("fdj_draws.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT date_de_tirage, boule_1, boule_2, boule_3, boule_4, boule_5 FROM draws LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    return {"status": "success", "sample_row": row}