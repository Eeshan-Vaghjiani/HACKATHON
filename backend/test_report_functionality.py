#!/usr/bin/env python3
"""
Simple test script to verify report generation functionality works
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.models.base import LayoutSpec, EnvelopeSpec, ModulePlacement, ModuleType, EnvelopeType, PerformanceMetrics
from app.services.report_generator import get_report_generator, ReportTemplate


async def test_report_functionality():
    """Test basic report generation functionality"""
    print("Testing HabitatCanvas Report Generation Functionality...")
    
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
            position=[2.5, 0.0, 0.0],
            rotation_deg=90.0,
            connections=["sleep-1"]
        ),
        ModulePlacement(
            module_id="lab-1",
            type=ModuleType.LABORATORY,
            position=[-2.5, 0.0, 0.0],
            rotation_deg=180.0,
            connections=["sleep-1"]
        ),
        ModulePlacement(
            module_id="airlock-1",
            type=ModuleType.AIRLOCK,
            position=[0.0, 2.5, 0.0],
            rotation_deg=270.0,
            connections=["sleep-1"]
        )
    ]
    
    layout = LayoutSpec(
        layout_id="test-layout-1",
        envelope_id="test-envelope-1",
        modules=modules,
        kpis=PerformanceMetrics(
            mean_transit_time=18.5,
            egress_time=42.0,
            mass_total=15200.0,
            power_budget=9200.0,
            thermal_margin=0.18,
            lss_margin=0.28,
            stowage_utilization=0.82
        ),
        explainability="Test layout demonstrates efficient module arrangement with central sleep quarters connected to all functional areas. The design prioritizes crew accessibility while maintaining emergency egress requirements."
    )
    
    # Test report generator
    print("\n1. Testing PDF Report Generation...")
    try:
        report_generator = get_report_generator()
        
        # Test technical report
        pdf_data = await report_generator.generate_pdf_report(
            [layout], 
            {envelope.id: envelope},
            template=ReportTemplate.TECHNICAL,
            include_3d_snapshots=False
        )
        print(f"   ✓ Technical PDF report generated: {len(pdf_data)} bytes")
        
        # Test executive report
        exec_pdf_data = await report_generator.generate_pdf_report(
            [layout], 
            {envelope.id: envelope},
            template=ReportTemplate.EXECUTIVE,
            include_3d_snapshots=False
        )
        print(f"   ✓ Executive PDF report generated: {len(exec_pdf_data)} bytes")
        
    except Exception as e:
        print(f"   ✗ PDF report generation failed: {e}")
        return False
    
    # Test PNG snapshot generation
    print("\n2. Testing PNG Snapshot Generation...")
    try:
        # Test top view snapshot
        png_data = await report_generator.generate_png_snapshot(
            layout, envelope, width=1920, height=1080, view_angle="top"
        )
        print(f"   ✓ PNG snapshot generated: {len(png_data)} bytes")
        
        # Test smaller snapshot
        small_png_data = await report_generator.generate_png_snapshot(
            layout, envelope, width=800, height=600, view_angle="top"
        )
        print(f"   ✓ Small PNG snapshot generated: {len(small_png_data)} bytes")
        
    except Exception as e:
        print(f"   ✗ PNG snapshot generation failed: {e}")
        return False
    
    # Test executive summary generation
    print("\n3. Testing Executive Summary Generation...")
    try:
        # Test single layout summary
        summary = await report_generator.generate_executive_summary(
            [layout], {envelope.id: envelope}, max_length=300
        )
        print(f"   ✓ Executive summary generated: {len(summary.split())} words")
        print(f"   Summary preview: {summary[:150]}...")
        
        # Test with multiple layouts (create a second layout)
        layout2 = LayoutSpec(
            layout_id="test-layout-2",
            envelope_id="test-envelope-1",
            modules=modules[:3],  # Fewer modules
            kpis=PerformanceMetrics(
                mean_transit_time=22.1,
                egress_time=38.5,
                mass_total=12800.0,
                power_budget=7800.0,
                thermal_margin=0.22,
                lss_margin=0.31,
                stowage_utilization=0.75
            ),
            explainability="Alternative layout with reduced module count for smaller crew missions."
        )
        
        multi_summary = await report_generator.generate_executive_summary(
            [layout, layout2], {envelope.id: envelope}, max_length=400
        )
        print(f"   ✓ Multi-layout summary generated: {len(multi_summary.split())} words")
        
    except Exception as e:
        print(f"   ✗ Executive summary generation failed: {e}")
        return False
    
    # Test comparison report
    print("\n4. Testing Comparison Report Generation...")
    try:
        # Create a comparison report with multiple layouts
        comparison_pdf = await report_generator.generate_pdf_report(
            [layout, layout2], 
            {envelope.id: envelope},
            template=ReportTemplate.COMPARISON,
            include_3d_snapshots=False
        )
        print(f"   ✓ Comparison PDF report generated: {len(comparison_pdf)} bytes")
        
    except Exception as e:
        print(f"   ✗ Comparison report generation failed: {e}")
        return False
    
    print("\n✓ All report generation functionality tests passed!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_report_functionality())
    sys.exit(0 if success else 1)