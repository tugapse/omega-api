import os
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from tinydb import TinyDB, Query
from src.core.config import resolve_path
from src.core.db_base import AbstractDatabase


class TinyDBAdapter(AbstractDatabase):
    def __init__(self, db: TinyDB):
        self.db = db
        self.users_table = db.table("users")
        self.projects_table = db.table("projects")
        self.assets_table = db.table("assets")

    # --- Users ---
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        self.users_table.insert(user_data)
        return user_data

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        User = Query()
        return self.users_table.get(User.id == user_id)

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        User = Query()
        return self.users_table.get(User.username == username)

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        User = Query()
        return self.users_table.get(User.email == email)

    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        User = Query()
        self.users_table.update(update_data, User.id == user_id)
        return self.get_user_by_id(user_id)

    # --- Projects ---
    def create_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        self.projects_table.insert(project_data)
        return project_data

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        Project = Query()
        return self.projects_table.get(Project.id == project_id)

    def list_projects_by_owner(self, owner_id: str) -> List[Dict[str, Any]]:
        Project = Query()
        return self.projects_table.search(Project.owner_id == owner_id)

    def update_project(self, project_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        Project = Query()
        self.projects_table.update(update_data, Project.id == project_id)
        return self.get_project(project_id)

    def delete_project(self, project_id: str) -> bool:
        Project = Query()
        self.projects_table.remove(Project.id == project_id)
        Asset = Query()
        self.assets_table.remove(Asset.project_id == project_id)
        return True

    # --- Assets ---
    def create_asset(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        self.assets_table.insert(asset_data)
        return asset_data

    def get_asset(self, asset_id: str, project_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        Asset = Query()
        if project_id:
            return self.assets_table.get((Asset.id == asset_id) & (Asset.project_id == project_id))
        return self.assets_table.get(Asset.id == asset_id)

    def get_asset_by_virtual_path(self, project_id: str, virtual_path: str) -> Optional[Dict[str, Any]]:
        Asset = Query()
        return self.assets_table.get((Asset.project_id == project_id) & (Asset.virtual_path == virtual_path))

    def list_assets(self, project_id: str, asset_type: Optional[str] = None, directory: Optional[str] = None) -> List[Dict[str, Any]]:
        Asset = Query()
        assets = self.assets_table.search(Asset.project_id == project_id)
        filtered = []
        for a in assets:
            if asset_type and a.get("asset_type") != asset_type: continue
            if directory and not a.get("virtual_path", "").startswith(directory): continue
            filtered.append(a)
        return filtered

    def update_asset(self, asset_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        Asset = Query()
        asset_doc = self.assets_table.get(Asset.id == asset_id)
        if asset_doc:
            self.assets_table.update(update_data, doc_ids=[asset_doc.doc_id])
            return self.assets_table.get(doc_id=asset_doc.doc_id)
        return None

    def delete_asset(self, asset_id: str) -> bool:
        Asset = Query()
        asset_doc = self.assets_table.get(Asset.id == asset_id)
        if asset_doc:
            self.assets_table.remove(doc_ids=[asset_doc.doc_id])
            return True
        return False


# Initialize TinyDB
db_path = resolve_path("@ROOT/data/database.json")

# Check for --overwrite-db flag
if "--overwrite-db" in sys.argv and os.path.exists(db_path):
    print("  --overwrite-db flag detected. Deleting existing database.")
    os.remove(db_path)

_raw_db = TinyDB(db_path)
db_adapter = TinyDBAdapter(_raw_db)

# Legacy exports for backward compatibility during transition
db = _raw_db
users_table = _raw_db.table("users")
projects_table = _raw_db.table("projects")
assets_table = _raw_db.table("assets")


def get_db() -> AbstractDatabase:
    """FastAPI dependency to get the database instance."""
    try:
        yield db_adapter
    finally:
        pass
