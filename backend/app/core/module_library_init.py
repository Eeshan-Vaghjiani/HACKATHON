"""
Module Library Initialization Script

Sets up the module library with standard modules and registers their 3D assets.
This script should be run during application startup to ensure the module library
is properly initialized with all standard modules and their assets.
"""

import logging
from pathlib import Path
from typing import Optional

from ..models.module_library import initialize_module_library, get_module_library
from ..core.asset_manager import initialize_asset_manager, get_asset_manager

logger = logging.getLogger(__name__)


def initialize_habitat_canvas_modules(
    assets_root: Optional[Path] = None,
    cache_ttl_hours: int = 24,
    register_assets: bool = True
) -> bool:
    """
    Initialize the HabitatCanvas module library and asset manager.
    
    Args:
        assets_root: Root directory for 3D assets (defaults to "assets/modules")
        cache_ttl_hours: Cache TTL in hours for asset manager
        register_assets: Whether to register standard module assets
    
    Returns:
        True if initialization successful, False otherwise
    """
    try:
        # Set default assets path
        if assets_root is None:
            # Use absolute path from project root
            current_dir = Path(__file__).parent.parent.parent.parent
            assets_root = current_dir / "assets" / "modules"
        
        # Ensure assets directory exists
        assets_root.mkdir(parents=True, exist_ok=True)
        
        # Initialize asset manager
        asset_manager = initialize_asset_manager(
            assets_root=assets_root,
            cache_ttl_hours=cache_ttl_hours
        )
        
        # Initialize module library
        module_library = initialize_module_library(
            assets_path=assets_root,
            cache_ttl_hours=cache_ttl_hours
        )
        
        logger.info(f"Module library initialized with {len(module_library.get_all_modules())} modules")
        
        # Register standard module assets
        if register_assets:
            success = register_standard_assets(module_library, asset_manager)
            if not success:
                logger.warning("Some asset registrations failed")
        
        # Log library statistics
        try:
            stats = module_library.get_library_stats()
            logger.info(f"Module library stats: {stats}")
        except Exception as e:
            logger.error(f"Failed to get library stats: {str(e)}")
        
        try:
            asset_stats = asset_manager.get_cache_stats()
            logger.info(f"Asset manager stats: {asset_stats}")
        except Exception as e:
            logger.error(f"Failed to get asset stats: {str(e)}")
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to initialize module library: {str(e)}")
        return False


def register_standard_assets(module_library, asset_manager) -> bool:
    """
    Register 3D assets for all standard modules.
    
    Args:
        module_library: ModuleLibrary instance
        asset_manager: AssetManager instance
    
    Returns:
        True if all assets registered successfully, False otherwise
    """
    success_count = 0
    total_count = 0
    
    # Get all standard modules
    standard_modules = [
        module for module in module_library.get_all_modules()
        if module.module_id.startswith("std_")
    ]
    
    for module in standard_modules:
        total_count += 1
        
        try:
            # Register the asset
            asset_registered = asset_manager.register_asset(
                asset_id=module.asset.file_path,
                file_path=Path(module.asset.file_path),
                validate=False  # Skip validation for placeholder files
            )
            
            if asset_registered:
                success_count += 1
                logger.debug(f"Registered asset for module {module.module_id}: {module.asset.file_path}")
            else:
                logger.warning(f"Failed to register asset for module {module.module_id}")
        
        except Exception as e:
            logger.error(f"Error registering asset for module {module.module_id}: {str(e)}")
    
    logger.info(f"Registered {success_count}/{total_count} standard module assets")
    return success_count == total_count


def validate_module_library_setup() -> bool:
    """
    Validate that the module library is properly set up.
    
    Returns:
        True if validation passes, False otherwise
    """
    try:
        # Get library instances
        module_library = get_module_library()
        asset_manager = get_asset_manager()
        
        # Check that standard modules are loaded
        all_modules = module_library.get_all_modules()
        standard_modules = [m for m in all_modules if m.module_id.startswith("std_")]
        
        if len(standard_modules) != 8:
            logger.error(f"Expected 8 standard modules, found {len(standard_modules)}")
            return False
        
        # Check that all module types are represented
        expected_types = {
            "sleep_quarter", "galley", "laboratory", "airlock",
            "mechanical", "medical", "exercise", "storage"
        }
        
        actual_types = set()
        for m in standard_modules:
            if hasattr(m.module_type, 'value'):
                actual_types.add(m.module_type.value)
            else:
                actual_types.add(str(m.module_type))
        
        if actual_types != expected_types:
            missing_types = expected_types - actual_types
            extra_types = actual_types - expected_types
            logger.error(f"Module type mismatch. Missing: {missing_types}, Extra: {extra_types}")
            return False
        
        # Validate module specifications
        validation_errors = []
        for module in standard_modules:
            errors = module_library.validate_module(module)
            # Filter out asset file errors for placeholder files
            filtered_errors = [
                error for error in errors 
                if "Asset file not found" not in error
            ]
            if filtered_errors:
                validation_errors.extend(filtered_errors)
        
        if validation_errors:
            logger.error(f"Module validation errors: {validation_errors}")
            return False
        
        # Check compatibility matrix
        compatibility_matrix = module_library.get_compatibility_matrix()
        if len(compatibility_matrix) != len(standard_modules):
            logger.error("Compatibility matrix size mismatch")
            return False
        
        logger.info("Module library validation passed")
        return True
    
    except Exception as e:
        logger.error(f"Module library validation failed: {str(e)}")
        return False


