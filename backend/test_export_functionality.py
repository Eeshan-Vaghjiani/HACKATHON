#!/usr/bin/env python3
"""
Simple test script to verify export functionality works
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.models.base import LayoutSpec, EnvelopeSpec, ModulePlacement, ModuleType, EnvelopeType
from app.services.export_service import get_model_exporter, get_cad_exporter


async def test_export_functionality():
    """Test basic export functionality"""
    print("Testing HabitatCanvas Export Functionality...")
    
    # Create test envelope
    envelope = EnvelopeSpec(
        id="test-envelope-1",
        type=EnvelopeType.CYLINDER,
        params={"radius": 3.0, "length": 12.0},
        coordinate_frame="local",
        metadata={
            "name": "Test Cylinder Habitat",
            "creator": "test",
            "created": "2024-01-01T00:00:00Z"
        }
    )
    
    # Create test layout with some modules
    modules = [
        ModulePlacement(
            module_id="sleep-1",
            type=ModuleType.SLEEP_QUARTER,
            position=[0.0, 0.0, 0.0],
            rotation_deg=0.0,
            connections=[]
        ),
        ModulePlacement(
            module_id="galley-1",
            type=ModuleType.GALLEY,
            position=[3.0, 0.0, 0.0],
            rotation_deg=90.0,
            connections=["sleep-1"]
        ),
        ModulePlacement(
            module_id="lab-1",
            type=ModuleType.LABORATORY,
            position=[-3.0, 0.0, 0.0],
            rotation_deg=180.0,
            connections=["sleep-1"]
        )
    ]
    
    layout = LayoutSpec(
        layout_id="test-layout-1",
        envelope_id="test-envelope-1",
        modules=modules,
        kpis={
            "mean_transit_time": 15.2,
            "egress_time": 45.0,
            "mass_total": 12500.0,
            "power_budget": 8500.0,
            "thermal_margin": 0.15,
            "lss_margin": 0.25,
            "stowage_utilization": 0.85
        },
        explainability="Test layout with basic module arrangement"
    )
    
    # Test model exporter
    print("\n1. Testing 3D Model Export (GLTF/GLB)...")
    try:
        model_exporter = get_model_exporter()
        
        # Test GLTF export
        gltf_data = await model_exporter.export_layout_gltf(layout, envelope)
        print(f"   ✓ GLTF export successful: {len(gltf_data)} bytes")
        
        # Test JSON export
        json_data = await model_exporter.export_layout_json(layout, envelope)
        print(f"   ✓ JSON export successful: {len(str(json_data))} characters")
        
        # Test batch export
        batch_data = await model_exporter.export_batch_layouts(
            [layout], 
            {envelope.id: envelope},
            format="glb",
            include_json=True
        )
        print(f"   ✓ Batch export successful: {len(batch_data)} bytes")
        
    except Exception as e:
        print(f"   ✗ Model export failed: {e}")
        return False
    
    # Test CAD exporter
    print("\n2. Testing CAD Export (STEP/IGES)...")
    try:
        cad_exporter = get_cad_exporter()
        
        # Test STEP export
        step_data = await cad_exporter.export_layout_step(layout, envelope)
        print(f"   ✓ STEP export successful: {len(step_data)} bytes")
        
        # Test IGES export
        iges_data = await cad_exporter.export_layout_iges(layout, envelope)
        print(f"   ✓ IGES export successful: {len(iges_data)} bytes")
        
    except Exception as e:
        print(f"   ✗ CAD export failed: {e}")
        return False
    
    print("\n✓ All export functionality tests passed!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_export_functionality())
    sys.exit(0 if success else 1)