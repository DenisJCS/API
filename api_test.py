from fastapi import FastAPI
from datetime import datetime 

app = FastAPI()

@app.get("/")
def hello_disa():
    return {"message": "Hello Disa"}

@app.get("/skills")
def my_skills():
    return{
        "python":"learning",
        "apis": "starting",
        "goal": "full developer"
    }

@app.get("/progress")
def learning_progress():
    return{
        "days_learning": 1,
        "current_topic": "FastAPI",
        "completed_topic": [
            "Python basics",
            "Functions",
            "Web basics"
        ],
        "next_topics": [
            "Database",
            "Authentication",
            "Docker"
        ]
    }

@app.get("/status")
def check_status():
    return{
        "user": "Disa",
        "status": "Learning APIs",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "active_endpoints": ["/", "/skills", "/progress", "/status"]
    }
