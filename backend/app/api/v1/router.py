"""
AI Research Assistant — API v1 Router

Aggregates all versioned API route modules.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, chat, documents, integrations, research

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["Integrations"])
api_router.include_router(research.router, prefix="/research", tags=["Research"])
