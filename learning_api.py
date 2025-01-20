from fastapi import FastAPI
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

app = FastAPI()

#Define our data structure 
class LearningUpdage(BaseModel):
    topic : str  # what you are learning
    hours_spent : float # how long you studied
    difficulty_level : int # how hard was it
    notes : str

# Store our learning updates (we will use data base later)
learning_updates = []

@app.post("/add_progress")
def add_learning_progress(update: LearningUpdage):
    update_with_timestamp = {
        **update.dict(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    }
    learning_updates.append(update_with_timestamp)
    return{
        "message" : "Progress update successfully!",
        "data" : update_with_timestamp
    }
@app.get("/view_progress")
def view_all_progress():
    return learning_updates
