"""
Health check endpoints for monitoring and deployment verification.
"""

import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
import psutil
import logging

from app.core.database import get_db
from app.core.config import get_settings
from app.models.base import HealthStatus, ServiceStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])

settings = get_settings()


class HealthChecker:
    """Comprehensive health checking service"""
    
    def __init__(self):
        self.start_time = time.time()
        self.version = "1.0.0"  # Should be loaded from package info
    
    async def check_database(self, db: AsyncSession) -> ServiceStatus:
        """Check database connectivity and performance"""
        try:
            start_time = time.time()
            
            # Simple connectivity test
            result = await db.execute(text("SELECT 1"))
            result.scalar()
            
            # Performance test
            await db.execute(text("SELECT COUNT(*) FROM information_schema.tables"))
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            # Check for slow queries (basic check)
            slow_query_threshold = 1000  # ms
            status = "healthy" if response_time < slow_query_threshold else "degraded"
            
            return ServiceStatus(
                name="database",
                status=status,
                response_time_ms=response_time,
                details={
                    "type": "postgresql",
                    "connection_pool_size": db.get_bind().pool.size(),
                    "active_connections": db.get_bind().pool.checkedout(),
                }
            )
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return ServiceStatus(
                name="database",
                status="unhealthy",
                error=str(e),
                details={"type": "postgresql"}
            )
    
    async def check_redis(self) -> ServiceStatus:
        """Check Redis connectivity and performance"""
        try:
            start_time = time.time()
            
            # Create Redis connection
            redis_client = redis.from_url(settings.REDIS_URL)
            
            # Connectivity test
            await redis_client.ping()
            
            # Performance test
            test_key = "health_check_test"
            await redis_client.set(test_key, "test_value", ex=60)
            value = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            # Get Redis info
            info = await redis_client.info()
            
            await redis_client.close()
            
            status = "healthy" if response_time < 100 else "degraded"
            
            return ServiceStatus(
                name="redis",
                status=status,
                response_time_ms=response_time,
                details={
                    "version": info.get("redis_version"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory": info.get("used_memory_human"),
                    "keyspace_hits": info.get("keyspace_hits"),
                    "keyspace_misses": info.get("keyspace_misses"),
                }
            )
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return ServiceStatus(
                name="redis",
                status="unhealthy",
                error=str(e)
            )
    
    def check_system_resources(self) -> ServiceStatus:
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Determine overall status
            status = "healthy"
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
                status = "critical"
            elif cpu_percent > 80 or memory_percent > 80 or disk_percent > 80:
                status = "degraded"
            
            return ServiceStatus(
                name="system",
                status=status,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "disk_percent": disk_percent,
                    "disk_free_gb": round(disk.free / (1024**3), 2),
                    "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None,
                }
            )
            
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return ServiceStatus(
                name="system",
                status="unhealthy",
                error=str(e)
            )
    
    async def check_external_services(self) -> List[ServiceStatus]:
        """Check external service dependencies"""
        services = []
        
        # Add checks for external APIs, file storage, etc.
        # Example:
        # try:
        #     # Check S3 connectivity
        #     s3_status = await self.check_s3()
        #     services.append(s3_status)
        # except Exception as e:
        #     services.append(ServiceStatus(
        #         name="s3",
        #         status="unhealthy",
        #         error=str(e)
        #     ))
        
        return services
    
    def get_application_info(self) -> Dict[str, Any]:
        """Get application information"""
        uptime = time.time() - self.start_time
        
        return {
            "name": "HabitatCanvas",
            "version": self.version,
            "environment": settings.ENVIRONMENT,
            "uptime_seconds": round(uptime, 2),
            "uptime_human": self._format_uptime(uptime),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}",
        }
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {secs}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"


# Global health checker instance
health_checker = HealthChecker()


