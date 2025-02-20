# learning_api_debug.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

# Authentication 
SECRET_KEY = "your-secret-key-keep-it-safe" # In production, this should be seciue
ALGORITHM = "HS256" # The algorithm used to sign in the JWB tokens
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # How long tokens remains active

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # This handles token authentication 

app = FastAPI()

@app.post("/test-auth")
async def test_auth():
    # Test password hashing
    test_password = "testpassword123"
    hashed = pwd_context.hash(test_password)
    verified = pwd_context.verify(test_password, hashed)
    return {"password_hashing_works": verified}

