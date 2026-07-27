from fastapi import APIRouter

from app.api.v1.endpoints import analyze, complaints, documents, health, incidents, official_data

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(analyze.router, prefix="/analyze", tags=["analysis"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["incidents"])
api_router.include_router(complaints.router, prefix="/complaints", tags=["complaints"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(official_data.router, prefix="/official-data", tags=["official-data"])
