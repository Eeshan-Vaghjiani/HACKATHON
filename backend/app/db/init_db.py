from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import engine, Base
from app.models.database import (
    Envelope, ModuleLibrary, Layout, SimulationResult, MissionProfile, ExportJob
)
import logging

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Initialize database tables"""
    try:
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise