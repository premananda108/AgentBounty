"""AgentBounty FastAPI Application"""
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import secrets

from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app.config import settings
from app.utils.db import init_db, check_db_health
from app.routers import auth
from app.routers import wallet
from app.routers import tasks
from app.routers import payments
from app.agents.registry import list_agents
from app.demo_middleware import DemoModeMiddleware
from app.core.mcp_client import mcp_client_instance


import aiosqlite

# --- Constants ---
MCP_USER_ID = "mcp-service-user"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown events"""
    # Startup
    print("\n🚀 AgentBounty starting up...")
    print(f"📍 Environment: {'Development' if settings.DEBUG else 'Production'}")

    # Start the global MCP client
    await mcp_client_instance.startup()

    # Initialize database
    await init_db()

    # Ensure MCP service user exists
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (id) VALUES (?)",
            (MCP_USER_ID,)
        )
        await db.commit()
    print(f"✅ Ensured MCP service user '{MCP_USER_ID}' exists")

    # Check database health
    healthy = await check_db_health()
    if healthy:
        print("✅ Database is healthy")
    else:
        print("⚠️  Database health check failed")

    print(f"✅ Server ready on http://{settings.HOST}:{settings.PORT}\n")

    yield

    # Shutdown
    print("\n👋 AgentBounty shutting down...")
    # Stop the global MCP client
    await mcp_client_instance.shutdown()


# Create FastAPI app
app = FastAPI(
    title="AgentBounty",
    description="Pay-per-use AI Agent Marketplace",
    version="0.1.0",
    lifespan=lifespan
)

# Demo Mode middleware (intercepts requests when ?demo=true)
# IMPORTANT: Must be FIRST (executes last, after SessionMiddleware)
app.add_middleware(DemoModeMiddleware)

# Session middleware (required for Auth0)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="agentbounty_session",
    max_age=3600,  # 1 hour
    same_site="lax",  # "lax" allows cookies on same-site navigation
    https_only=False,  # Allow HTTP in development
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(wallet.router)
app.include_router(tasks.router)
app.include_router(payments.router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_healthy = await check_db_health()

    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
        "version": "0.1.0"
    }


# Agents endpoint
@app.get("/api/agents")
async def get_agents():
    """List all available agents"""
    agents = list_agents()

    return {
        "agents": agents,
        "count": len(agents)
    }


# Simple test endpoint (requires auth)
@app.get("/api/me")
async def get_me(request: Request):
    """Get current user info"""
    user = request.session.get('user')

    if not user:
        return JSONResponse(
            status_code=401,
            content={"error": "Not authenticated", "hint": "Visit /auth/login to login"}
        )

    return {
        "user": user,
        "authenticated": True
    }


# IMPORTANT: This static files mount must come AFTER all other API routes
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
