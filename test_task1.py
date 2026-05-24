import os
import sys

try:
    import config
    import database
    from schemas import ProjectCreate, ProjectSettings
    from pydantic import ValidationError
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

print("Checking config logic...")
cwd = os.getcwd()
res = config.resolve_path("@ROOT/storage/test")
expected = os.path.join(cwd, "storage/test")
if res != expected:
    print(f"resolve_path failed. Expected {expected}, got {res}")
    sys.exit(1)

print("Checking directory creation...")
if not os.path.isdir(os.path.join(cwd, "data")):
    print("data directory not created")
    sys.exit(1)
if not os.path.isdir(os.path.join(cwd, "storage")):
    print("storage directory not created")
    sys.exit(1)

print("Checking database creation...")
if not os.path.isfile(os.path.join(cwd, "data", "database.json")):
    print("database.json not created")
    sys.exit(1)

print("Checking Pydantic schemas validation...")
try:
    ProjectCreate(name="a" * 101)
    print("Failed to reject name exceeding 100 characters")
    sys.exit(1)
except ValidationError:
    pass

try:
    ProjectCreate(name="test", settings=ProjectSettings(environment="invalid"))
    print("Failed to reject invalid environment")
    sys.exit(1)
except ValidationError:
    pass

try:
    ProjectCreate(name="test", settings=ProjectSettings(version="1.0"))
    print("Failed to reject invalid version")
    sys.exit(1)
except ValidationError:
    pass

print("ALL TESTS PASSED")
