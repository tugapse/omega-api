from pydantic import BaseModel, EmailStr, Field
from typing import List, Dict, Literal, Optional

class UserPreferences(BaseModel):
    theme: Literal["dark", "light"] = "dark"
    notifications_enabled: bool = True
    editor_settings: Dict[str, str] = {}

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9]+$")
    email: EmailStr

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    preferences: UserPreferences
    created_at: str
    updated_at: str

class ProjectSettings(BaseModel):
    environment: Literal["development", "staging", "production"] = "development"
    version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    settings: ProjectSettings = Field(default_factory=ProjectSettings)

class ProjectResponse(BaseModel):
    id: str
    slug: str
    owner_id: str
    name: str
    description: Optional[str] = None
    status: Literal["active", "archived", "maintenance"]
    settings: ProjectSettings
    created_at: str
    updated_at: str


class AssetResponse(BaseModel):
    id: str
    filename: str
    virtual_path: str
    asset_type: Literal["code", "image", "audio", "text", "raw"]
    mime_type: str
    size_bytes: int = Field(ge=0)
    sha256: str = Field(min_length=64, max_length=64)
    created_at: str
    updated_at: str


class ProjectAssetIndexResponse(BaseModel):
    project_id: str
    total_assets: int
    total_size_bytes: int
    assets: List[AssetResponse]


class AssetUpdateRequest(BaseModel):
    virtual_path: Optional[str] = None
    asset_type: Optional[Literal["code", "image", "audio", "text", "raw"]] = None
