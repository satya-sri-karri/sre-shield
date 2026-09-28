import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database.connection import init_db
from backend.database.seed_data import seed_database
from backend.memory.hindsight_engine import hindsight
from backend.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    print("[SRE-Shield] Initializing database tables...")
    await init_db()
    print("[SRE-Shield] Seeding historical incidents & runbooks...")
    await seed_database()
    print("[SRE-Shield] Pre-warming Hindsight Agent Memory index...")
    await hindsight.initialize()
    print("[SRE-Shield] Ready for autonomous SRE operations.")
    yield
    # Shutdown sequence
    print("[SRE-Shield] Shutting down.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan
)

# Enable CORS for dashboard and external tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include main router
app.include_router(router)

@app.get("/")
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "documentation": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
