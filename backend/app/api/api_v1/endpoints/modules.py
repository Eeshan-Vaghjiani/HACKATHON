from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.base import ModuleSpec, ModuleType, BoundingBox, ModuleMetadata
from app.models.database import ModuleLibrary
from app.crud import module_library as crud_module

router = APIRouter()


def db_module_to_spec(db_module: ModuleLibrary) -> ModuleSpec:
    """Convert database ModuleLibrary to Pydantic ModuleSpec"""
    bbox = BoundingBox(
        x=db_module.bbox_x,
        y=db_module.bbox_y,
        z=db_module.bbox_z
    )
    
    metadata = None
    if any([db_module.description, db_module.manufacturer, db_module.model, db_module.certification]):
        metadata = ModuleMetadata(
            description=db_module.description,
            manufacturer=db_module.manufacturer,
            model=db_module.model,
            certification=db_module.certification
        )
    
    module_spec = ModuleSpec(
        module_id=db_module.module_id,
        type=ModuleType(db_module.type),
        name=db_module.name,
        bbox_m=bbox,
        mass_kg=db_module.mass_kg,
        power_w=db_module.power_w,
        stowage_m3=db_module.stowage_m3,
        connectivity_ports=db_module.connectivity_ports,
        adjacency_preferences=[ModuleType(pref) for pref in db_module.adjacency_preferences],
        adjacency_restrictions=[ModuleType(rest) for rest in db_module.adjacency_restrictions],
        metadata=metadata
    )
    
    return module_spec


@router.get("/", response_model=List[ModuleSpec])
async def get_modules(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    module_type: Optional[ModuleType] = Query(None, description="Filter by module type"),
    db: AsyncSession = Depends(get_db)
):
    """Get list of modules from the library"""
    try:
        if module_type:
            modules = await crud_module.get_by_type(db, module_type=module_type)
        else:
            modules = await crud_module.get_multi(db, skip=skip, limit=limit)
        
        return [db_module_to_spec(module) for module in modules]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving modules: {str(e)}")


@router.post("/", response_model=ModuleSpec)
async def create_module(
    module: ModuleSpec,
    db: AsyncSession = Depends(get_db)
):
    """Add a new module to the library"""
    try:
        # Check if module with this ID already exists
        existing = await crud_module.get(db, id=module.module_id)
        if existing:
            raise HTTPException(status_code=400, detail=f"Module with ID '{module.module_id}' already exists")
        
        db_module = await crud_module.create_from_spec(db, module_spec=module)
        return db_module_to_spec(db_module)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating module: {str(e)}")


@router.get("/{module_id}", response_model=ModuleSpec)
async def get_module(
    module_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific module by ID"""
    try:
        module = await crud_module.get(db, id=module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        return db_module_to_spec(module)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving module: {str(e)}")


@router.put("/{module_id}", response_model=ModuleSpec)
async def update_module(
    module_id: str,
    module: ModuleSpec,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing module in the library"""
    try:
        # Ensure the module ID in the path matches the one in the body
        if module.module_id != module_id:
            raise HTTPException(
                status_code=400, 
                detail="Module ID in path must match ID in request body"
            )
        
        # Check if module exists
        existing_module = await crud_module.get(db, id=module_id)
        if not existing_module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        # Update the module (for simplicity, we'll recreate it)
        # In a production system, you'd want a proper update method
        await crud_module.remove(db, id=module_id)
        db_module = await crud_module.create_from_spec(db, module_spec=module)
        
        return db_module_to_spec(db_module)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating module: {str(e)}")


@router.delete("/{module_id}")
async def delete_module(
    module_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Remove a module from the library"""
    try:
        module = await crud_module.remove(db, id=module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        return {"message": "Module deleted successfully", "module_id": module_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting module: {str(e)}")


@router.get("/search/mass-range")
async def search_modules_by_mass(
    min_mass: Optional[float] = Query(None, ge=0, description="Minimum mass in kg"),
    max_mass: Optional[float] = Query(None, ge=0, description="Maximum mass in kg"),
    db: AsyncSession = Depends(get_db)
):
    """Search modules by mass range"""
    try:
        if min_mass is not None and max_mass is not None and min_mass > max_mass:
            raise HTTPException(status_code=400, detail="min_mass cannot be greater than max_mass")
        
        modules = await crud_module.search_by_mass_range(db, min_mass=min_mass, max_mass=max_mass)
        return [db_module_to_spec(module) for module in modules]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching modules: {str(e)}")


@router.get("/search/power-range")
async def search_modules_by_power(
    min_power: Optional[float] = Query(None, ge=0, description="Minimum power in watts"),
    max_power: Optional[float] = Query(None, ge=0, description="Maximum power in watts"),
    db: AsyncSession = Depends(get_db)
):
    """Search modules by power consumption range"""
    try:
        if min_power is not None and max_power is not None and min_power > max_power:
            raise HTTPException(status_code=400, detail="min_power cannot be greater than max_power")
        
        modules = await crud_module.search_by_power_range(db, min_power=min_power, max_power=max_power)
        return [db_module_to_spec(module) for module in modules]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching modules: {str(e)}")


@router.get("/search/dimensions")
async def search_modules_by_dimensions(
    max_x: Optional[float] = Query(None, gt=0, description="Maximum width in meters"),
    max_y: Optional[float] = Query(None, gt=0, description="Maximum height in meters"),
    max_z: Optional[float] = Query(None, gt=0, description="Maximum depth in meters"),
    db: AsyncSession = Depends(get_db)
):
    """Search modules that fit within given dimensions"""
    try:
        modules = await crud_module.search_by_dimensions(db, max_x=max_x, max_y=max_y, max_z=max_z)
        return [db_module_to_spec(module) for module in modules]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching modules: {str(e)}")


@router.get("/compatibility/{module_type}")
async def get_compatible_modules(
    module_type: ModuleType,
    db: AsyncSession = Depends(get_db)
):
    """Get modules that are compatible (not restricted) with the given module type"""
    try:
        modules = await crud_module.get_compatible_modules(db, module_type=module_type)
        return [db_module_to_spec(module) for module in modules]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding compatible modules: {str(e)}")


@router.get("/preferences/{module_type}")
async def get_preferred_adjacencies(
    module_type: ModuleType,
    db: AsyncSession = Depends(get_db)
):
    """Get modules that prefer to be adjacent to the given module type"""
    try:
        modules = await crud_module.get_preferred_adjacencies(db, module_type=module_type)
        return [db_module_to_spec(module) for module in modules]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding preferred adjacencies: {str(e)}")


@router.get("/types/")
async def get_module_types():
    """Get all available module types"""
    return {
        "module_types": [
            {
                "value": module_type.value,
                "name": module_type.value.replace("_", " ").title()
            }
            for module_type in ModuleType
        ]
    }