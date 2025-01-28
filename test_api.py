
from fastapi.testclient import TestClient
from learning_api import app # Importing our main FastAPI app
import pytest 

#Create test client
client = TestClient(app)

#Our first test function
def test_add_learning_progress():
    """Test adding a new learning progress entry"""
    test_data = {
        "topic": "Python", # using our LearningTopic enum
        "hours_spent": 2.5, # valid hourse (between 0-24)
        "difficulty_level": 3, # valid level (1-5)
        "notes": "Learning FastAPI testint", # more than 10 charts
        "understanding_level": 8, # valid level (1-10)
        "questions": ["How do we handle test database?"]
    }

    response = client.post("/add-progress", json=test_data) 
    assert response.status_code == 200 # Check if request was successful
    assert "Progress update successfully !" in response.json()["message"]
      
