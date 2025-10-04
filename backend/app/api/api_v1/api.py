from fastapi import APIRouter
from app.api.api_v1.endpoints import envelopes, layouts, modules, health
from app.api import module_library

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(envelopes.router, prefix="/envelopes", tags=["envelopes"])
api_router.include_router(layouts.router, prefix="/layouts", tags=["layouts"])
api_router.include_router(modules.router, prefix="/modules", tags=["modules"])
api_router.include_router(module_library.router, prefix="/module-library", tags=["module-library"])