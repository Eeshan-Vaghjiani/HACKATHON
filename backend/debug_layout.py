"""
Debug script for layout generation
"""

import asyncio
from app.models.base import (
    EnvelopeSpec, MissionParameters, EnvelopeType, CoordinateFrame, 
    EnvelopeMetadata, ModuleType
)
from app.services.layout_generator import BasicLayoutGenerator
from app.models.module_library import get_module_library


async def debug_layout_generation():
    """Debug layout generation step by step"""
    
    # Create a large envelope to ensure modules can fit
    envelope = EnvelopeSpec(
        id="debug_envelope",
        type=EnvelopeType.CYLINDER,
        params={"radius": 5.0, "length": 20.0},  # Large cylinder
        coordinate_frame=CoordinateFrame.LOCAL,
        metadata=EnvelopeMetadata(
            name="Debug Habitat",
            creator="debug"
        )
    )
    
    # Simple mission
    mission = MissionParameters(
        crew_size=2,  # Small crew
        duration_days=30  # Short mission
    )
    
    print(f"Envelope volume: {envelope.volume:.1f} m³")
    
    # Check module library
    library = get_module_library()
    print(f"Module library has {len(library.get_all_modules())} modules")
    
    for module in library.get_all_modules():
        print(f"  - {module.module_id}: {module.spec.type}, {module.spec.bbox_m.volume:.1f} m³")
    
    # Initialize generator
    generator = BasicLayoutGenerator()
    
    # Check required modules
    required_modules = generator._select_required_modules(mission)
    print(f"\nRequired modules for crew of {mission.crew_size}:")
    total_volume = 0
    for module in required_modules:
        volume = module.spec.bbox_m.volume
        total_volume += volume
        print(f"  - {module.spec.type}: {volume:.1f} m³")
    
    print(f"Total required volume: {total_volume:.1f} m³")
    print(f"Envelope usable volume (70%): {envelope.volume * 0.7:.1f} m³")
    
    # Check if modules can fit
    can_fit = generator._validate_envelope_capacity(envelope, required_modules)
    print(f"Can modules fit? {can_fit}")
    
    if can_fit:
        try:
            layouts = await generator.generate_layouts(envelope, mission, count=1)
            print(f"\nGenerated {len(layouts)} layouts!")
            
            if layouts:
                layout = layouts[0]
                print(f"Layout has {len(layout.modules)} modules")
                print(f"Overall score: {layout.kpis.overall_score:.3f}")
        except Exception as e:
            print(f"Generation failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_layout_generation())