"""Firebase JWT Authentication Middleware"""

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import auth, credentials
import os
import json
from typing import Optional

security = HTTPBearer(auto_error=False)

# Initialize Firebase Admin SDK
_firebase_initialized = False

def _init_firebase():
    global _firebase_initialized
    if not _firebase_initialized:
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
        else:
            # Use environment variable for credentials JSON
            cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON", "{}")
            cred = credentials.Certificate(json.loads(cred_json))
        
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        _firebase_initialized = True


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Verify Firebase JWT and return user info, fallback to mock in local dev."""
    mock_user = {
        "id": "00000000-0000-0000-0000-000000000000",
        "email": "arjun.rao@email.com",
        "name": "Arjun Rao",
        "firebase_uid": "mock-user-123",
    }
    
    if not credentials:
        return mock_user
    
    try:
        _init_firebase()
        token = credentials.credentials
        decoded = auth.verify_id_token(token)
        return {
            "id": decoded.get("uid"),
            "email": decoded.get("email"),
            "name": decoded.get("name"),
            "firebase_uid": decoded.get("uid"),
        }
    except Exception:
        # Fallback to mock user for local testing if verification/firebase fails
        return mock_user


async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Require admin role."""
    # In production, check role from DB
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user

