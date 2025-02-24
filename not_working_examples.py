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




"""This version worked and got data I wanted it to work with """
@app.get("/analytics/learning-summary")
def get_learning_summary():
   
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # The simpliest possible query - just selecting a single value
            cursor.execute("SELECT COUNT(*) FROM learning_updates")
            count_result = cursor.fetchone() #This returns a tuple like (5, )
            total_entries = count_result[0]
            
            # Then, let's get a simple first of all entries
            cursor.execute("""
                SELECT topic, hours_spent, understanding_level, timestamp
                FROM learning_updates
                ORDER by timestamp DESC
            """)
            entries = cursor.fetchall()

            # Foramt the result in a clear way
            formatted_entries = [
                {
                    "topic": entry[0],
                    "hours_spent": entry[1],
                    "understanding_level": entry[2],
                    "timestamp": entry[3]
                }
                for entry in entries
                
            ]


            return {
                "total_entries": total_entries, # Now using the correctly extracted value
                "entries": formatted_entries
                
            }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error recieving learning summary : {str(e)}")


"""New problem , need to recieve data one at the time """
@app.get("/analytics/learning-summary")
def get_learning_summary():
   
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get total entries count
            cursor.execute("SELECT COUNT(*) FROM learning_updates")
            total_entries = cursor.fetchone()[0]

            # Calculate statistic per topic
            cursor.execute("""
                SELECT
                    topic,
                    COUNT(*) as session_count,
                    SUM(hours_spent) as total_hours,
                    AVG(hours_spent) as avg_spent ,
                    AVG(understanding_level) as avg_understanding
                FROM learning_updates
                GROUP BY topic
            """)
            topic_stats = cursor.fetchall()

            # Get all entries for the detailed list
            cursor.execute("""
                SELECT topic, hours_spent, understanding_level, timestamp
                FROM learning_updates
                ORDERED BY timestamp DESC
            """)
            entries = cursor.fetchall()

            #Calculate topic statistic
            topic_summary = [
                {
                    "topic": stat[0],
                    "total_sessions": stat[1],
                    "total_hours": stat[2],
                    "average_hour_per_session": round(stat[3], 2),
                    "average_understanding": round(stat[4], 2)
                }
                for stat in topic_stats
            ]

            #Format individual entries
            formatted_entries = [
                {
                "topic": entry[0],
                "hours_spent": [1],
                "understanding_level": entry[2],
                "timestamp": entry[3]
                }
                for entry in entries 
            ]

            return {
                "summary":{
                    "total_entries": total_entries,
                    "total_hours": sum(entry[1] for entry in entries),
                    "topic_studied": len(topic_summary)
                },
                "topic_statistic": topic_summary,
                "recent_entries": formatted_entries
            }
        
""" This code worked but we recieved only  1 out of 3 , so not succesfull , but this time all 200 YEAHHH """
@app.get("/analytics/learning-summary")
def get_learning_summary():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # First, let's see what our data actually looks like
            cursor.execute("SELECT * FROM learning_updates LIMIT 1")
            sample_row = cursor.fetchone()
            print("Sample row structure:", sample_row)  # This will help us see the column order
            
            # Now get all our data
            cursor.execute("SELECT * FROM learning_updates")
            all_data = cursor.fetchall()
            
            topics = {}
            total_hours = 0
            
            for entry in all_data:
                # Instead of assuming column positions, let's print what we're working with
                print(f"Processing entry: {entry}")
                
                topic = str(entry[1])  # Topic name
                
                # We need to find the correct column for hours - let's try printing each value
                print(f"Topic: {topic}")
                print(f"Column values: {', '.join(str(x) for x in entry)}")
                
                # For now, let's skip entries where we can't convert hours to float
                try:
                    hours = float(entry[2])
                    understanding = float(entry[4])
                except (ValueError, IndexError):
                    print(f"Skipping entry due to invalid number format: {entry}")
                    continue
                
                if topic not in topics:
                    topics[topic] = {
                        "total_hours": 0.0,
                        "sessions": 0,
                        "total_understanding": 0.0
                    }
                
                topics[topic]['total_hours'] += hours
                topics[topic]['sessions'] += 1
                topics[topic]['total_understanding'] += understanding
                total_hours += hours
            
            topic_stats = [
                {
                    'topic': topic,
                    'total_hours': round(stats['total_hours'], 2),
                    'average_understanding': round(
                        stats['total_understanding'] / stats['sessions'], 
                        2
                    ) if stats['sessions'] > 0 else 0
                }
                for topic, stats in topics.items()
            ]
            
            return {
                'summary': {
                    'total_entries': len(all_data),
                    'total_hours': round(total_hours, 2),
                    'unique_topics': len(topics)
                },
                'topic_statistics': topic_stats
            }
            
    except Exception as e:
        print(f"Detailed error: {str(e)}")  # This will help us see exactly what went wrong
        raise HTTPException(
            status_code=404,
            detail=f"Error receiving learning summary: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error recieving learning summary : {str(e)}")
    
