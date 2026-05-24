import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from tinydb import Query

from auth import get_current_user, create_access_token
from database import users_table
from schemas import UserCreate, UserPreferences, UserResponse

router = APIRouter()

class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None

@router.post("/auth/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register_user(user: UserCreate):
    User = Query()
    if users_table.contains((User.email == user.email) | (User.username == user.username)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )

    now = datetime.now(timezone.utc).isoformat()
    new_user = {
        "id": str(uuid.uuid4()),
        "username": user.username,
        "email": user.email,
        "preferences": UserPreferences().model_dump(),
        "created_at": now,
        "updated_at": now
    }
    users_table.insert(new_user)
    return new_user

@router.post("/auth/login")
def login_user(user: UserLogin):
    User = Query()
    existing_user = users_table.get(User.username == user.username)
    
    if not existing_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    token = create_access_token(data={"sub": existing_user["id"]})
    return {"token": token, "access_token": token, "token_type": "bearer"}

@router.post("/auth/logout")
def logout_user(current_user: dict = Depends(get_current_user)):
    return {"message": "Successfully logged out"}

@router.get("/users/me", response_model=UserResponse)
def get_profile(current_user: dict = Depends(get_current_user)):
    return current_user

@router.patch("/users/me", response_model=UserResponse)
def update_profile(user_update: UserUpdate, current_user: dict = Depends(get_current_user)):
    User = Query()
    update_data = user_update.model_dump(exclude_unset=True)
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        users_table.update(update_data, User.id == current_user["id"])
        current_user.update(update_data)
        
    return current_user

@router.get("/users/me/preferences", response_model=UserPreferences)
def get_preferences(current_user: dict = Depends(get_current_user)):
    return current_user.get("preferences", {})

@router.put("/users/me/preferences", response_model=UserPreferences)
def update_preferences(preferences: UserPreferences, current_user: dict = Depends(get_current_user)):
    User = Query()
    updates = {"preferences": preferences.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}
    users_table.update(updates, User.id == current_user["id"])
    return preferences