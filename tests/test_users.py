import pytest
from fastapi.testclient import TestClient
import os
import sys

# Allow imports from the root directory by adding it to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from database import users_table

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    users_table.truncate()
    # Disable any dependency overrides set by other test modules
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides.clear()
    
    yield
    
    users_table.truncate()
    app.dependency_overrides = original_overrides

def test_register_and_login_flow():
    # 1. Register User
    res = client.post("/api/v1/auth/register", json={"username": "testuser", "email": "test@test.com"})
    assert res.status_code == 201
    user_id = res.json()["id"]

    # 2. Register Duplicate User
    res = client.post("/api/v1/auth/register", json={"username": "testuser", "email": "test@test.com"})
    assert res.status_code == 400

    # 3. Login User
    res = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "password"})
    assert res.status_code == 200
    token = res.json()["token"]

    headers = {"Authorization": f"Bearer {token}"}

    # 4. Get Profile
    res = client.get("/api/v1/users/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["username"] == "testuser"

    # 5. Update Profile
    res = client.patch("/api/v1/users/me", headers=headers, json={"username": "newusername"})
    assert res.status_code == 200
    assert res.json()["username"] == "newusername"

    # 6. Get Preferences
    res = client.get("/api/v1/users/me/preferences", headers=headers)
    assert res.status_code == 200
    assert res.json()["theme"] == "dark" # default

    # 7. Update Preferences
    res = client.put("/api/v1/users/me/preferences", headers=headers, json={"theme": "light", "notifications_enabled": False, "editor_settings": {}})
    assert res.status_code == 200
    assert res.json()["theme"] == "light"

    # 8. Logout User
    res = client.post("/api/v1/auth/logout", headers=headers)
    assert res.status_code == 200

def test_unauthorized_endpoints():
    # Attempting to access protected endpoints without a token
    res = client.get("/api/v1/users/me")
    assert res.status_code == 401

    res = client.patch("/api/v1/users/me", json={"username": "hacker"})
    assert res.status_code == 401

    res = client.get("/api/v1/users/me/preferences")
    assert res.status_code == 401

    res = client.put("/api/v1/users/me/preferences", json={"theme": "light", "notifications_enabled": False, "editor_settings": {}})
    assert res.status_code == 401

    res = client.post("/api/v1/auth/logout")
    assert res.status_code == 401

def test_health_check_no_auth():
    # Health check should not require auth
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy"}
