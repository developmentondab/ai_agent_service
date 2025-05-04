from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .endpoints import agent_interaction, file_qa, auth
from ..config import get_config

def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    config = get_config()
    
    app = FastAPI(
        title="AI Agents Service",
        description="A service for managing AI agents and their interactions",
        version="1.0.0"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(agent_interaction.router, prefix="/api", tags=["agent-interaction"])
    app.include_router(file_qa.router, prefix="/api", tags=["file-qa"])
    
    return app

app = create_app() 