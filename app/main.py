from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api.agent import router as agent_router
from app.api.hitl import router as hitl_router
from app.api.system import router as system_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Progressive Autonomy Agent Harness with Pydantic & Reversible Tool Execution",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(agent_router)
app.include_router(hitl_router)
app.include_router(system_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "trust_threshold": settings.TRUST_THRESHOLD,
        "mock_llm_enabled": settings.MOCK_LLM_ENABLED
    }
