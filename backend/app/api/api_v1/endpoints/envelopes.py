from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.base import EnvelopeSpec, EnvelopeType, EnvelopeMetadata, CoordinateFrame
from app.models.database import Envelope
from app.crud import envelope as crud_envelope

router = APIRouter()


def db_envelope_to_spec(db_envelope: Envelope) -> EnvelopeSpec:
    """Convert database Envelope to Pydantic EnvelopeSpec"""
    metadata = EnvelopeMetadata(
        name=db_envelope.name,
        creator=db_envelope.creator,
        created=db_envelope.created_at,
        version=db_envelope.version,
        description=db_envelope.description
    )
    
    envelope_spec = EnvelopeSpec(
        id=db_envelope.id,
        type=EnvelopeType(db_envelope.type),
        params=db_envelope.params,
        coordinate_frame=CoordinateFrame(db_envelope.coordinate_frame),
        metadata=metadata
    )
    
    return envelope_spec


@router.get("/", response_model=List[EnvelopeSpec])
async def get_envelopes(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    envelope_type: Optional[EnvelopeType] = Query(None, description="Filter by envelope type"),
    db: AsyncSession = Depends(get_db)
):
    """Get list of habitat envelopes"""
    try:
        if envelope_type:
            envelopes = await crud_envelope.search_by_type(db, envelope_type=envelope_type.value)
        else:
            envelopes = await crud_envelope.get_multi(db, skip=skip, limit=limit)
        
        return [db_envelope_to_spec(envelope) for envelope in envelopes]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving envelopes: {str(e)}")


@router.post("/", response_model=EnvelopeSpec)
async def create_envelope(
    envelope: EnvelopeSpec,
    db: AsyncSession = Depends(get_db)
):
    """Create a new habitat envelope"""
    try:
        # Check if envelope with this ID already exists
        existing = await crud_envelope.get(db, id=envelope.id)
        if existing:
            raise HTTPException(status_code=400, detail=f"Envelope with ID '{envelope.id}' already exists")
        
        db_envelope = await crud_envelope.create_from_spec(db, envelope_spec=envelope)
        return db_envelope_to_spec(db_envelope)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating envelope: {str(e)}")


@router.get("/{envelope_id}", response_model=EnvelopeSpec)
async def get_envelope(
    envelope_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific habitat envelope by ID"""
    try:
        envelope = await crud_envelope.get(db, id=envelope_id)
        if not envelope:
            raise HTTPException(status_code=404, detail="Envelope not found")
        
        return db_envelope_to_spec(envelope)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving envelope: {str(e)}")


@router.put("/{envelope_id}", response_model=EnvelopeSpec)
async def update_envelope(
    envelope_id: str,
    envelope: EnvelopeSpec,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing habitat envelope"""
    try:
        # Ensure the envelope ID in the path matches the one in the body
        if envelope.id != envelope_id:
            raise HTTPException(
                status_code=400, 
                detail="Envelope ID in path must match ID in request body"
            )
        
        db_envelope = await crud_envelope.update_from_spec(db, envelope_id=envelope_id, envelope_spec=envelope)
        if not db_envelope:
            raise HTTPException(status_code=404, detail="Envelope not found")
        
        return db_envelope_to_spec(db_envelope)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating envelope: {str(e)}")


@router.delete("/{envelope_id}")
async def delete_envelope(
    envelope_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a habitat envelope"""
    try:
        envelope = await crud_envelope.remove(db, id=envelope_id)
        if not envelope:
            raise HTTPException(status_code=404, detail="Envelope not found")
        
        return {"message": "Envelope deleted successfully", "envelope_id": envelope_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting envelope: {str(e)}")


@router.get("/{envelope_id}/layouts")
async def get_envelope_layouts(
    envelope_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all layouts associated with an envelope"""
    try:
        envelope = await crud_envelope.get_with_layouts(db, envelope_id=envelope_id)
        if not envelope:
            raise HTTPException(status_code=404, detail="Envelope not found")
        
        return {
            "envelope_id": envelope_id,
            "layout_count": len(envelope.layouts),
            "layouts": [{"layout_id": layout.layout_id, "name": layout.name} for layout in envelope.layouts]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving envelope layouts: {str(e)}")


@router.get("/search/volume")
async def search_envelopes_by_volume(
    min_volume: Optional[float] = Query(None, ge=0, description="Minimum volume in cubic meters"),
    max_volume: Optional[float] = Query(None, ge=0, description="Maximum volume in cubic meters"),
    db: AsyncSession = Depends(get_db)
):
    """Search envelopes by volume range"""
    try:
        if min_volume is not None and max_volume is not None and min_volume > max_volume:
            raise HTTPException(status_code=400, detail="min_volume cannot be greater than max_volume")
        
        envelopes = await crud_envelope.search_by_volume_range(
            db, min_volume=min_volume, max_volume=max_volume
        )
        
        return [db_envelope_to_spec(envelope) for envelope in envelopes]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching envelopes: {str(e)}")