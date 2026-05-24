import os

def resolve_path(target_path: str) -> str:
    if target_path.startswith("@ROOT"):
        return target_path.replace("@ROOT", os.getcwd(), 1)
    return target_path

class Config:
    STORAGE_ROOT: str = resolve_path("@ROOT/storage")

settings = Config()

# Automated Directory Creation
data_dir = resolve_path("@ROOT/data")
storage_dir = resolve_path("@ROOT/storage")

os.makedirs(data_dir, exist_ok=True)
os.makedirs(storage_dir, exist_ok=True)
