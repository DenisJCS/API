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
    token_type: str

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
