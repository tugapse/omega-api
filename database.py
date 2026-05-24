from tinydb import TinyDB
from config import resolve_path

# Initialize TinyDB
db_path = resolve_path("@ROOT/data/database.json")
db = TinyDB(db_path)

# Logical Tables
users_table = db.table("users")
projects_table = db.table("projects")
assets_table = db.table("assets")


def get_db():
    """FastAPI dependency to get the database instance."""
    try:
        yield db
    finally:
        # In a real-world scenario with a different DB, you might close the connection.
        # For TinyDB, this is a no-op but good practice for dependency structure.
        pass
