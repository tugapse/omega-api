import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.core.auth import get_current_user, create_access_token, get_password_hash, verify_password
from src.core.database import get_db, AbstractDatabase
from src.schemas import UserCreate, UserPreferences, UserResponse

router = APIRouter()

class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None

@router.post("/auth/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register_user(user: UserCreate, db: AbstractDatabase = Depends(get_db)):
    if db.get_user_by_email(user.email) or db.get_user_by_username(user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )

    now = datetime.now(timezone.utc).isoformat()
    new_user = {
        "id": str(uuid.uuid4()),
        "username": user.username,
        "email": user.email,
        "hashed_password": get_password_hash(user.password),
        "preferences": UserPreferences().model_dump(),
        "created_at": now,
        "updated_at": now
    }
    db.create_user(new_user)
    return new_user

@router.post("/auth/login")
def login_user(user: UserLogin, db: AbstractDatabase = Depends(get_db)):
    existing_user = db.get_user_by_username(user.username)
    
    if not existing_user:
        print(f"[AUTH ERROR] Login failed: User '{user.username}' not found.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    hashed_password = existing_user.get("hashed_password")
    
    if not hashed_password:
        print(f"[AUTH ERROR] Login failed: User '{user.username}' has no hashed password (legacy account).")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        
    try:
        if not verify_password(user.password, hashed_password):
            print(f"[AUTH ERROR] Login failed: Incorrect password for user '{user.username}'.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    except Exception as e:
        print(f"[AUTH ERROR] Exception verifying password for '{user.username}': {repr(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    print(f"[AUTH INFO] User '{user.username}' logged in successfully.")
    token = create_access_token(data={"sub": existing_user["id"]})
    return {"token": token, "access_token": token, "token_type": "bearer"}

@router.post("/auth/logout")
def logout_user(current_user: dict = Depends(get_current_user)):
    return {"message": "Successfully logged out"}

@router.get("/users/me", response_model=UserResponse)
def get_profile(current_user: dict = Depends(get_current_user)):
    return current_user

@router.patch("/users/me", response_model=UserResponse)
def update_profile(user_update: UserUpdate, current_user: dict = Depends(get_current_user), db: AbstractDatabase = Depends(get_db)):
    update_data = user_update.model_dump(exclude_unset=True)
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        db.update_user(current_user["id"], update_data)
        current_user.update(update_data)
        
    return current_user

@router.get("/users/me/preferences", response_model=UserPreferences)
def get_preferences(current_user: dict = Depends(get_current_user)):
    return current_user.get("preferences", {})

@router.put("/users/me/preferences", response_model=UserPreferences)
def update_preferences(preferences: UserPreferences, current_user: dict = Depends(get_current_user), db: AbstractDatabase = Depends(get_db)):
    updates = {"preferences": preferences.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}
    db.update_user(current_user["id"], updates)
    return preferences