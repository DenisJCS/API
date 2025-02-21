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
    
