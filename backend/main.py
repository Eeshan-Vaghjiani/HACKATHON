from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging

from app.core.config import settings
from app.api.api_v1.api import api_router
from app.db.init_db import init_db
from app.core.module_library_init import initialize_habitat_canvas_modules, validate_module_library_setup

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting HabitatCanvas API...")
    
    # Initialize database
    await init_db()
    
    # Initialize module library and asset manager
    module_library_success = initialize_habitat_canvas_modules()
    if module_library_success:
        logger.info("Module library initialized successfully")
        
        # Validate setup
        validation_success = validate_module_library_setup()
        if validation_success:
            logger.info("Module library validation passed")
        else:
            logger.warning("Module library validation failed")
    else:
        logger.error("Failed to initialize module library")
    
    yield
    
    # Shutdown
    logger.info("Shutting down HabitatCanvas API...")
    pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="HabitatCanvas API - Generative Layout Studio for Space Habitats",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {"message": "HabitatCanvas API", "version": settings.VERSION}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )