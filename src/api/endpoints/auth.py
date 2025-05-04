from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import Any

from ...auth import create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

@router.post("/token", response_model=dict)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    """
    Get access token for authentication.
    For testing purposes, it accepts any username/password combination.
    In production, you should verify against a database.
    """
    # For testing, we'll accept any username/password
    # In production, you should verify against a database
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username},
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/test-auth")
async def test_auth(current_user = Depends(get_current_user)):
    """Test endpoint to verify authentication is working"""
    return {"message": "You are authenticated", "username": current_user.username} 