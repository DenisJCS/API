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

# Test view-progress endpoint
def test_view_progress():
    """Test the endpoint that shows all learning progress"""
    #first, let's get all progress entries
    response = client.get("view-progress")
    
    #Basic checks
    assert response.status_code == 200 #check if request succeeded

    #Get the response data
    data = response.json()

    # Check if response has all required fields
    assert "total_entries" in data, "Response should have total_entries field"
    assert "total_hours" in data, "Response should have total_hours field"
    assert "entries" in data, "Response should have entries field"

    #Check data types
    assert isinstance(data["entries"], list), "Entries should be a list"
    assert isinstance(data["total_hours"], (int,float)), "Total hours should be a number "
    assert isinstance(data["total_entries"], int), "Total entries should be integer"

    # If there are entries check first entry structured
    if data["entries"]:
        first_entry = data["entries"][0]
        assert "topic" in first_entry, "Entry should have topic"
        assert "hours_spent" in first_entry, "Entry should have hours_spent"
        assert "understanding_level" in first_entry, "Entry should have understanding_level"

def test_update__progress():
    """The updating an existing learning entry"""
    # Frist creat an entry
    initial_data = {
        "topic": "Python",
        "hours_spent": 2.0,
        "difficulty_level": 3,
        "notes": "Initial learning session",
        "understanding_level": 7,
        "questions": []
    }
    create_response = client.post("/add-progress", json=initial_data)
    entry_id = create_response.json()["data"]["id"]

    # Nos update some fields
    update_data = {
        "hours_spent": 3.0,
        "notes": "Updated learning session notes"
    }

    response = client.put(f"/update-progress/{entry_id}", json=update_data)
    assert response.status_code == 200

    #Check if only specified fields were updates
    updated_data = response.json()["data"]
    assert updated_data["hours_spent"] == 3.0
    assert updated_data["notes"] == "Updated learning session notes"
    assert updated_data["topic"] == "Python" # Should remain unchange

def test_delete_progress():
    """Test delete a learning entry"""
    #First create an entry to delete
    initial_data = {
        'topic':'Python',
        'hours_spent': 2.0,
        'difficulty_level': 3,
        'notes': 'Testing delete functionality',
        'understanding_level' : 7,
        'questions': []
}
    
    # Add the entry and get its ID
    create_response = client.post('/add-progress', json=initial_data)
    entry_id = create_response.json()['data']['id']

    # Try to delete the entry
    delete_response = client.delete(f'/delete-progress/{entry_id}')
    assert delete_response.status_code == 200
    assert f'Entry {entry_id} deleted successfully !' in delete_response.json()['message']

    # Verify entry is gone by trying view it
    verify_response = client.get(f'/view-progress/{entry_id}')
    assert verify_response.status_code == 404 #Should return not found




def test_simple_lifecycle():
    '''Test an entry's complete journey in our system'''

    # Step 1 : Create a new entry
    new_entry = {
        'topc': 'Python',
        'hours_spent': 2.0,
        'difficulty_level': 3,
        'notes': 'First test note',
        'questions': []
    }

    # Save it and get its ID number
    response = client.post('/add-progress', json=new_entry)
    entry_id = response.json()['data']['id']

    # Step 2: Check if it's saved correctly
    check_response = client.get('/view-progress')
    assert check_response.status_code == 200

    # Step 3: Change something
    changes = {
        'hours_spent' : 3.0,
        'notes' : 'Change test note'
    }
    client.put(f'/update-progress/{entry_id}', json=changes)

    # Step 4: Delete it
    delete_response = client.delete(f'/delete-progress/{entry_id}')
    assert f'Entry {entry_id} deleted successfully !' in delete_response.json()['message'] 
    

% pytest
============================================ test session starts ============================================
platform darwin -- Python 3.12.3, pytest-8.3.4, pluggy-1.5.0
rootdir: /Users/denis_jcs/Documents/Intensive2
plugins: anyio-4.8.0
collected 3 items                                                                                           

test_api.py ...                                                                                       [100%]

============================================= warnings summary ==============================================
test_api.py::test_add_learning_progress
test_api.py::test_update__progress
  /Users/denis_jcs/Documents/Intensive2/learning_api.py:130: PydanticDeprecatedSince20: The `dict` method is deprecated; use `model_dump` instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.10/migration/
    "data": {**update.dict(), "id": new_id}

test_api.py::test_update__progress
  /Users/denis_jcs/Documents/Intensive2/learning_api.py:149: PydanticDeprecatedSince20: The `dict` method is deprecated; use `model_dump` instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.10/migration/
    update_dict = update.dict(exclude_unset=True)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================================= 3 passed, 3 warnings in 0.19s =======================================
