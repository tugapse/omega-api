import uuid
import os
import shutil
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, List

from database import projects_table, assets_table
from tinydb import Query
from schemas import ProjectCreate, ProjectResponse, ProjectSettings
from auth import get_current_user
from config import resolve_path
from utils.slugger import generate_slug

router = APIRouter()

def get_utc_now_iso():
    return datetime.now(timezone.utc).isoformat()

class ProjectSettingsUpdate(BaseModel):
    environment: Optional[str] = None
    version: Optional[str] = Field(None, pattern=r"^\d+\.\d+\.\d+$")

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    settings: Optional[ProjectSettingsUpdate] = None

@router.post("/projects", status_code=status.HTTP_201_CREATED, response_model=ProjectResponse)
def create_project(project: ProjectCreate, current_user: dict = Depends(get_current_user)):
    project_id = str(uuid.uuid4())
    owner_id = current_user["id"]
    slug = generate_slug(project.name)
    now_iso = get_utc_now_iso()
    
    new_project = {
        "id": project_id,
        "slug": slug,
        "owner_id": owner_id,
        "name": project.name,
        "description": project.description,
        "status": "active",
        "settings": project.settings.model_dump(),
        "created_at": now_iso,
        "updated_at": now_iso
    }
    
    # Physical Storage Setup
    storage_path = resolve_path(f"@ROOT/storage/{owner_id}/projects/{project_id}")
    os.makedirs(storage_path, exist_ok=True)
    
    # Database Sync
    projects_table.insert(new_project)
    
    return new_project

@router.get("/projects", response_model=List[ProjectResponse])
def list_projects(current_user: dict = Depends(get_current_user)):
    Project = Query()
    user_projects = projects_table.search(Project.owner_id == current_user["id"])
    return user_projects

@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, current_user: dict = Depends(get_current_user)):
    Project = Query()
    project = projects_table.get(Project.id == project_id)
    if not project or project["owner_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project

@router.patch("/projects/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, update_data: ProjectUpdate, current_user: dict = Depends(get_current_user)):
    Project = Query()
    project = projects_table.get(Project.id == project_id)
    if not project or project["owner_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        
    update_dict = update_data.model_dump(exclude_unset=True)
    if "name" in update_dict:
        update_dict["slug"] = generate_slug(update_dict["name"])
        
    if "settings" in update_dict and update_dict["settings"] is not None:
        merged_settings = project.get("settings", {})
        merged_settings.update(update_dict["settings"])
        update_dict["settings"] = merged_settings
        
    update_dict["updated_at"] = get_utc_now_iso()
    
    projects_table.update(update_dict, Project.id == project_id)
    updated_project = projects_table.get(Project.id == project_id)
    return updated_project

@router.delete("/projects/{project_id}")
def delete_project(project_id: str, current_user: dict = Depends(get_current_user)):
    Project = Query()
    project = projects_table.get(Project.id == project_id)
    if not project or project["owner_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        
    owner_id = current_user["id"]
    storage_path = resolve_path(f"@ROOT/storage/{owner_id}/projects/{project_id}")
    
    if os.path.exists(storage_path):
        shutil.rmtree(storage_path)
        
    projects_table.remove(Project.id == project_id)
    
    # Remove assets
    Asset = Query()
    assets_table.remove(Asset.project_id == project_id)
    
    return {"status": "success", "message": "Project workspace and all associated physical assets purged from disk."}
