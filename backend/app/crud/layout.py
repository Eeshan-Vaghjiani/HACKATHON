from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.database import Layout
from app.models.base import LayoutSpec, PerformanceMetrics


class CRUDLayout(CRUDBase[Layout, LayoutSpec, LayoutSpec]):
    async def get_by_envelope(self, db: AsyncSession, *, envelope_id: str) -> List[Layout]:
        """Get all layouts for a specific envelope"""
        result = await db.execute(
            select(self.model).where(self.model.envelope_id == envelope_id)
        )
        return result.scalars().all()

    async def get_with_envelope(self, db: AsyncSession, *, layout_id: str) -> Optional[Layout]:
        """Get layout with its associated envelope"""
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.envelope))
            .where(self.model.layout_id == layout_id)
        )
        return result.scalar_one_or_none()

    async def create_from_spec(self, db: AsyncSession, *, layout_spec: LayoutSpec) -> Layout:
        """Create layout from LayoutSpec Pydantic model"""
        # Convert Pydantic model to database model
        layout_data = {
            "layout_id": layout_spec.layout_id,
            "envelope_id": layout_spec.envelope_id,
            "name": layout_spec.metadata.name if layout_spec.metadata else None,
            "modules": [module.model_dump() for module in layout_spec.modules],
            "explainability": layout_spec.explainability,
            
            # Performance metrics
            "mean_transit_time": layout_spec.kpis.mean_transit_time,
            "egress_time": layout_spec.kpis.egress_time,
            "mass_total": layout_spec.kpis.mass_total,
            "power_budget": layout_spec.kpis.power_budget,
            "thermal_margin": layout_spec.kpis.thermal_margin,
            "lss_margin": layout_spec.kpis.lss_margin,
            "stowage_utilization": layout_spec.kpis.stowage_utilization,
            "connectivity_score": layout_spec.kpis.connectivity_score,
            "safety_score": layout_spec.kpis.safety_score,
            "efficiency_score": layout_spec.kpis.efficiency_score,
            "volume_utilization": layout_spec.kpis.volume_utilization,
            
            # Computed fields
            "module_count": layout_spec.module_count,
            "module_types_count": layout_spec.module_types_count,
            "has_airlock": layout_spec.has_airlock,
            "layout_bounds": layout_spec.layout_bounds,
            "overall_score": layout_spec.kpis.overall_score,
            "critical_issues": layout_spec.kpis.critical_issues,
        }
        
        # Add metadata if present
        if layout_spec.metadata:
            layout_data.update({
                "generation_params": layout_spec.metadata.generation_params,
                "version": layout_spec.metadata.version,
            })
        
        # Add constraints if present
        if layout_spec.constraints:
            layout_data.update({
                "total_mass_constraint": layout_spec.constraints.total_mass,
                "total_power_constraint": layout_spec.constraints.total_power,
                "min_clearance_constraint": layout_spec.constraints.min_clearance,
            })
        
        db_obj = self.model(**layout_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_metrics(
        self, 
        db: AsyncSession, 
        *, 
        layout_id: str, 
        metrics: PerformanceMetrics
    ) -> Optional[Layout]:
        """Update only the performance metrics of a layout"""
        db_obj = await self.get(db, id=layout_id)
        if not db_obj:
            return None
        
        # Update metrics
        db_obj.mean_transit_time = metrics.mean_transit_time
        db_obj.egress_time = metrics.egress_time
        db_obj.mass_total = metrics.mass_total
        db_obj.power_budget = metrics.power_budget
        db_obj.thermal_margin = metrics.thermal_margin
        db_obj.lss_margin = metrics.lss_margin
        db_obj.stowage_utilization = metrics.stowage_utilization
        db_obj.connectivity_score = metrics.connectivity_score
        db_obj.safety_score = metrics.safety_score
        db_obj.efficiency_score = metrics.efficiency_score
        db_obj.volume_utilization = metrics.volume_utilization
        db_obj.overall_score = metrics.overall_score
        db_obj.critical_issues = metrics.critical_issues
        
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def search_by_score_range(
        self, 
        db: AsyncSession, 
        *, 
        min_score: Optional[float] = None,
        max_score: Optional[float] = None
    ) -> List[Layout]:
        """Search layouts by overall score range"""
        query = select(self.model)
        
        if min_score is not None:
            query = query.where(self.model.overall_score >= min_score)
        if max_score is not None:
            query = query.where(self.model.overall_score <= max_score)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_top_performing(
        self, 
        db: AsyncSession, 
        *, 
        envelope_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Layout]:
        """Get top performing layouts by overall score"""
        query = select(self.model).order_by(self.model.overall_score.desc())
        
        if envelope_id:
            query = query.where(self.model.envelope_id == envelope_id)
        
        query = query.limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_with_critical_issues(self, db: AsyncSession) -> List[Layout]:
        """Get layouts that have critical issues"""
        result = await db.execute(
            select(self.model).where(self.model.critical_issues.isnot(None))
        )
        return result.scalars().all()


layout = CRUDLayout(Layout)