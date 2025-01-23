# 1 Imports
from fastapi import FastAPI, HTTPException
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional,Dict, Any
from enum import Enum
import sqlite3 # This is our databese engine
from contextlib import contextmanager
import json # We will need this to handle lists in SQLite

# 2 App initialization 
app = FastAPI()


# 3 Database connection manager

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('learning_progress.db')
    try:
        yield conn
    finally:
        conn.close()


# 4 MODELS
#Define valid topic (это определяет допустимые темы)
class LearningTopic(str, Enum):
    PYTHON = "Python"
    FASTAPI = "FastAPI"
    DATABASE = "Database"
    DOCKER = "Docker"
    AI = "AI"
    DJANGO = "Django"

#Enhance data validation ( улучшенная валидация данных)
class LearningUpdate(BaseModel):
    topic: LearningTopic #No only acctepts prefered topic
    hours_spent: float = Field(gt=0, lt=24) # Must be between 0 and 24
    difficulty_level: int = Field(ge=1, le=5) # Must be between 1 and 5
    notes: str = Field(min_length=10) # Notes must be meaningfull 
    understanding_level : int = Field(ge=1 , le=10) # Scale of 1-10
    questions: Optional[List[str]] = [] # Any questions you have 

class LearningUpdatePatch(BaseModel):
    topic: Optional[LearningTopic] = None
    hours_spent: Optional[float] = Field(None, gt=0, lt=24)
    difficulty_level: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = Field(None, min_length=10)
    understanding_level: Optional[int] = Field(None, ge=1, le=10)
    questions: Optional[List[str]] = None

