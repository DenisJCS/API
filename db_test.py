from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime
import sqlite3
from contextlib import contextmanager
import json

app = FastAPI(title="Database Integretion Test")

#Define our data models
class LearningTopic(str, Enum):
    PYTHON = "Python"
    FASTAPI = "FastAPI"
    DATABASE = "Database"
    DOCKER = "Docker"
    AI = "AI"
    DJANGO = "Django"

class LearningUpdate:
    topic: LearningTopic
    hours_spent: float = Field(gt=0, lt=24)
    difficulty_level: int = Field(ge=1, le=5)
    notes: str = Field(min_length=10)
    understanding_level: int = Field(ge=1, le=10)
    question: Optional[List[str]] = []


# Database connection manager
@contextmanager
def get_db_connection():
    """Create and manage a database connection"""
    # This patterns ensures the connection properly closed even if an error occurs
    conn = sqlite3.connect('test_learning.db')
    try:
        # The yieald statement is what makes this a contextmanager
        # It temporarily gives control back to the caller
        yield conn 
    finally:
        # This code always runs when context ends, ensuring connection closure
        conn.close()

# Initialize database
def init_db():
    """Create the database tables if they don't exist"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE A TABLE IF NOT EXIST learning_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                hours_spent REAL NOT NULL,
                difficulty_level INTEGER NOT NULL,
                notes TEXT NOT NULL,
                understanding_level INTEGER NOT NULL,
                questions TEXT,
                timestamp TEXT NOT NULL
            )
        ''')
        conn.commit()

# Call init_db when the application starts 
@app.on_event("startup")
async def startup_event():
    init_db()


# Endpoints
@app.post("/add-progress")
async def add_learning_progress(update: LearningUpdate):
    """Add a new learning progress entry to the database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

        # SQLite doesn't have a native JSON type, so we convert lists to JSON string
        questions_json = json.dumps(update.question)

        cursor.execute('''
            INSERT INTO learning_updates
            ( topic, hours_spent, difficulty_level, notes, understanding_level, timestamp) 
            VALUES (?, ?, ?, ?, ?, ?,)
            RETURNING id
        ''', (
            update.topic,
            update.hours_spent,
            update.difficulty_level,
            update.notes,
            update.understanding_level,
            questions_json,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        # Get the ID of the newly inserted row
        new_id = cursor.fetchone()[0]
        conn.commit()

        return {
            "message": "Progress updated successfully!",
            "data": {**update.model_dupm(), "id": new_id}
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/view-progress")
async def view_progress():
    """Retrieve all learning progress entries"""
    with get_db_connection as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM learning_updates')
        rows = cursor.fetchall()

        entries = []
        for row in rows:
            # Convert SQLite row to dictionary
            entry = {
                "id": row[0],
                "topic": row[1],
                "hours_spent": row[2],
                "difficulty_level": row[3],
                "notes": row[4],
                "understanding_level": row[5],
                "questions": json.loads(row[6]) if row[6] else [],
                "timestamp": row[7]
            }
            entries.append(entry)

        return {
            "total_entries": len(entries),
            "total_hours": sum(entry["hours_spent"] for entry in entries),
            "entries": entries 
        }       
                       
                       
                       
                       
                       
                       
