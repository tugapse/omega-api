from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..routes.users import router as users_router
from ..routes.projects import router as projects_router
from ..routes.assets import router as assets_router

app = FastAPI(title="Game Project Server API", version="1.0.0")

# Define your specific allowed origins
allowed_origins = [
    "https://your-production-domain.com",  # Production frontend
    "https://staging.your-domain.com",     # Staging frontend
    "http://localhost:4200",               # Local frontend development (if needed)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(assets_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "healthy"}