"""One more wierd"""
@app.get("/analytics/learning-summary")
def get_learning_summary():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # First, let's get a simple row to understand out data
            cursor.execute("SELECT * FROM learning_updates LIMIT 1")
            sample = cursor.fetchone()
            print("Sample row structure:", {sample})  # This will help us see the column order
            
            # Now get all our data
            cursor.execute("""
                SELECT id, topic, hours_spent, difficulty_level,
                           understanding_level, notes, questions, timestamp
                FROM learning_updates
            """)
            all_data = cursor.fetchall()
            
            # Initialize our tracking
            topics = {}
            total_hours = 0
            
            # Process each entry
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
                
                # Tracking statistic for this topic
                if topic not in topics:
                    topics[topic] = {
                        "total_hours": 0.0,
                        "sessions": 0,
                        "total_understanding": 0.0,
                        "entries": []
                    }
                
                #Update our counters
                
                topics[topic]['total_hours'] += hours
                topics[topic]['sessions'] += 1
                topics[topic]['total_understanding'] += understanding
                topics[topic]['entries'].append({
                    'date': timestamp,
                    'hours': hours,
                    'understanding': understanding
                })
            
            # Create our statistic summary
            topic_stats = []
            for topic, stats in topics.items():
                avg_understanding = (stats['total_understanding']/
                                stats['sessions']) if stats['sessions'] > 0 else 0
            topic_stats.append({
                'topic': topic,
                'total_hours': round(stats['total_hours'], 2),
                'number_of sessions': stats['sessions'],
                'average_understanding': round(avg_understanding, 2)
            })

            # Sort topics by total hours spent (most to least)
            topic_stats.sort(key=lambda x: x['total_hours'], reverse=True)

            return {
                'summary': {
                    'total_entries': len(all_data),
                    'total_hours' : round('total_hours',2),
                    'unique_topic': len(topics),
                    'most_studied_topic': topic_stats[0]['topic'] if topic_stats else None
                },
                'topic_statistic': topic_stats
            }                                  
                                  
    except Exception as e:
        print(f"Detailed error: {str(e)}")  # This will help us see exactly what went wrong
        raise HTTPException(
            status_code=404,
            detail=f"Error receiving learning summary: {str(e)}"
        )








# 1 Imports
from fastapi import FastAPI, HTTPException, Depends, status 
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from typing import List, Optional,Dict, Any, Union
from enum import Enum
import sqlite3 # This is our databese engine
from contextlib import contextmanager
import json # We will need this to handle lists in SQLite
from sqlite3 import IntegrityError

# Security configurations

SECRET_KEY = "your-secret-key-keep-it-safe" # In production, this should be seciue
ALGORITHM = "HS256" # The algorithm used to sign in the JWB tokens
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # How long tokens remains active

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") # This handles password hashing
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # This handles token authentication 

# For demostration, we'll use a simple dictionary as our user dabase
# In real application, this would be in a proper database

# Models for user managment
class Token(BaseModel):
    """Token model for authentication responses"""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Dara structure for token payload"""
    username: Optional[str] = None


# User model for authentication
class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled : Optional[bool] = None

class UserInDB(User):
    """User model as stored in database, including hashed password"""
    hashed_password: str

# Test user database (in production, this would be a real database)
fake_users_db = {
    "denis": {
        "username": "denis",
        "full_name": "Denis Developer",
        "email": "denis@example.com",
        "hashed_password": pwd_context.hash("testpassword123"),
        "disabled": False 
    }
}

# Authentication helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify if a plain password matches its hashed version"""
    return pwd_context.verify(plain_password, hashed_password)

