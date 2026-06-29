from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.v1.index_router import index_router
from jobs.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""
    start_scheduler()
    yield


app = FastAPI(
    title="SpendSense API",
    version="1.0.0",
    description="Personal expense tracker powered by SMS parsing",
    lifespan=lifespan,
)

# Mount all versioned routes
app.include_router(index_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
