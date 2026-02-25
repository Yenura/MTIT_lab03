from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta
from typing import Dict

security = HTTPBearer()

# Secret key for JWT (in production, use environment variables)
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"

def create_token(username: str) -> str:
    """Create JWT token"""
    payload = {
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict:
    """Verify JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, 
            detail={
                "error": "Token Expired",
                "message": "Your access token has expired. Please login again."
            }
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401, 
            detail={
                "error": "Invalid Token",
                "message": "The provided token is invalid. Please check your credentials."
            }
        )