def get_user(username: str) -> Optional[UserInDB]:
    """Retrive a user from the database"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username)),
        user = cursor.fetchone()
        if user:
            return UserInDB(
                username = user[1],
                email = user[2],
                full_name = user[3],
                hashed_password = user[4],
                disabled = user[5]
            )
    return None


def authenticate_user(username: str, password: str) -> Union[bool, UserInDB]:
    """Authenticate a user's credentials"""
    user = get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a new JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Validate token and return current user"""
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = "Could not validate credential",
        headers = {"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


# 2 App initialization 
app = FastAPI(
    title= "Learning Progress Tracker",
    description="""
    A comprehensive API for tracking your programming learning journey.

    Key Features :
    . Track time spent learning different progamming topic
    . Record difficulty level and understanding metrics
    . Store notes and questions from each learning session
    . Analyze progess over time with detailed analytics

    This API is a part of learning journey to become a professional Python developer.
    """,
    version = "1.0.0",
    openapi_tags = [{
        "name": "Learning Progress",
        "description": "Operations for tracking and learning sessions"     
        }]
)


# Login endpoint
@app.post("/token", response_model = Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Endpoint for user authentication and token generation"""
    user = authenticate_user(form_data.username, form_data.password )
    if not user:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Incorrect username or password",
            headers = {"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/register", response_model=User)
async def register_user(username:str, password: str, email: Optional[str] = None, full_name: Optional[str] = None ):
    """Register a new user"""
    with get_db_connection as conn:
        cursor = conn.cursor()
        try:
            hashed_password = pwd_context.hash(password)
            cursor.execute('''
                INSERT INTO users (username, email, full_name, hashed_password)
                VALUES (?, ?, ?, ?)
                RETURNING id, username, email, full_name
            ''', (username, email, full_name, hashed_password))
            user_data = cursor.fetchone()
            conn.commit()
            return {
                "username": user_data[1],
                "email": user_data[2],
                "full_name": user_data[3]
            }
        except IntegrityError:
            raise HTTPException(
                status_code = 400,
                detail = "Username already exists"
            )

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
                            user_id INTEGER NOT NULL,
                            topic TEXT NOT NULL, 
                            hours_spent REAL NOT NULL,
                            difficulty_level INTEGER NOT NULL,
                            notes TEXT NOT NULL,
                            understanding_level INTEGER NOT NULL,
                            questions TEXT,
                            timestamp TEXT NOT NULL,
                            FOREIGN KEY (user_id) REFERENCES user(id)
                       )
                ''')
        conn.commit()

# Call init.db at startup
init_db()

# User tabled 
def init_user_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,           
                email TEXT UNIQUE,
                full_name TEXT,
                hashed_password TEXT NOT NULL,
                disabled BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )     
        ''')
        conn.commit()

# 6 ENDPOINTS Update POST endpoint to use database
@app.on_event("startup")
async def startup_event():
    init_db()
    init_user_db()




