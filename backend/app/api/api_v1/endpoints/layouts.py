from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.base import (
    LayoutSpec, MissionParameters, EnvelopeSpec, PerformanceMetrics,
    ModulePlacement, ModuleType, LayoutMetadata
)
from app.models.database import Layout
from app.crud import layout as crud_layout
from app.services.layout_generator import BasicLayoutGenerator, LayoutGenerationError

router = APIRouter()


def db_layout_to_spec(db_layout: Layout) -> LayoutSpec:
    """Convert database Layout to Pydantic LayoutSpec"""
    # Convert modules from JSON to ModulePlacement objects
    modules = [
        ModulePlacement(
            module_id=module["module_id"],
            type=ModuleType(module["type"]),
            position=module["position"],
            rotation_deg=module["rotation_deg"],
            connections=module.get("connections", []),
            is_valid=module.get("is_valid"),
            validation_errors=module.get("validation_errors")
        )
        for module in db_layout.modules
    ]
    
    # Create performance metrics
    kpis = PerformanceMetrics(
        mean_transit_time=db_layout.mean_transit_time,
        egress_time=db_layout.egress_time,
        mass_total=db_layout.mass_total,
        power_budget=db_layout.power_budget,
        thermal_margin=db_layout.thermal_margin,
        lss_margin=db_layout.lss_margin,
        stowage_utilization=db_layout.stowage_utilization,
        connectivity_score=db_layout.connectivity_score,
        safety_score=db_layout.safety_score,
        efficiency_score=db_layout.efficiency_score,
        volume_utilization=db_layout.volume_utilization
    )
    
    # Create metadata if available
    metadata = None
    if db_layout.name or db_layout.generation_params or db_layout.version:
        metadata = LayoutMetadata(
            name=db_layout.name,
            created=db_layout.created_at,
            generation_params=db_layout.generation_params,
            version=db_layout.version
        )
    
    layout_spec = LayoutSpec(
        layout_id=db_layout.layout_id,
        envelope_id=db_layout.envelope_id,
        modules=modules,
        kpis=kpis,
        explainability=db_layout.explainability,
        metadata=metadata
    )
    
    return layout_spec


@router.post("/generate", response_model=List[LayoutSpec])
async def generate_layouts(
    envelope: EnvelopeSpec,
    mission_params: MissionParameters,
    count: int = Query(5, ge=1, le=8, description="Number of layouts to generate"),
    db: AsyncSession = Depends(get_db)
):
    """Generate multiple candidate layouts for a habitat envelope"""
    try:
        # Initialize layout generator
        generator = BasicLayoutGenerator()
        
        # Generate layouts
        layouts = await generator.generate_layouts(envelope, mission_params, count)
        
        # Store layouts in database
        stored_layouts = []
        for layout in layouts:
            try:
                # Convert LayoutSpec to database format and store
                db_layout = await crud_layout.create_from_spec(db, layout_spec=layout)
                stored_layouts.append(layout)
            except Exception as e:
                # Log error but continue with other layouts
                print(f"Warning: Failed to store layout {layout.layout_id}: {str(e)}")
                stored_layouts.append(layout)  # Still return the generated layout
        
        return stored_layouts
        
    except LayoutGenerationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating layouts: {str(e)}")


@router.get("/", response_model=List[LayoutSpec])
async def get_layouts(
    envelope_id: Optional[str] = Query(None, description="Filter by envelope ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get list of generated layouts"""
    try:
        if envelope_id:
            layouts = await crud_layout.get_by_envelope(db, envelope_id=envelope_id)
        else:
            layouts = await crud_layout.get_multi(db, skip=skip, limit=limit)
        
        return [db_layout_to_spec(layout) for layout in layouts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving layouts: {str(e)}")


@router.get("/{layout_id}", response_model=LayoutSpec)
async def get_layout(
    layout_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific layout by ID"""
    try:
        layout = await crud_layout.get(db, id=layout_id)
        if not layout:
            raise HTTPException(status_code=404, detail="Layout not found")
        
        return db_layout_to_spec(layout)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving layout: {str(e)}")


@router.put("/{layout_id}", response_model=LayoutSpec)
async def update_layout(
    layout_id: str,
    layout: LayoutSpec,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing layout (for manual editing)"""
    try:
        # Ensure the layout ID in the path matches the one in the body
        if layout.layout_id != layout_id:
            raise HTTPException(
                status_code=400, 
                detail="Layout ID in path must match ID in request body"
            )
        
        # Check if layout exists
        existing_layout = await crud_layout.get(db, id=layout_id)
        if not existing_layout:
            raise HTTPException(status_code=404, detail="Layout not found")
        
        # For now, we'll update the metrics only
        # TODO: Implement full layout update with metrics recalculation
        updated_layout = await crud_layout.update_metrics(db, layout_id=layout_id, metrics=layout.kpis)
        
        return db_layout_to_spec(updated_layout)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating layout: {str(e)}")


@router.delete("/{layout_id}")
async def delete_layout(
    layout_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a layout"""
    try:
        layout = await crud_layout.remove(db, id=layout_id)
        if not layout:
            raise HTTPException(status_code=404, detail="Layout not found")
        
        return {"message": "Layout deleted successfully", "layout_id": layout_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting layout: {str(e)}")


@router.get("/search/top-performing")
async def get_top_performing_layouts(
    envelope_id: Optional[str] = Query(None, description="Filter by envelope ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of top layouts to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get top performing layouts by overall score"""
    try:
        layouts = await crud_layout.get_top_performing(db, envelope_id=envelope_id, limit=limit)
        return [db_layout_to_spec(layout) for layout in layouts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving top layouts: {str(e)}")


@router.get("/search/score-range")
async def search_layouts_by_score(
    min_score: Optional[float] = Query(None, ge=0, le=1, description="Minimum overall score"),
    max_score: Optional[float] = Query(None, ge=0, le=1, description="Maximum overall score"),
    db: AsyncSession = Depends(get_db)
):
    """Search layouts by overall score range"""
    try:
        if min_score is not None and max_score is not None and min_score > max_score:
            raise HTTPException(status_code=400, detail="min_score cannot be greater than max_score")
        
        layouts = await crud_layout.search_by_score_range(db, min_score=min_score, max_score=max_score)
        return [db_layout_to_spec(layout) for layout in layouts]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching layouts: {str(e)}")


@router.get("/critical-issues")
async def get_layouts_with_critical_issues(
    db: AsyncSession = Depends(get_db)
):
    """Get layouts that have critical performance issues"""
    try:
        layouts = await crud_layout.get_with_critical_issues(db)
        return [db_layout_to_spec(layout) for layout in layouts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving layouts with issues: {str(e)}")


@router.put("/{layout_id}/metrics", response_model=LayoutSpec)
async def update_layout_metrics(
    layout_id: str,
    metrics: PerformanceMetrics,
    db: AsyncSession = Depends(get_db)
):
    """Update only the performance metrics of a layout"""
    try:
        updated_layout = await crud_layout.update_metrics(db, layout_id=layout_id, metrics=metrics)
        if not updated_layout:
            raise HTTPException(status_code=404, detail="Layout not found")
        
        return db_layout_to_spec(updated_layout)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating layout metrics: {str(e)}")