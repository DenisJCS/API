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
            new_id = cursor.fetchone()[0]
            conn.commit()
            return {
                "message": "Progress updated successfully!",
                "data": {**update.model_dump(), "id": new_id}                   
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
            update_dict = update.model_dump(exclude_unset=True)
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
        

@app.get("/analytics/learning-summary")
def get_learning_summary():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # First, let's get a sample row to understand our data structure
            cursor.execute("SELECT * FROM learning_updates LIMIT 1")
            sample = cursor.fetchone()
            print(f"Sample row structure: {sample}")  # This helps us see column order
            
            # Now get all entries
            cursor.execute("""
                SELECT id, topic, hours_spent, difficulty_level, 
                       understanding_level, notes, questions, timestamp 
                FROM learning_updates
            """)
            all_data = cursor.fetchall()
            
            # Initialize our tracking variables
            topics = {}
            total_hours = 0
            
            # Process each entry carefully
            for entry in all_data:
                # Unpack our data with clear names
                id, topic, hours, difficulty, understanding, notes, questions, timestamp = entry
                
                # Convert numeric values safely
                try:
                    hours = float(hours)
                    understanding = float(understanding)
                except (ValueError, TypeError):
                    print(f"Warning: Invalid number format in entry {id}")
                    continue
                
                # Track statistics for this topic
                if topic not in topics:
                    topics[topic] = {
                        "total_hours": 0.0,
                        "sessions": 0,
                        "total_understanding": 0.0,
                        "entries": []
                    }
                
                # Update our counters
                topics[topic]['total_hours'] += hours
                topics[topic]['sessions'] += 1
                topics[topic]['total_understanding'] += understanding
                topics[topic]['entries'].append({
                    "date": timestamp,
                    "hours": hours,
                    "understanding": understanding
                })
                total_hours += hours
            
            # Create our statistics summary
            topic_stats = []
            for topic, stats in topics.items():
                avg_understanding = (stats['total_understanding'] / 
                                  stats['sessions']) if stats['sessions'] > 0 else 0
                topic_stats.append({
                    'topic': topic,
                    'total_hours': round(stats['total_hours'], 2),
                    'number_of_sessions': stats['sessions'],
                    'average_understanding': round(avg_understanding, 2)
                })
            
            # Sort topics by total hours spent (most to least)
            topic_stats.sort(key=lambda x: x['total_hours'], reverse=True)
            
            return {
                'summary': {
                    'total_entries': len(all_data),
                    'total_hours': round(total_hours, 2),
                    'unique_topics': len(topics),
                    'most_studied_topic': topic_stats[0]['topic'] if topic_stats else None
                },
                'topic_statistics': topic_stats
            }
            
    except Exception as e:
        print(f"Error details: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"Error receiving learning summary: {str(e)}"
        )
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


