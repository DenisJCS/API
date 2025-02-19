from fastapi import FastAPI
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from enum import Enum

class LearningTopic(str, Enum):
    PYTHON = "Python"
    FASTAPI = "FastAPI"
    DATABASE = "Database"
    DOCKER = "Docker"
    AI = "AI"
    DJANGO = "Django"

class LearningUpdate(BaseModel):
    topic: LearningTopic
    hours_spent:float = Field(gt=0, lt=24)
    difficulty_level: int = Field(ge=1, le=10)
    notes: str = Field(min_length=10)
    understanding_level = int = Field(ge = 1, le = 10)
    questions = Optional[List[str]] = []

app = FastAPI(
    title = "Learning Progress Tracker",
    description = "Track your programming learning journey"
)

@app.post("/add-progress")
async def add_learning_progress(update: LearningUpdate):
    """Record a new learning session"""
    return {
        "message": "Progress updated successully!",
        "data": update 
    }

@app.get("/view-progress")
async def view_progress():
    """View all learning progress"""
    #We'll add database integration here later
    return {"message": "This will show your learning progress"}
