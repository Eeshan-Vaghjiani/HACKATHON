from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.crud.base import CRUDBase
from app.models.database import ModuleLibrary
from app.models.base import ModuleSpec, ModuleType


class CRUDModuleLibrary(CRUDBase[ModuleLibrary, ModuleSpec, ModuleSpec]):
    async def get_by_type(self, db: AsyncSession, *, module_type: ModuleType) -> List[ModuleLibrary]:
        """Get all modules of a specific type"""
        result = await db.execute(
            select(self.model).where(self.model.type == module_type.value)
        )
        return result.scalars().all()

    async def create_from_spec(self, db: AsyncSession, *, module_spec: ModuleSpec) -> ModuleLibrary:
        """Create module from ModuleSpec Pydantic model"""
        # Convert Pydantic model to database model
        module_data = {
            "module_id": module_spec.module_id,
            "type": module_spec.type.value if hasattr(module_spec.type, 'value') else module_spec.type,
            "name": module_spec.name,
            "bbox_x": module_spec.bbox_m.x,
            "bbox_y": module_spec.bbox_m.y,
            "bbox_z": module_spec.bbox_m.z,
            "mass_kg": module_spec.mass_kg,
            "power_w": module_spec.power_w,
            "stowage_m3": module_spec.stowage_m3,
            "connectivity_ports": module_spec.connectivity_ports,
            "adjacency_preferences": [pref.value if hasattr(pref, 'value') else pref for pref in module_spec.adjacency_preferences],
            "adjacency_restrictions": [rest.value if hasattr(rest, 'value') else rest for rest in module_spec.adjacency_restrictions],
            "volume": module_spec.bbox_m.volume,
            "density_kg_m3": module_spec.density_kg_m3,
            "power_density_w_m3": module_spec.power_density_w_m3,
        }
        
        # Add metadata if present
        if module_spec.metadata:
            module_data.update({
                "description": module_spec.metadata.description,
                "manufacturer": module_spec.metadata.manufacturer,
                "model": module_spec.metadata.model,
                "certification": module_spec.metadata.certification,
            })
        
        db_obj = self.model(**module_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def search_by_mass_range(
        self, 
        db: AsyncSession, 
        *, 
        min_mass: Optional[float] = None,
        max_mass: Optional[float] = None
    ) -> List[ModuleLibrary]:
        """Search modules by mass range"""
        query = select(self.model)
        
        if min_mass is not None:
            query = query.where(self.model.mass_kg >= min_mass)
        if max_mass is not None:
            query = query.where(self.model.mass_kg <= max_mass)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def search_by_power_range(
        self, 
        db: AsyncSession, 
        *, 
        min_power: Optional[float] = None,
        max_power: Optional[float] = None
    ) -> List[ModuleLibrary]:
        """Search modules by power consumption range"""
        query = select(self.model)
        
        if min_power is not None:
            query = query.where(self.model.power_w >= min_power)
        if max_power is not None:
            query = query.where(self.model.power_w <= max_power)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_compatible_modules(
        self, 
        db: AsyncSession, 
        *, 
        module_type: ModuleType
    ) -> List[ModuleLibrary]:
        """Get modules that are compatible (not restricted) with the given module type"""
        # Get modules that don't have this type in their restrictions
        result = await db.execute(
            select(self.model).where(
                ~self.model.adjacency_restrictions.contains([module_type.value])
            )
        )
        return result.scalars().all()

    async def get_preferred_adjacencies(
        self, 
        db: AsyncSession, 
        *, 
        module_type: ModuleType
    ) -> List[ModuleLibrary]:
        """Get modules that prefer to be adjacent to the given module type"""
        result = await db.execute(
            select(self.model).where(
                self.model.adjacency_preferences.contains([module_type.value])
            )
        )
        return result.scalars().all()

    async def search_by_dimensions(
        self, 
        db: AsyncSession, 
        *, 
        max_x: Optional[float] = None,
        max_y: Optional[float] = None,
        max_z: Optional[float] = None
    ) -> List[ModuleLibrary]:
        """Search modules that fit within given dimensions"""
        query = select(self.model)
        
        if max_x is not None:
            query = query.where(self.model.bbox_x <= max_x)
        if max_y is not None:
            query = query.where(self.model.bbox_y <= max_y)
        if max_z is not None:
            query = query.where(self.model.bbox_z <= max_z)
        
        result = await db.execute(query)
        return result.scalars().all()


module_library = CRUDModuleLibrary(ModuleLibrary)