import csv
import sqlite3
from datetime import datetime

# Connect (or create) database
conn = sqlite3.connect("fdj_draws.db")
cursor = conn.cursor()

# 1. Create clean table structure
cursor.execute("DROP TABLE IF EXISTS draws")
cursor.execute("""
    CREATE TABLE draws (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_de_tirage DATE,
        jour_de_tirage TEXT,
        boule_1 INTEGER,
        boule_2 INTEGER,
        boule_3 INTEGER,
        boule_4 INTEGER,
        boule_5 INTEGER,
        numero_chance INTEGER
    )
""")

# 2. Parse CSV and insert clean rows
with open("loto_201911.csv", mode="r", encoding="utf-8") as file:
    reader = csv.DictReader(file, delimiter=";")
    for row in reader:
        # Convert date DD/MM/YYYY -> YYYY-MM-DD
        raw_date = row["date_de_tirage"]
        formatted_date = datetime.strptime(raw_date, "%d/%m/%Y").strftime("%Y-%m-%d")

        cursor.execute("""
            INSERT INTO draws (date_de_tirage, jour_de_tirage, boule_1, boule_2, boule_3, boule_4, boule_5, numero_chance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            formatted_date,
            row["jour_de_tirage"],
            int(row["boule_1"]),
            int(row["boule_2"]),
            int(row["boule_3"]),
            int(row["boule_4"]),
            int(row["boule_5"]),
            int(row["numero_chance"])
        ))

conn.commit()
conn.close()
print("Database populated successfully!")