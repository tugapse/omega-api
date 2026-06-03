
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AbstractDatabase(ABC):
    """
    Abstract Database Interface.
    This defines the standard CRUD operations needed by the Omega API, 
    allowing us to eventually swap underlying database implementations without changing routes.
    """

    # --- Users ---
    @abstractmethod
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new user and returns the created document."""
        pass

    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass

    # --- Projects ---
    @abstractmethod
    def create_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a project by its ID."""
        pass

    @abstractmethod
    def list_projects_by_owner(self, owner_id: str) -> List[Dict[str, Any]]:
        """Return all projects owned by a specific user."""
        pass

    @abstractmethod
    def update_project(self, project_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def delete_project(self, project_id: str) -> bool:
        pass

    # --- Assets ---
    @abstractmethod
    def create_asset(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_asset(self, asset_id: str, project_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch an asset by ID, optionally ensuring it belongs to a project."""
        pass

    @abstractmethod
    def get_asset_by_virtual_path(self, project_id: str, virtual_path: str) -> Optional[Dict[str, Any]]:
        """Fetch an asset within a project by its unique virtual path."""
        pass

    @abstractmethod
    def list_assets(self, project_id: str, asset_type: Optional[str] = None, directory: Optional[str] = None) -> List[Dict[str, Any]]:
        """List assets for a project, optionally filtered by type and virtual directory prefix."""
        pass

    @abstractmethod
    def update_asset(self, asset_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def delete_asset(self, asset_id: str) -> bool:
        pass