@app.get("/view-progress", tags=["Learning Progress"])
def view_all_progress(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Retrive all learning progress entries

    Returns a comprehensive view of all learning sessions, including:
    - Total number of entries
    - Total hours spent learning
    -Detailed list of all learning sessions

    Example Response:
    '''json
    {
        "total_entries": 10,
        "total_hours": 25.5,
        "entries": [
            {
                "id": 1,
                "topic": "Python",
                "hours_spent": 2.5,
                "difficulty_level": 3,
                "notes": "API Documentation",
                "understanding_level": 8,
                "questions": [],
                "timestamp": "2025-02-05 10:00:00"
            }
        ]
    }
    '''
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Get user_id first
        cursor.execute('SELECT id FROM user WHERE username = ?', (current_user.username)) 
        user_id = cursor.fetchone[0]
        # The get only this user's entries
        cursor.execute('SELECT * FROM learning_updates WHERE user_id = ?', (user_id))
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
    


@app.post("/add-progress", tags=["Learning Progress"])
async def add_learning_progress(
    update: LearningUpdate,
    current_user: User = Depends(get_current_user) # Add this line
) :

    """Record a new learning session with (requires authentication)
    
    This endpoint allows you to log you learning progress with comprehensie detail
    about what you studied and how effective the session was.

    Parameters:
    - **topic**: The main subject studied (e.g., Python, FastAPI, Algorithms)
    - **hour_spent**: Number of hours dedicated to learning (0-24)
    - **difficulty_level**: How challenging the material was (1-5)
    - **notes**: Detailed notes about what you learned
    - **understanding_level**: How well you understood the material (1-10)
    - **questions**: Any questions that came up during learning

    Returns:
    - A JSON object containing:
        - A success message
        - The complete entry data including the assigned ID
    
        Example:
        ''' pyton
        {
             "topic": "Python",
             "hours_spent": 2.5,
             "difficulty_level": 3,
             "notes": "Learned about FastAPI documentation",
             "understanding_level": 8,
             "questions": ["How to handle versioning?"]
        
        }
        '''
  
      """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # First get user's ID
            cursor.execute('SELECT id FROM users WHERE username = ?', (current_user.username,))
            user_id = cursor.fetchone()[0]
            
            questions_json = json.dumps(update.questions)
            cursor.execute('''
                INSERT INTO learning_updates
                (user_id ,topic, hours_spent, difficulty_level, notes, understanding_level, questions, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
            ''', (
                user_id,
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
    

@app.put("/update-progress/{entry_id}", tags=["Learning Progress"])
def update_learning_progress(entry_id: int, update: LearningUpdatePatch):
    """
    Update an existing learning entry

    Parameters:
    - entry_id: ID of the entry to update
    - update: Fields to modify (all fields optional)
    
    Returns:
    - Success message
    - Update entry data
    """
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
    
@app.delete("/delete-progress/{entry_id}", tags=["Learning Progress"])
def delete_learning_progress(entry_id: int):
    """
    Delete a learning entry.

    Parameters:
    - entry_id: ID of the entry to delete

    Returns:
    - Success message
    - ID of the deleted entry
    """
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
    

@app.get("/view-progress/by-topic/{topic}", tags=["Learning Progress"])
def get_progress_by_topic(topic: str):
    """
    Get the 5 most recent learning sessions for a specific topic.

    Parameters:
    - topic: The learning topic to filter by ( e.g., Python, FastAPI)

    Returns:
    - Recent learning entries for the topic
    - Total hours spent on this topic
    - Average difficulty level
    - Latest 5 entries with full details
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            #Add order by timestamp DESC to get most recent entries first
            cursor.execute('''
                SELECT * FROM learning_updates
                WHERE topic = ?
                ORDER BY timestamp DESC
                LIMIT 5
            ''', (topic,)) # Limit to most recent 5 entries
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
                "recent_entries": len(entries),
                "total_hours": round(total_hours,2),
                "average_difficulty": round(total_difficulty / len(entries), 2),
                "latest_entries": entries # Now showing the most recent entries
            }
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        

@app.get("/analytics/learning-summary", tags=["Learning Progress"])
def get_learning_summary():
    """
    Generate a comprehensive summary of all learning activities.

    Returns:
    - Overall summary ( total entries, hours, unique topics)
    - Pep-topic statistics including:
        - Total hours per topic
        - Number of sessions
        - Average understanding level
        - Most studied topic
    """
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


AUTHENTICATION FALL 
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional

#Initialize FastAPI
app = FastAPI(title="Authentication Test")

# Security configuration
# In a real application, you'd want to store in a secure environment variable
SECRET_KEY = "test-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Setup password hashing - this creates a context that how to hash and verify passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated = "auto")

# Setup the OAuth2 scheme - this tells FastAPI how to handle bearer tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Define our models
class Token(BaseModel):
    access_token : str
    token_type: Optional[bool] = None

class User(BaseModel):
    username : str
    disabled: Optional[bool] = None

# For testing, we'll use a simple dictionary as our user database
fake_user_db = {
    "testuser": {
        "username": "testuser",
        "hashed_password": pwd_context.hash("testpassword"),
        "disabled": False 
    }
}

# Helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify if plain password matches its hashed version"""
    return pwd_context.verify(plain_password, hashed_password)

def get_user(username: str):
    """Get user from our test database"""
    if username in fake_user_db:
        return fake_user_db[username]
    return None 

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a new JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

#Endpoints
@app.post("/token", response_model=Token)
async def login(from_data: OAuth2PasswordRequestForm = Depends()):
    """Test endpoint for logging in and getting a token"""
    # Get user from our test database
    user = get_user(from_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="Incorect username or password")
    
    #Verify password
    if not verify_password(from_data.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    #Create access token
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    )

    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/test-auth")
async def test_authentication(token, str = Depends(oauth2_scheme)):
    """Test endpoint that requires authentication"""
    try:
        #Verify token
        playload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = playload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {"message": "Authentication successful!", "username": username}
