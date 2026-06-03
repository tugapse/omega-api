import pytest
from fastapi.testclient import TestClient
import os
import shutil
import uuid
import sys

# Allow imports from the root directory by adding it to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app
from src.core.database import projects_table, assets_table
from src.core.auth import get_current_user
from src.core.config import resolve_path

# Mock user for testing purposes
TEST_USER = {"id": "test-user-id-projects", "username": "testuser_projects"}

# Mock the authentication dependency to return our test user
async def override_get_current_user():
    return TEST_USER

app.dependency_overrides[get_current_user] = override_get_current_user

# Initialize the test client
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """
    Fixture to ensure a clean state before each test and clean up after.
    This runs automatically for every test function.
    """
    # Setup: Clear database tables and remove physical storage
    projects_table.truncate()
    assets_table.truncate()
    storage_path = resolve_path(f"@ROOT/storage/{TEST_USER['id']}")
    if os.path.exists(storage_path):
        shutil.rmtree(storage_path)
    
    yield  # This is where the test execution happens

    # Teardown: Clean up resources after the test is complete
    projects_table.truncate()
    assets_table.truncate()
    if os.path.exists(storage_path):
        shutil.rmtree(storage_path)

def test_create_project_success():
    """
    Tests successful creation of a new project.
    Verifies HTTP status, response body, database record, and physical folder creation.
    """
    project_data = {
        "name": "My Awesome Game",
        "description": "A new adventure game.",
        "settings": {
            "environment": "development",
            "version": "1.0.0"
        }
    }
    response = client.post("/api/v1/projects", json=project_data)
    
    assert response.status_code == 201, "Expected HTTP 201 Created"
    
    data = response.json()
    assert data["name"] == project_data["name"]
    assert data["description"] == project_data["description"]
    assert data["owner_id"] == TEST_USER["id"]
    assert "id" in data
    assert data["slug"] == "my-awesome-game"
    
    # Verify database state
    assert len(projects_table.all()) == 1
    db_project = projects_table.all()[0]
    assert db_project["id"] == data["id"]
    
    # Verify physical storage creation
    project_storage_path = resolve_path(f"@ROOT/storage/{TEST_USER['id']}/projects/{data['id']}")
    assert os.path.exists(project_storage_path)

def test_list_projects_for_user():
    """
    Tests listing all projects owned by the authenticated user.
    """
    # Create two projects to be listed
    client.post("/api/v1/projects", json={"name": "Project One"})
    client.post("/api/v1/projects", json={"name": "Project Two"})
    
    response = client.get("/api/v1/projects")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Project One"
    assert data[1]["name"] == "Project Two"

def test_get_project_by_id_success():
    """
    Tests fetching a single, specific project by its ID.
    """
    create_response = client.post("/api/v1/projects", json={"name": "Test Project"})
    project_id = create_response.json()["id"]
    
    response = client.get(f"/api/v1/projects/{project_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert data["name"] == "Test Project"

def test_get_project_not_found():
    """
    Tests that fetching a project with a non-existent UUID returns a 404 error.
    """
    non_existent_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/projects/{non_existent_id}")
    assert response.status_code == 404

def test_update_project_success():
    """
    Tests successfully patching a project's name, description, and settings.
    """
    create_response = client.post("/api/v1/projects", json={"name": "Old Name", "description": "Old Desc"})
    project_id = create_response.json()["id"]
    
    update_data = {
        "name": "New Awesome Name",
        "description": "This is the new description.",
        "settings": {"version": "1.0.1"}
    }
    
    response = client.patch(f"/api/v1/projects/{project_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Awesome Name"
    assert data["slug"] == "new-awesome-name"
    assert data["description"] == "This is the new description."
    assert data["settings"]["version"] == "1.0.1"
    
    # Verify database update
    db_project = projects_table.all()[0]
    assert db_project["name"] == "New Awesome Name"

def test_delete_project_success():
    """
    Tests successful deletion of a project.
    Verifies the database record and physical storage are removed.
    """
    create_response = client.post("/api/v1/projects", json={"name": "To Be Deleted"})
    project_id = create_response.json()["id"]
    
    project_storage_path = resolve_path(f"@ROOT/storage/{TEST_USER['id']}/projects/{project_id}")
    assert os.path.exists(project_storage_path), "Pre-condition failed: storage path should exist"
    
    delete_response = client.delete(f"/api/v1/projects/{project_id}")
    
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "success"
    
    # Verify it's gone from the database
    assert len(projects_table.all()) == 0
    
    # Verify physical storage is removed
    assert not os.path.exists(project_storage_path)
    
    # Verify fetching the deleted project now returns a 404
    get_response = client.get(f"/api/v1/projects/{project_id}")
    assert get_response.status_code == 404