#!/usr/bin/env python3
"""
Demo script to show database models and CRUD operations working
"""
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.base import (
    EnvelopeSpec, EnvelopeType, CoordinateFrame, EnvelopeMetadata,
    ModuleSpec, ModuleType, BoundingBox,
    LayoutSpec, PerformanceMetrics, ModulePlacement
)
from app.crud import envelope as crud_envelope
from app.crud import module_library as crud_module
from app.crud import layout as crud_layout


async def demo_database_operations():
    """Demonstrate database operations"""
    print("🚀 HabitatCanvas Database Demo")
    print("=" * 50)
    
    # Create in-memory SQLite database for demo
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        print("\n1. Creating Envelope...")
        
        # Create envelope specification
        envelope_metadata = EnvelopeMetadata(
            name="ISS-Style Cylinder",
            creator="demo_user",
            created=datetime.now(),
            version="1.0",
            description="Cylindrical habitat module similar to ISS design"
        )
        
        envelope_spec = EnvelopeSpec(
            id="demo_envelope_001",
            type=EnvelopeType.CYLINDER,
            params={"radius": 2.1, "length": 8.5},  # Similar to ISS module
            coordinate_frame=CoordinateFrame.LOCAL,
            metadata=envelope_metadata
        )
        
        # Create envelope in database
        db_envelope = await crud_envelope.create_from_spec(db, envelope_spec=envelope_spec)
        print(f"   ✅ Created envelope: {db_envelope.name}")
        print(f"   📏 Volume: {db_envelope.volume:.2f} m³")
        
        print("\n2. Creating Module Library...")
        
        # Create some standard modules
        modules = [
            ModuleSpec(
                module_id="sleep_quarter_001",
                type=ModuleType.SLEEP_QUARTER,
                name="Crew Sleep Quarter",
                bbox_m=BoundingBox(x=1.8, y=1.8, z=2.0),
                mass_kg=400.0,
                power_w=80.0,
                stowage_m3=2.5,
                connectivity_ports=["main_port", "emergency_port"],
                adjacency_preferences=[ModuleType.GALLEY, ModuleType.MEDICAL],
                adjacency_restrictions=[ModuleType.MECHANICAL]
            ),
            ModuleSpec(
                module_id="galley_main",
                type=ModuleType.GALLEY,
                name="Main Galley",
                bbox_m=BoundingBox(x=2.0, y=1.5, z=2.0),
                mass_kg=600.0,
                power_w=1200.0,
                stowage_m3=4.0,
                connectivity_ports=["main_port", "utility_port"],
                adjacency_preferences=[ModuleType.SLEEP_QUARTER],
                adjacency_restrictions=[ModuleType.MECHANICAL]
            ),
            ModuleSpec(
                module_id="airlock_eva",
                type=ModuleType.AIRLOCK,
                name="EVA Airlock",
                bbox_m=BoundingBox(x=1.5, y=1.5, z=2.5),
                mass_kg=800.0,
                power_w=300.0,
                stowage_m3=1.5,
                connectivity_ports=["internal_port", "external_port"],
                adjacency_preferences=[ModuleType.STORAGE],
                adjacency_restrictions=[ModuleType.SLEEP_QUARTER, ModuleType.GALLEY]
            )
        ]
        
        db_modules = []
        for module_spec in modules:
            db_module = await crud_module.create_from_spec(db, module_spec=module_spec)
            db_modules.append(db_module)
            print(f"   ✅ Created module: {db_module.name} ({db_module.type})")
        
        print("\n3. Creating Layout...")
        
        # Create module placements
        placements = [
            ModulePlacement(
                module_id="sleep_quarter_001",
                type=ModuleType.SLEEP_QUARTER,
                position=[0.0, 0.0, 0.0],
                rotation_deg=0.0,
                connections=["galley_main"]
            ),
            ModulePlacement(
                module_id="galley_main",
                type=ModuleType.GALLEY,
                position=[3.0, 0.0, 0.0],
                rotation_deg=0.0,
                connections=["sleep_quarter_001", "airlock_eva"]
            ),
            ModulePlacement(
                module_id="airlock_eva",
                type=ModuleType.AIRLOCK,
                position=[6.0, 0.0, 0.0],
                rotation_deg=0.0,
                connections=["galley_main"]
            )
        ]
        
        # Create performance metrics
        metrics = PerformanceMetrics(
            mean_transit_time=45.0,
            egress_time=180.0,
            mass_total=1800.0,  # Sum of module masses
            power_budget=1580.0,  # Sum of module power
            thermal_margin=0.20,
            lss_margin=0.25,
            stowage_utilization=0.75
        )
        
        # Create layout specification
        layout_spec = LayoutSpec(
            layout_id="demo_layout_001",
            envelope_id=envelope_spec.id,
            modules=placements,
            kpis=metrics,
            explainability="Linear layout optimized for crew workflow efficiency. Sleep quarters are positioned away from high-activity areas, with the galley centrally located for easy access. The airlock is positioned at the end for safety and operational efficiency."
        )
        
        # Create layout in database
        db_layout = await crud_layout.create_from_spec(db, layout_spec=layout_spec)
        print(f"   ✅ Created layout: {db_layout.layout_id}")
        print(f"   📊 Overall Score: {db_layout.overall_score:.3f}")
        print(f"   🏠 Module Count: {db_layout.module_count}")
        print(f"   🚪 Has Airlock: {db_layout.has_airlock}")
        
        print("\n4. Querying Database...")
        
        # Query envelopes
        all_envelopes = await crud_envelope.get_multi(db, skip=0, limit=10)
        print(f"   📦 Total Envelopes: {len(all_envelopes)}")
        
        # Query modules by type
        sleep_modules = await crud_module.get_by_type(db, module_type=ModuleType.SLEEP_QUARTER)
        print(f"   🛏️  Sleep Quarters: {len(sleep_modules)}")
        
        galley_modules = await crud_module.get_by_type(db, module_type=ModuleType.GALLEY)
        print(f"   🍽️  Galleys: {len(galley_modules)}")
        
        # Query layouts by envelope
        envelope_layouts = await crud_layout.get_by_envelope(db, envelope_id=envelope_spec.id)
        print(f"   🏗️  Layouts for envelope: {len(envelope_layouts)}")
        
        # Search modules by mass range
        heavy_modules = await crud_module.search_by_mass_range(db, min_mass=500.0)
        print(f"   ⚖️  Heavy modules (>500kg): {len(heavy_modules)}")
        
        print("\n5. Performance Analysis...")
        
        if db_layout.critical_issues:
            print("   ⚠️  Critical Issues:")
            for issue in db_layout.critical_issues:
                print(f"      - {issue}")
        else:
            print("   ✅ No critical issues detected")
        
        print(f"   🚀 Mean Transit Time: {db_layout.mean_transit_time:.1f}s")
        print(f"   🚨 Emergency Egress Time: {db_layout.egress_time:.1f}s")
        print(f"   🌡️  Thermal Margin: {db_layout.thermal_margin:.1%}")
        print(f"   💨 LSS Margin: {db_layout.lss_margin:.1%}")
        
        print("\n6. Testing Updates...")
        
        # Update envelope
        envelope_spec.metadata.name = "Updated ISS-Style Cylinder"
        envelope_spec.params["radius"] = 2.2  # Slightly larger
        
        updated_envelope = await crud_envelope.update_from_spec(
            db, 
            envelope_id=envelope_spec.id, 
            envelope_spec=envelope_spec
        )
        print(f"   ✅ Updated envelope: {updated_envelope.name}")
        print(f"   📏 New Volume: {updated_envelope.volume:.2f} m³")
        
        # Update layout metrics (simulate optimization)
        improved_metrics = PerformanceMetrics(
            mean_transit_time=35.0,  # Improved
            egress_time=150.0,  # Improved
            mass_total=1800.0,
            power_budget=1580.0,
            thermal_margin=0.30,  # Improved
            lss_margin=0.35,  # Improved
            stowage_utilization=0.80  # Better utilization
        )
        
        updated_layout = await crud_layout.update_metrics(
            db, 
            layout_id=layout_spec.layout_id, 
            metrics=improved_metrics
        )
        print(f"   ✅ Updated layout metrics")
        print(f"   📊 New Overall Score: {updated_layout.overall_score:.3f}")
        print(f"   📈 Score Improvement: {updated_layout.overall_score - db_layout.overall_score:.3f}")
        
    await engine.dispose()
    
    print("\n" + "=" * 50)
    print("✅ Database demo completed successfully!")
    print("🎯 All CRUD operations working correctly")


if __name__ == "__main__":
    asyncio.run(demo_database_operations())