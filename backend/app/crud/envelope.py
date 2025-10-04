from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.database import Envelope
from app.models.base import EnvelopeSpec


class CRUDEnvelope(CRUDBase[Envelope, EnvelopeSpec, EnvelopeSpec]):
    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[Envelope]:
        """Get envelope by name"""
        result = await db.execute(select(self.model).where(self.model.name == name))
        return result.scalar_one_or_none()

    async def get_with_layouts(self, db: AsyncSession, *, envelope_id: str) -> Optional[Envelope]:
        """Get envelope with its associated layouts"""
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.layouts))
            .where(self.model.id == envelope_id)
        )
        return result.scalar_one_or_none()

    async def create_from_spec(self, db: AsyncSession, *, envelope_spec: EnvelopeSpec) -> Envelope:
        """Create envelope from EnvelopeSpec Pydantic model"""
        # Convert Pydantic model to database model
        envelope_data = {
            "id": envelope_spec.id,
            "name": envelope_spec.metadata.name,
            "type": envelope_spec.type.value if hasattr(envelope_spec.type, 'value') else envelope_spec.type,
            "params": envelope_spec.params,
            "coordinate_frame": envelope_spec.coordinate_frame.value if hasattr(envelope_spec.coordinate_frame, 'value') else envelope_spec.coordinate_frame,
            "creator": envelope_spec.metadata.creator,
            "version": envelope_spec.metadata.version,
            "description": envelope_spec.metadata.description,
            "volume": envelope_spec.volume,
        }
        
        # Add constraints if present
        if envelope_spec.constraints:
            envelope_data.update({
                "min_volume": envelope_spec.constraints.min_volume,
                "max_volume": envelope_spec.constraints.max_volume,
                "min_dimension": envelope_spec.constraints.min_dimension,
                "max_dimension": envelope_spec.constraints.max_dimension,
            })
        
        db_obj = self.model(**envelope_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_from_spec(
        self, 
        db: AsyncSession, 
        *, 
        envelope_id: str, 
        envelope_spec: EnvelopeSpec
    ) -> Optional[Envelope]:
        """Update envelope from EnvelopeSpec Pydantic model"""
        db_obj = await self.get(db, id=envelope_id)
        if not db_obj:
            return None
        
        # Update fields from spec
        db_obj.name = envelope_spec.metadata.name
        db_obj.type = envelope_spec.type.value if hasattr(envelope_spec.type, 'value') else envelope_spec.type
        db_obj.params = envelope_spec.params
        db_obj.coordinate_frame = envelope_spec.coordinate_frame.value if hasattr(envelope_spec.coordinate_frame, 'value') else envelope_spec.coordinate_frame
        db_obj.creator = envelope_spec.metadata.creator
        db_obj.version = envelope_spec.metadata.version
        db_obj.description = envelope_spec.metadata.description
        db_obj.volume = envelope_spec.volume
        
        # Update constraints if present
        if envelope_spec.constraints:
            db_obj.min_volume = envelope_spec.constraints.min_volume
            db_obj.max_volume = envelope_spec.constraints.max_volume
            db_obj.min_dimension = envelope_spec.constraints.min_dimension
            db_obj.max_dimension = envelope_spec.constraints.max_dimension
        else:
            # Clear constraints if not provided
            db_obj.min_volume = None
            db_obj.max_volume = None
            db_obj.min_dimension = None
            db_obj.max_dimension = None
        
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def search_by_type(self, db: AsyncSession, *, envelope_type: str) -> List[Envelope]:
        """Search envelopes by type"""
        result = await db.execute(
            select(self.model).where(self.model.type == envelope_type)
        )
        return result.scalars().all()

    async def search_by_volume_range(
        self, 
        db: AsyncSession, 
        *, 
        min_volume: Optional[float] = None,
        max_volume: Optional[float] = None
    ) -> List[Envelope]:
        """Search envelopes by volume range"""
        query = select(self.model)
        
        if min_volume is not None:
            query = query.where(self.model.volume >= min_volume)
        if max_volume is not None:
            query = query.where(self.model.volume <= max_volume)
        
        result = await db.execute(query)
        return result.scalars().all()


envelope = CRUDEnvelope(Envelope)