def create_sample_habitat_layout() -> Optional[dict]:
    """
    Create a sample habitat layout using standard modules for testing.
    
    Returns:
        Dictionary representing a sample layout, or None if creation fails
    """
    try:
        module_library = get_module_library()
        
        # Get standard modules
        sleep_quarter = module_library.get_module("std_sleep_quarter")
        galley = module_library.get_module("std_galley")
        laboratory = module_library.get_module("std_laboratory")
        airlock = module_library.get_module("std_airlock")
        mechanical = module_library.get_module("std_mechanical")
        medical = module_library.get_module("std_medical")
        storage = module_library.get_module("std_storage")
        
        if not all([sleep_quarter, galley, laboratory, airlock, mechanical, medical, storage]):
            logger.error("Not all standard modules are available")
            return None
        
        # Create sample layout with module placements
        sample_layout = {
            "layout_id": "sample_habitat_001",
            "envelope_id": "cylinder_envelope_001",
            "name": "Sample Habitat Layout",
            "description": "A sample habitat layout using standard modules",
            "modules": [
                {
                    "module_id": "std_sleep_quarter",
                    "position": [0.0, 0.0, 0.0],
                    "rotation_deg": 0.0,
                    "connections": ["std_galley"]
                },
                {
                    "module_id": "std_galley",
                    "position": [3.0, 0.0, 0.0],
                    "rotation_deg": 0.0,
                    "connections": ["std_sleep_quarter", "std_medical"]
                },
                {
                    "module_id": "std_medical",
                    "position": [6.0, 0.0, 0.0],
                    "rotation_deg": 0.0,
                    "connections": ["std_galley", "std_laboratory"]
                },
                {
                    "module_id": "std_laboratory",
                    "position": [9.0, 0.0, 0.0],
                    "rotation_deg": 0.0,
                    "connections": ["std_medical", "std_storage"]
                },
                {
                    "module_id": "std_storage",
                    "position": [0.0, 3.0, 0.0],
                    "rotation_deg": 90.0,
                    "connections": ["std_laboratory", "std_airlock"]
                },
                {
                    "module_id": "std_airlock",
                    "position": [3.0, 3.0, 0.0],
                    "rotation_deg": 90.0,
                    "connections": ["std_storage", "std_mechanical"]
                },
                {
                    "module_id": "std_mechanical",
                    "position": [6.0, 3.0, 0.0],
                    "rotation_deg": 90.0,
                    "connections": ["std_airlock"]
                }
            ],
            "estimated_metrics": {
                "total_mass_kg": sum([
                    sleep_quarter.spec.mass_kg,
                    galley.spec.mass_kg,
                    laboratory.spec.mass_kg,
                    airlock.spec.mass_kg,
                    mechanical.spec.mass_kg,
                    medical.spec.mass_kg,
                    storage.spec.mass_kg
                ]),
                "total_power_w": sum([
                    sleep_quarter.spec.power_w,
                    galley.spec.power_w,
                    laboratory.spec.power_w,
                    airlock.spec.power_w,
                    mechanical.spec.power_w,
                    medical.spec.power_w,
                    storage.spec.power_w
                ]),
                "total_stowage_m3": sum([
                    sleep_quarter.spec.stowage_m3,
                    galley.spec.stowage_m3,
                    laboratory.spec.stowage_m3,
                    airlock.spec.stowage_m3,
                    mechanical.spec.stowage_m3,
                    medical.spec.stowage_m3,
                    storage.spec.stowage_m3
                ])
            }
        }
        
        logger.info("Created sample habitat layout")
        return sample_layout
    
    except Exception as e:
        logger.error(f"Failed to create sample habitat layout: {str(e)}")
        return None


if __name__ == "__main__":
    # Initialize logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize module library
    success = initialize_habitat_canvas_modules()
    
    if success:
        # Validate setup
        validation_success = validate_module_library_setup()
        
        if validation_success:
            # Create sample layout
            sample_layout = create_sample_habitat_layout()
            
            if sample_layout:
                print("Module library initialization completed successfully!")
                print(f"Sample layout created with {len(sample_layout['modules'])} modules")
                print(f"Total estimated mass: {sample_layout['estimated_metrics']['total_mass_kg']:.1f} kg")
                print(f"Total estimated power: {sample_layout['estimated_metrics']['total_power_w']:.1f} W")
            else:
                print("Module library initialized but sample layout creation failed")
        else:
            print("Module library initialization failed validation")
    else:
        print("Module library initialization failed")