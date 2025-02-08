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

def get_user(db: dict, username: str) -> Optional[UserInDB]:
    """Retrive a user from the database"""
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None

def authenticate_user(db: dict, username: str, password: str) -> Union[bool, UserInDB]:
    """Authenticate a user's credentials"""
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
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
    user = authenticate_user(fake_users_db, form_data.username, form_data.password )
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

# User tabled 
def init_user_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXIST users(
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
def view_all_progress() -> Dict[str, Any]:
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


