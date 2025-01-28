

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
        "notes": "Learning FastAPI testing", # more than 10 charts
        "understanding_level": 8, # valid level (1-10)
        "questions": ["How do we handle test database?"]
    }

    response = client.post("/add-progress", json=test_data) 
    assert response.status_code == 200 # Check if request was successful
    assert "Progress updated successfully!" in response.json()["message"]

Intensive2 % python -m pytest test_api.py -v
========================================== test session starts ==========================================
platform darwin -- Python 3.12.3, pytest-8.3.4, pluggy-1.5.0 -- /Users/denis_jcs/Documents/Intensive2/venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/denis_jcs/Documents/Intensive2
plugins: anyio-4.8.0
collected 1 item                                                                                        

test_api.py::test_add_learning_progress PASSED                                                    [100%]

=========================================== warnings summary ============================================
test_api.py::test_add_learning_progress
  /Users/denis_jcs/Documents/Intensive2/learning_api.py:128: PydanticDeprecatedSince20: The `dict` method is deprecated; use `model_dump` instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.10/migration/
    "data": update.dict()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
===================================== 1 passed, 1 warning in 0.22s ======================================
