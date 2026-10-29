from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.api.routes import router as api_router
from app.tools.implementations import register_default_tools

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and register built-in tools
    await init_db()
    register_default_tools()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Virar AI - Observability, Evaluation, Reliability, and Governance Platform for AI Agents",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Core API Routes
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "platform": "Virar AI",
        "status": "operational",
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR
    }