@router.get("/", response_model=HealthStatus)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive health check endpoint.
    
    Returns the overall health status of the application and all its dependencies.
    This endpoint is used by load balancers, monitoring systems, and deployment tools.
    """
    try:
        # Run all health checks concurrently
        db_check_task = health_checker.check_database(db)
        redis_check_task = health_checker.check_redis()
        external_checks_task = health_checker.check_external_services()
        
        # Wait for all checks to complete
        db_status, redis_status, external_statuses = await asyncio.gather(
            db_check_task,
            redis_check_task,
            external_checks_task,
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(db_status, Exception):
            db_status = ServiceStatus(name="database", status="unhealthy", error=str(db_status))
        if isinstance(redis_status, Exception):
            redis_status = ServiceStatus(name="redis", status="unhealthy", error=str(redis_status))
        if isinstance(external_statuses, Exception):
            external_statuses = []
        
        # System check (synchronous)
        system_status = health_checker.check_system_resources()
        
        # Collect all service statuses
        services = [db_status, redis_status, system_status] + external_statuses
        
        # Determine overall status
        overall_status = "healthy"
        for service in services:
            if service.status == "unhealthy":
                overall_status = "unhealthy"
                break
            elif service.status == "degraded":
                overall_status = "degraded"
        
        # Build response
        health_status = HealthStatus(
            status=overall_status,
            timestamp=datetime.now(timezone.utc),
            application=health_checker.get_application_info(),
            services={service.name: service for service in services}
        )
        
        # Set appropriate HTTP status code
        if overall_status == "unhealthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=health_status.dict()
            )
        
        return health_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


@router.get("/liveness")
async def liveness_check():
    """
    Liveness probe endpoint for Kubernetes.
    
    This endpoint should only check if the application process is running
    and able to serve requests. It should not check external dependencies.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": time.time() - health_checker.start_time
    }


@router.get("/readiness")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness probe endpoint for Kubernetes.
    
    This endpoint checks if the application is ready to serve traffic,
    including connectivity to essential external dependencies.
    """
    try:
        # Check essential services only
        db_status = await health_checker.check_database(db)
        redis_status = await health_checker.check_redis()
        
        # Application is ready if essential services are healthy
        ready = (db_status.status in ["healthy", "degraded"] and 
                redis_status.status in ["healthy", "degraded"])
        
        if not ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "not_ready",
                    "database": db_status.status,
                    "redis": redis_status.status,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        
        return {
            "status": "ready",
            "database": db_status.status,
            "redis": redis_status.status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


@router.get("/db")
async def database_health(db: AsyncSession = Depends(get_db)):
    """Database-specific health check endpoint"""
    db_status = await health_checker.check_database(db)
    
    if db_status.status == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=db_status.dict()
        )
    
    return db_status.dict()


@router.get("/redis")
async def redis_health():
    """Redis-specific health check endpoint"""
    redis_status = await health_checker.check_redis()
    
    if redis_status.status == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=redis_status.dict()
        )
    
    return redis_status.dict()


@router.get("/system")
async def system_health():
    """System resources health check endpoint"""
    system_status = health_checker.check_system_resources()
    
    if system_status.status == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=system_status.dict()
        )
    
    return system_status.dict()


@router.get("/metrics")
async def metrics_endpoint():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus format for monitoring and alerting.
    """
    # This would typically use a proper metrics library like prometheus_client
    # For now, return basic metrics in text format
    
    uptime = time.time() - health_checker.start_time
    
    metrics = [
        f"# HELP habitatcanvas_uptime_seconds Application uptime in seconds",
        f"# TYPE habitatcanvas_uptime_seconds counter",
        f"habitatcanvas_uptime_seconds {uptime}",
        "",
        f"# HELP habitatcanvas_info Application information",
        f"# TYPE habitatcanvas_info gauge",
        f'habitatcanvas_info{{version="{health_checker.version}",environment="{settings.ENVIRONMENT}"}} 1',
    ]
    
    return "\n".join(metrics)