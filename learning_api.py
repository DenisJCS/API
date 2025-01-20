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



# This is modified API with terms for Post and updates
from fastapi import FastAPI, HTTPException
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from typing import Dict, Any

app = FastAPI()


#Define valid topic (это определяет допустимые темы)
class LearningTopic(str, Enum):
    PYTHON = "Python"
    FASTAPI = "FastAPI"
    DATABASE = "Database"
    DOCKER = "Docker"
    AI = "AI"

#Enhance data validation ( улучшенная валидация данных)
class LearningUpdate(BaseModel):
    topic: LearningTopic #No only acctepts prefered topic
    hours_spent: float = Field(gt=0, lt=24) # Must be between 0 and 24
    difficulty_level: int = Field(ge=1, le=5) # Must be between 1 and 5
    notes: str = Field(min_length=10) # Notes must be meaningfull 
    understanding_level : int = Field(ge=1 , le=10) # Scale of 1-10
    questions: Optional[List[str]] = [] # Any questions you have 

# Store our updated
learning_updates = []

@app.post("/add-progress")
def add_learning_progress(update: LearningUpdate):
    try:
        update_with_timestamp = {
            **update.dict(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        learning_updates.append(update_with_timestamp)
        return{
            "message": "Progress updated successfully!",
            "data": update_with_timestamp
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/view-progress")
def view_all_progress() -> Dict[str, Any]:
    return {
        "total_entries": len(learning_updates),
        "total_hours": sum(update["hours_spent"] for update in learning_updates),
        "entries": learning_updates
    }

#Added topic-specific endpoint
@app.get("/topic/{topic}")
def get_topic_progress(topic: LearningTopic):
    topic_updates = [u for u in learning_updates if u["topic"] == topic]
    return {
        "topic":topic, 
        "total_hours" : sum(update["hours_spent"] for update in topic_updates),
        "entries": topic_updates
    }

