import pytest
from fastapi.testclient import TestClient
import os
import shutil
import uuid
import sys
from datetime import datetime, timezone

# Allow imports from the root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from database import projects_table, assets_table
from auth import get_current_user
from config import resolve_path

# Mock user for testing purposes
TEST_USER = {"id": "test-user-id-assets", "username": "testuser_assets"}

# Mock the authentication dependency
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
    
    yield

    # Teardown: Clean up resources
    projects_table.truncate()
    assets_table.truncate()
    if os.path.exists(storage_path):
        shutil.rmtree(storage_path)

def _create_test_project(name="Test Project"):
    """Helper function to create a project and return its ID."""
    response = client.post("/api/v1/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]

def _create_mock_asset(project_id: str, virtual_path: str, asset_type: str, size: int):
    """Helper function to insert a mock asset record into the database."""
    now = datetime.now(timezone.utc).isoformat() + "Z"
    asset_id = str(uuid.uuid4())
    assets_table.insert({
        "id": asset_id,
        "project_id": project_id,
        "filename": os.path.basename(virtual_path),
        "virtual_path": virtual_path,
        "asset_type": asset_type,
        "mime_type": "application/octet-stream",
        "size_bytes": size,
        "sha256": "a" * 64,
        "created_at": now,
        "updated_at": now,
    })
    return asset_id

def test_get_asset_index_empty_project():
    """
    Tests that querying an empty project returns a 200 OK with an empty asset list.
    """
    project_id = _create_test_project()
    response = client.get(f"/api/v1/projects/{project_id}/assets")

    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project_id
    assert data["total_assets"] == 0
    assert data["total_size_bytes"] == 0
    assert data["assets"] == []

def test_get_asset_index_not_found():
    """
    Tests that querying for a non-existent project UUID returns a 404.
    """
    non_existent_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/projects/{non_existent_id}/assets")
    assert response.status_code == 404

def test_get_asset_index_with_data():
    """
    Tests fetching a populated asset index, verifying counts and totals.
    """
    project_id = _create_test_project()
    _create_mock_asset(project_id, "scripts/main.py", "code", 1024)
    _create_mock_asset(project_id, "textures/player.png", "image", 5120)
    _create_mock_asset(project_id, "audio/music.mp3", "audio", 20480)

    response = client.get(f"/api/v1/projects/{project_id}/assets")

    assert response.status_code == 200
    data = response.json()
    assert data["total_assets"] == 3
    assert data["total_size_bytes"] == 1024 + 5120 + 20480
    assert len(data["assets"]) == 3
    # Check if one of the assets is correctly represented
    asset_filenames = [a["filename"] for a in data["assets"]]
    assert "main.py" in asset_filenames
    assert "player.png" in asset_filenames
    assert "music.mp3" in asset_filenames

def test_get_asset_index_filter_by_type():
    """
    Tests the `type` query parameter to filter assets.
    """
    project_id = _create_test_project()
    _create_mock_asset(project_id, "scripts/main.py", "code", 100)
    _create_mock_asset(project_id, "art/icon.png", "image", 200)
    _create_mock_asset(project_id, "art/logo.png", "image", 300)

    response = client.get(f"/api/v1/projects/{project_id}/assets?type=image")

    assert response.status_code == 200
    data = response.json()
    assert data["total_assets"] == 2
    assert data["total_size_bytes"] == 500
    assert len(data["assets"]) == 2
    assert data["assets"][0]["asset_type"] == "image"
    assert data["assets"][1]["asset_type"] == "image"

def test_get_asset_index_filter_by_dir():
    """
    Tests the `dir` query parameter to filter by virtual directory prefix.
    """
    project_id = _create_test_project()
    _create_mock_asset(project_id, "characters/player/sprite.png", "image", 100)
    _create_mock_asset(project_id, "characters/enemy/sprite.png", "image", 150)
    _create_mock_asset(project_id, "ui/button.png", "image", 50)

    # Test a parent directory
    response = client.get(f"/api/v1/projects/{project_id}/assets?dir=characters")
    assert response.status_code == 200
    data = response.json()
    assert data["total_assets"] == 2
    assert data["total_size_bytes"] == 250

    # Test a more specific sub-directory
    response = client.get(f"/api/v1/projects/{project_id}/assets?dir=characters/player")
    assert response.status_code == 200
    data = response.json()
    assert data["total_assets"] == 1
    assert data["total_size_bytes"] == 100
    assert data["assets"][0]["virtual_path"] == "characters/player/sprite.png"

def test_get_asset_index_filter_by_type_and_dir():
    """
    Tests combining both `type` and `dir` filters.
    """
    project_id = _create_test_project()
    _create_mock_asset(project_id, "scripts/game.js", "code", 1000)
    _create_mock_asset(project_id, "scripts/ai/pathfinding.js", "code", 2000)
    _create_mock_asset(project_id, "scripts/ai/enemy.png", "image", 500) # Decoy

    response = client.get(f"/api/v1/projects/{project_id}/assets?type=code&dir=scripts/ai")

    assert response.status_code == 200
    data = response.json()
    assert data["total_assets"] == 1
    assert data["total_size_bytes"] == 2000
    assert data["assets"][0]["filename"] == "pathfinding.js"