"""
Module Library API endpoints for HabitatCanvas

Provides REST API access to the module library functionality including
module search, validation, asset management, and compatibility analysis.
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File
from fastapi.responses import FileResponse
import logging

from ..models.module_library import (
    ModuleDefinition, ModuleLibrary, get_module_library,
    AssetReference
)
from ..models.base import ModuleType, ModuleSpec
from ..core.asset_manager import AssetManager, get_asset_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/modules", tags=["Module Library"])


@router.get("/", response_model=List[ModuleDefinition])
async def list_modules(
    module_type: Optional[ModuleType] = Query(None, description="Filter by module type"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    max_mass_kg: Optional[float] = Query(None, description="Maximum mass filter"),
    max_power_w: Optional[float] = Query(None, description="Maximum power filter"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    library: ModuleLibrary = Depends(get_module_library)
):
    """
    List all modules in the library with optional filtering
    """
    try:
        module_types = [module_type] if module_type else None
        
        modules = library.search_modules(
            query=search,
            module_types=module_types,
            tags=tags,
            max_mass_kg=max_mass_kg,
            max_power_w=max_power_w
        )
        
        return modules
    
    except Exception as e:
        logger.error(f"Failed to list modules: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve modules")


@router.get("/{module_id}", response_model=ModuleDefinition)
async def get_module(
    module_id: str,
    library: ModuleLibrary = Depends(get_module_library)
):
    """
    Get a specific module by ID
    """
    module = library.get_module(module_id)
    
    if not module:
        raise HTTPException(status_code=404, detail=f"Module {module_id} not found")
    
    return module


@router.get("/types/{module_type}", response_model=List[ModuleDefinition])
async def get_modules_by_type(
    module_type: ModuleType,
    library: ModuleLibrary = Depends(get_module_library)
):
    """
    Get all modules of a specific type
    """
    try:
        modules = library.get_modules_by_type(module_type)
        return modules
    
    except Exception as e:
        logger.error(f"Failed to get modules by type {module_type}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve modules by type")


@router.post("/validate", response_model=Dict[str, Any])
async def validate_module(
    module: ModuleDefinition,
    library: ModuleLibrary = Depends(get_module_library)
):
    """
    Validate a module definition
    """
    try:
        errors = library.validate_module(module)
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "module_id": module.module_id
        }
    
    except Exception as e:
        logger.error(f"Failed to validate module: {str(e)}")
        raise HTTPException(status_code=500, detail="Module validation failed")


@router.post("/", response_model=Dict[str, Any])
async def add_custom_module(
    module: ModuleDefinition,
    library: ModuleLibrary = Depends(get_module_library)
):
    """
    Add a custom module to the library
    """
    try:
        success = library.add_custom_module(module)
        
        if not success:
            errors = library.validate_module(module)
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to add module. Validation errors: {errors}"
            )
        
        return {
            "success": True,
            "module_id": module.module_id,
            "message": "Module added successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add custom module: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to add module")


@router.delete("/{module_id}", response_model=Dict[str, Any])
async def remove_module(
    module_id: str,
    library: ModuleLibrary = Depends(get_module_library)
):
    """
    Remove a custom module from the library (standard modules cannot be removed)
    """
    try:
        success = library.remove_module(module_id)
        
        if not success:
            if module_id.startswith("std_"):
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot remove standard modules"
                )
            else:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Module {module_id} not found"
                )
        
        return {
            "success": True,
            "module_id": module_id,
            "message": "Module removed successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove module {module_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to remove module")


@router.get("/compatibility/matrix", response_model=Dict[str, Dict[str, str]])
async def get_compatibility_matrix(
    library: ModuleLibrary = Depends(get_module_library)
):
    """
    Get module compatibility matrix showing adjacency preferences and restrictions
    """
    try:
        matrix = library.get_compatibility_matrix()
        return matrix
    
    except Exception as e:
        logger.error(f"Failed to generate compatibility matrix: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate compatibility matrix")


@router.get("/stats", response_model=Dict[str, Any])
async def get_library_stats(
    library: ModuleLibrary = Depends(get_module_library)
):
    """
    Get library statistics and metadata
    """
    try:
        stats = library.get_library_stats()
        return stats
    
    except Exception as e:
        logger.error(f"Failed to get library stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve library statistics")


@router.post("/export", response_model=Dict[str, Any])
async def export_library(
    file_path: str = Query(..., description="Export file path"),
    library: ModuleLibrary = Depends(get_module_library)
):
    """
    Export the module library to a JSON file
    """
    try:
        export_path = Path(file_path)
        success = library.export_library(export_path)
        
        if not success:
            raise HTTPException(status_code=500, detail="Export failed")
        
        return {
            "success": True,
            "file_path": str(export_path),
            "message": "Library exported successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export library: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export library")


@router.post("/import", response_model=Dict[str, Any])
async def import_library(
    file_path: str = Query(..., description="Import file path"),
    merge: bool = Query(True, description="Merge with existing library"),
    library: ModuleLibrary = Depends(get_module_library)
):
    """
    Import modules from a JSON file
    """
    try:
        import_path = Path(file_path)
        
        if not import_path.exists():
            raise HTTPException(status_code=404, detail="Import file not found")
        
        success = library.import_library(import_path, merge=merge)
        
        if not success:
            raise HTTPException(status_code=500, detail="Import failed")
        
        return {
            "success": True,
            "file_path": str(import_path),
            "merge": merge,
            "message": "Library imported successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import library: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to import library")


# Asset management endpoints

@router.get("/{module_id}/asset", response_class=FileResponse)
async def get_module_asset(
    module_id: str,
    library: ModuleLibrary = Depends(get_module_library),
    asset_manager: AssetManager = Depends(get_asset_manager)
):
    """
    Download the 3D asset file for a module
    """
    module = library.get_module(module_id)
    
    if not module:
        raise HTTPException(status_code=404, detail=f"Module {module_id} not found")
    
    asset_path = asset_manager.get_asset_path(module.asset.file_path)
    
    if not asset_path or not asset_path.exists():
        raise HTTPException(status_code=404, detail="Asset file not found")
    
    return FileResponse(
        path=asset_path,
        filename=asset_path.name,
        media_type="application/octet-stream"
    )


@router.get("/{module_id}/asset/info", response_model=Dict[str, Any])
async def get_module_asset_info(
    module_id: str,
    library: ModuleLibrary = Depends(get_module_library),
    asset_manager: AssetManager = Depends(get_asset_manager)
):
    """
    Get information about a module's 3D asset
    """
    module = library.get_module(module_id)
    
    if not module:
        raise HTTPException(status_code=404, detail=f"Module {module_id} not found")
    
    asset_info = asset_manager.get_asset_info(module.asset.file_path)
    
    if not asset_info:
        raise HTTPException(status_code=404, detail="Asset information not found")
    
    return asset_info.model_dump()


@router.post("/{module_id}/asset/upload")
async def upload_module_asset(
    module_id: str,
    file: UploadFile = File(...),
    library: ModuleLibrary = Depends(get_module_library),
    asset_manager: AssetManager = Depends(get_asset_manager)
):
    """
    Upload a new 3D asset file for a module
    """
    module = library.get_module(module_id)
    
    if not module:
        raise HTTPException(status_code=404, detail=f"Module {module_id} not found")
    
    if module_id.startswith("std_"):
        raise HTTPException(status_code=400, detail="Cannot modify assets for standard modules")
    
    # Validate file format
    allowed_formats = {'.gltf', '.glb', '.obj', '.fbx'}
    file_suffix = Path(file.filename).suffix.lower()
    
    if file_suffix not in allowed_formats:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format. Allowed: {allowed_formats}"
        )
    
    try:
        # Save uploaded file
        asset_filename = f"{module_id}{file_suffix}"
        asset_path = asset_manager.assets_root / asset_filename
        
        with open(asset_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Register asset
        success = asset_manager.register_asset(
            asset_id=asset_filename,
            file_path=Path(asset_filename),
            validate=True
        )
        
        if not success:
            asset_path.unlink()  # Clean up failed upload
            raise HTTPException(status_code=400, detail="Asset validation failed")
        
        # Update module asset reference
        module.asset.file_path = asset_filename
        module.asset.format = file_suffix[1:]  # Remove dot
        
        return {
            "success": True,
            "module_id": module_id,
            "asset_filename": asset_filename,
            "message": "Asset uploaded successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload asset for module {module_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload asset")


@router.get("/assets/stats", response_model=Dict[str, Any])
async def get_asset_stats(
    asset_manager: AssetManager = Depends(get_asset_manager)
):
    """
    Get asset manager statistics
    """
    try:
        stats = asset_manager.get_cache_stats()
        return stats
    
    except Exception as e:
        logger.error(f"Failed to get asset stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve asset statistics")


@router.post("/assets/cleanup", response_model=Dict[str, Any])
async def cleanup_asset_cache(
    max_age_days: int = Query(30, description="Maximum age in days for cache cleanup"),
    asset_manager: AssetManager = Depends(get_asset_manager)
):
    """
    Clean up old asset cache entries
    """
    try:
        removed_count = asset_manager.cleanup_cache(max_age_days=max_age_days)
        
        return {
            "success": True,
            "removed_count": removed_count,
            "max_age_days": max_age_days,
            "message": f"Cleaned up {removed_count} old cache entries"
        }
    
    except Exception as e:
        logger.error(f"Failed to cleanup asset cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cleanup asset cache")