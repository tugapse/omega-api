import requests
import sys

# Test 1: Register User
reg_res = requests.post("http://127.0.0.1:8000/api/v1/auth/register", json={"username": "testuser", "email": "test@test.com"})
if reg_res.status_code != 201:
    print(f"Failed to register user: {reg_res.text}")
    sys.exit(1)
print("Registered user.")

# Test 2: Register Duplicate User
dup_res = requests.post("http://127.0.0.1:8000/api/v1/auth/register", json={"username": "testuser", "email": "test@test.com"})
if dup_res.status_code != 400:
    print("Failed to reject duplicate user.")
    sys.exit(1)
print("Rejected duplicate user.")

# Test 3: Login User
login_res = requests.post("http://127.0.0.1:8000/api/v1/auth/login", json={"username": "testuser", "password": "password"})
if login_res.status_code != 200:
    print("Failed to login user.")
    sys.exit(1)
token = login_res.json()["access_token"]
print("Logged in user.")

# Test 4: Get Profile Without Token
profile_res = requests.get("http://127.0.0.1:8000/api/v1/users/me")
if profile_res.status_code != 401:
    print("Failed to reject profile access without token.")
    sys.exit(1)
print("Rejected profile access without token.")

# Test 5: Update Preferences
headers = {"Authorization": f"Bearer {token}"}
prefs_res = requests.put("http://127.0.0.1:8000/api/v1/users/me/preferences", headers=headers, json={"theme": "light", "notifications_enabled": False, "editor_settings": {}})
if prefs_res.status_code != 200 or prefs_res.json()["theme"] != "light":
    print(f"Failed to update preferences: {prefs_res.text}")
    sys.exit(1)
print("Updated preferences.")
print("ALL TESTS PASSED")