# 5 Initialize database

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS learning_updates(
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

# Call init.db at startup
init_db()


# 6 ENDPOINTS Update POST endpoint to use database

@app.get("/view-progress")
def view_all_progress() -> Dict[str, Any]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM learning_updates')
        rows = cursor.fetchall()
        entries = []
        for row in rows:
            entry = {
                "id": row[0],
                "topic":row[1],
                "hours_spent":row[2],
                "difficulty_level":row[3],
                "notes":row[4],
                "understanding_level":row[5],
                "questions": json.loads(row[6]) if row[6] else [],
                "timestamp": row[7]
            }
            entries.append(entry)

        return {
            "total_entries": len(entries),
            "total_hours": sum(entry["hours_spent"] for entry in entries),
            "entries": entries
        }
    


@app.post("/add-progress")
def add_learning_progress(update: LearningUpdate):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            questions_json = json.dumps(update.questions)
            cursor.execute('''
                INSERT INTO learning_updates
                (topic, hours_spent, difficulty_level, notes, understanding_level, questions, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                update.topic,
                update.hours_spent,
                update.difficulty_level,
                update.notes,
                update.understanding_level,
                questions_json,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()
            return{
                "message": "Progress updated successfully!",
                "data": update.dict()                   
            }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@app.put("/update-progress/{entry_id}")
def update_learning_progress(entry_id: int, update: LearningUpdatePatch):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # First check if entry exists
            cursor.execute('SELECT * FROM learning_updates WHERE id = ?', (entry_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Entry not found")
            
            # Build entry update query dynamicly based on provided fiels
            update_dict = update.dict(exclude_unset=True)
            if not update_dict:
                raise HTTPException(status_code=404, detail="No fields to update")
            
            # Handle questions list speacially
            if 'questions' in update_dict:
                update_dict['questions'] = json.dumps(update_dict['questions'])

            # Construct SQL querry
            set_values = [f"{k} = ?" for k in update_dict]
            query = f'''
                UPDATE learning_updates
                SET {', '.join(set_values)}
                WHERE id = ?
            '''

            # Execute update
            cursor.execute(query, list(update_dict.values()) + [entry_id])
            conn.commit()

            # Return update entry
            cursor.execute('SELECT * FROM learning_updates WHERE id = ?', (entry_id,))
            row = cursor.fetchone()

            return {
                "message": "Progress update successfully!",
                "data": {
                    "id": row[0],
                    "topic": row[1],
                    "hours_spent": row[2],
                    "difficulty_level": row[3],
                    "notes": row[4],
                    "understanding_level": row[5],
                    "questions": json.loads(row[6]) if row[6] else [],
                    "timestamp": row[7]
                }
            }
                                
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@app.delete("/delete-progress/{entry_id}")
def delete_learning_progress(entry_id: int):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            #First check if entry exist
            cursor.execute('SELECT * FROM learning_updates WHERE id = ?', (entry_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail = "Entry form not found")
            
            #Delete the entry
            cursor.execute('DELETE FROM learning_updates WHERE id = ?', (entry_id,))
            conn.commit()

            return {
                "message": f"Entry {entry_id} deleted successfully !",
                "deleted_id": entry_id
            }

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    

@app.get("/view-progress/by-topic/{topic}")
def get_progress_by_topic(topic: str):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(''' SELECT * FROM learning_updates WHERE topic = ?''',(topic,))
            
            rows = cursor.fetchall()
            if not rows:
                raise HTTPException(status_code=404, detail=f"No entries found for topic:{topic} ")
            
            entries = []
            for row in rows:
                entry = {
                    "id": row[0],
                    "topic": row[1],
                    "hourse_spent": [2],
                    "difficulty_level": [3],
                    "notes": [4],
                    "understanding_level": [5],
                    "questions": json.loads(row[6]) if row[6] else [],
                    "timestamp": row[7]
                }
                entries.append(entry)

            
            return {
                "topic":topic,
                "total_entries": len(entries),
                "total_hours": sum(entry["hours_spent"] for entry in entries),
                "entries": entries 
            }

    except Exception as e:
        raise HTTPException(status_code= 404, detail=str(e))
    
# This function will set up our database
def init_db():
    conn = sqlite3.connect('learning_progress.db')
    cursor = conn.cursor()

    #Created a table to store our learning updates
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS learning_updates (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   topic   TEXT NOT NULL,
                   hours_spent REAL NOT NULL,
                   difficulty_level INTEGER NOT NULL,
                   notes TEXT NOT NULL,
                   understanding_level INTEGER NOT NULL,
                   questions TEXT,
                   timestamp TEXT NOT NULL
                   )
            ''')
    
    conn.commit()
    conn.close()



# This one worked because we simplified code so much so it redeems raw data and now I can add the rest of code 
@app.get("/view-progress/by-topic/{topic}")
def get_progress_by_topic(topic: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            # Simple query first
            cursor.execute(''' SELECT * FROM learning_updates WHERE topic = ?''',(topic,))
            rows = cursor.fetchall()
            
           
            # Just return raw data firtst to see what we're getting
            return {
                "topic":topic,
                "raw_data": [list(row) for row in rows] 
            }

        except Exception as e:
            raise HTTPException(status_code= 404, detail=str(e))
    
# Maybe will not work lol 
# 1 Imports
from fastapi import FastAPI, HTTPException
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional,Dict, Any
from enum import Enum
import sqlite3 # This is our databese engine
from contextlib import contextmanager
import json # We will need this to handle lists in SQLite

# 2 App initialization 
app = FastAPI()


# 3 Database connection manager

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('learning_progress.db')
    try:
        yield conn
    finally:
        conn.close()


# 4 MODELS
#Define valid topic (это определяет допустимые темы)
class LearningTopic(str, Enum):
    PYTHON = "Python"
    FASTAPI = "FastAPI"
    DATABASE = "Database"
    DOCKER = "Docker"
    AI = "AI"
    DJANGO = "Django"

#Enhance data validation ( улучшенная валидация данных)
class LearningUpdate(BaseModel):
    topic: LearningTopic #No only acctepts prefered topic
    hours_spent: float = Field(gt=0, lt=24) # Must be between 0 and 24
    difficulty_level: int = Field(ge=1, le=5) # Must be between 1 and 5
    notes: str = Field(min_length=10) # Notes must be meaningfull 
    understanding_level : int = Field(ge=1 , le=10) # Scale of 1-10
    questions: Optional[List[str]] = [] # Any questions you have 

class LearningUpdatePatch(BaseModel):
    topic: Optional[LearningTopic] = None
    hours_spent: Optional[float] = Field(None, gt=0, lt=24)
    difficulty_level: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = Field(None, min_length=10)
    understanding_level: Optional[int] = Field(None, ge=1, le=10)
    questions: Optional[List[str]] = None

# 5 Initialize database

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS learning_updates(
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

# Call init.db at startup
init_db()


# 6 ENDPOINTS Update POST endpoint to use database

@app.get("/view-progress")
def view_all_progress() -> Dict[str, Any]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM learning_updates')
        rows = cursor.fetchall()
        entries = []
        for row in rows:
            entry = {
                "id": row[0],
                "topic":row[1],
                "hours_spent":row[2],
                "difficulty_level":row[3],
                "notes":row[4],
                "understanding_level":row[5],
                "questions": json.loads(row[6]) if row[6] else [],
                "timestamp": row[7]
            }
            entries.append(entry)

        return {
            "total_entries": len(entries),
            "total_hours": sum(entry["hours_spent"] for entry in entries),
            "entries": entries
        }
    


@app.post("/add-progress")
def add_learning_progress(update: LearningUpdate):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            questions_json = json.dumps(update.questions)
            cursor.execute('''
                INSERT INTO learning_updates
                (topic, hours_spent, difficulty_level, notes, understanding_level, questions, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                update.topic,
                update.hours_spent,
                update.difficulty_level,
                update.notes,
                update.understanding_level,
                questions_json,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()
            return{
                "message": "Progress updated successfully!",
                "data": update.dict()                   
            }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@app.put("/update-progress/{entry_id}")
def update_learning_progress(entry_id: int, update: LearningUpdatePatch):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # First check if entry exists
            cursor.execute('SELECT * FROM learning_updates WHERE id = ?', (entry_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Entry not found")
            
            # Build entry update query dynamicly based on provided fiels
            update_dict = update.dict(exclude_unset=True)
            if not update_dict:
                raise HTTPException(status_code=404, detail="No fields to update")
            
            # Handle questions list speacially
            if 'questions' in update_dict:
                update_dict['questions'] = json.dumps(update_dict['questions'])

            # Construct SQL querry
            set_values = [f"{k} = ?" for k in update_dict]
            query = f'''
                UPDATE learning_updates
                SET {', '.join(set_values)}
                WHERE id = ?
            '''

            # Execute update
            cursor.execute(query, list(update_dict.values()) + [entry_id])
            conn.commit()

            # Return update entry
            cursor.execute('SELECT * FROM learning_updates WHERE id = ?', (entry_id,))
            row = cursor.fetchone()

            return {
                "message": "Progress update successfully!",
                "data": {
                    "id": row[0],
                    "topic": row[1],
                    "hours_spent": row[2],
                    "difficulty_level": row[3],
                    "notes": row[4],
                    "understanding_level": row[5],
                    "questions": json.loads(row[6]) if row[6] else [],
                    "timestamp": row[7]
                }
            }
                                
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@app.delete("/delete-progress/{entry_id}")
def delete_learning_progress(entry_id: int):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            #First check if entry exist
            cursor.execute('SELECT * FROM learning_updates WHERE id = ?', (entry_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail = "Entry form not found")
            
            #Delete the entry
            cursor.execute('DELETE FROM learning_updates WHERE id = ?', (entry_id,))
            conn.commit()

            return {
                "message": f"Entry {entry_id} deleted successfully !",
                "deleted_id": entry_id
            }

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    

@app.get("/view-progress/by-topic/{topic}")
def get_progress_by_topic(topic: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM learning_updates WHERE topic = ?', (topic,))
            rows = cursor.fetchall()
            
            if not rows:
                raise HTTPException(status_code=404, detail=f"No entries found for topic: {topic}")
            
            entries = []
            total_hours = 0
            total_difficulty = 0
            
            for row in rows:
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
                total_hours += row[2]  # hours_spent
                total_difficulty += row[3]  # difficulty_level

            return {
                "topic": topic,
                "total_entries": len(entries),
                "total_hours": total_hours,
                "average_difficulty": round(total_difficulty / len(entries), 2),
                "entries": entries
            }
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        

@app.get("analytics/learning-summary")
def get_learning_summary():
    """
    Provides a comprehensive summary of your learning progress.
    This endpoint helps you understand your learning patterns and achievements.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # First, let's get you overall study metrics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_session,          -- row[0]
                SUM(hours_spent) as total_hours,    -- row[1]
                AVG(understanding_level) as avg_understanding       -- row[2]
            FROM learning_updates
            WHERE timestamp => date('now', '-30 days')
        ''')
        recent_status = cursor.fetchone()

        # Now lets analyze your progress by topic
        cursor.execute('''

            SELECT
                topic,                              -- row[0]
                COUNT(*) as study_session,          -- row[1]
                SUM(hours_spent) as hours_invested, -- row[2]
                AVG(understanding_level) as current_understanding,      -- row[3]
                MAX(timestamp) as last_studied      -- row[4]
            FROM learning_updates
            GROUP BY topic
            ORDER BY hours_invested DESC
        ''')
        topic_breakdown = cursor.fetchall()

        # Let's create more descriptive names for our indices
        TOPIC = 0
        SESSIONS = 1
        HOURS = 2
        UNDERSTANDING = 3
        LAST_STUDIED = 4


        return {
            "recent_progress":{
                "study_session_last_30_days": recent_status[0],
                "total_hours_invested": round(recent_status[1], 2),
                "average_understanding_level": round(recent_status[2], 2)
            },
            "topic_analysis": [
                {
                    "topic": row[TOPIC],
                    "total_session": row[SESSIONS],
                    "hours_ivested": row[HOURS, 2],
                    "understanding_lever": round(row[UNDERSTANDING], 2),
                    "last_studied": row[LAST_STUDIED]
                }
                for row in topic_breakdown
            ] 
        }
    
# This function will set up our database
def init_db():
    conn = sqlite3.connect('learning_progress.db')
    cursor = conn.cursor()

    #Created a table to store our learning updates
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS learning_updates (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   topic   TEXT NOT NULL,
                   hours_spent REAL NOT NULL,
                   difficulty_level INTEGER NOT NULL,
                   notes TEXT NOT NULL,
                   understanding_level INTEGER NOT NULL,
                   questions TEXT,
                   timestamp TEXT NOT NULL
                   )
            ''')
    
    conn.commit()
    conn.close()

# Issue 404 cant get data , code below is simpified version of this endpoint . It worked but not as we needed
@app.get("/analytics/learning-summary")
def get_learning_summary():
    """
    Provides a comprehensive summary of your learning progress.
    This endpoint helps you understand your learning patterns and achievements.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # The simpliest possible query - just selecting a single value
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            

            return{
                "total_entries": result[0],
                "message": "Basic conntection test successful"
            }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error recieving learning summary : {str(e)}")
    
