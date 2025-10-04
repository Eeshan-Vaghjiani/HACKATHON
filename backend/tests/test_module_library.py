"""
Unit tests for the Module Library functionality

Tests module definitions, validation, search, compatibility matrix,
and asset management features.
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from app.models.module_library import (
    ModuleLibrary, ModuleDefinition, AssetReference,
    get_module_library, initialize_module_library
)
from app.models.base import (
    ModuleSpec, ModuleType, BoundingBox, ModuleMetadata
)
from app.core.asset_manager import AssetManager, initialize_asset_manager


class TestModuleLibrary:
    """Test cases for ModuleLibrary class"""
    
    @pytest.fixture
    def temp_assets_dir(self):
        """Create temporary assets directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_path = Path(temp_dir) / "assets"
            assets_path.mkdir(parents=True, exist_ok=True)
            yield assets_path
    
    @pytest.fixture
    def module_library(self, temp_assets_dir):
        """Create a test module library instance"""
        return ModuleLibrary(assets_path=temp_assets_dir)
    
    @pytest.fixture
    def sample_custom_module(self):
        """Create a sample custom module for testing"""
        return ModuleDefinition(
            spec=ModuleSpec(
                module_id="test_custom_module",
                type=ModuleType.STORAGE,
                name="Test Custom Storage",
                bbox_m=BoundingBox(x=2.0, y=2.0, z=2.0),
                mass_kg=400.0,
                power_w=100.0,
                stowage_m3=6.0,
                connectivity_ports=["port_main"],
                adjacency_preferences=[ModuleType.GALLEY],
                adjacency_restrictions=[ModuleType.AIRLOCK],
                metadata=ModuleMetadata(
                    description="Custom storage module for testing",
                    manufacturer="Test Corp",
                    model="TEST-001"
                )
            ),
            asset=AssetReference(
                file_path="test_storage.glb",
                format="glb",
                scale=1.0
            ),
            tags=["test", "custom", "storage"]
        )
    
    def test_library_initialization(self, module_library):
        """Test that library initializes with standard modules"""
        assert module_library._initialized
        assert len(module_library._modules) == 8  # 8 standard modules
        
        # Check that all standard module types are present
        module_types = {m.module_type for m in module_library._modules.values()}
        expected_types = {
            ModuleType.SLEEP_QUARTER, ModuleType.GALLEY, ModuleType.LABORATORY,
            ModuleType.AIRLOCK, ModuleType.MECHANICAL, ModuleType.MEDICAL,
            ModuleType.EXERCISE, ModuleType.STORAGE
        }
        assert module_types == expected_types
    
    def test_get_module_by_id(self, module_library):
        """Test retrieving modules by ID"""
        # Test existing module
        sleep_module = module_library.get_module("std_sleep_quarter")
        assert sleep_module is not None
        assert sleep_module.module_type == ModuleType.SLEEP_QUARTER
        
        # Test non-existent module
        non_existent = module_library.get_module("non_existent_module")
        assert non_existent is None
    
    def test_get_modules_by_type(self, module_library):
        """Test retrieving modules by type"""
        sleep_modules = module_library.get_modules_by_type(ModuleType.SLEEP_QUARTER)
        assert len(sleep_modules) == 1
        assert sleep_modules[0].module_id == "std_sleep_quarter"
        
        # Test type with no modules
        # Add a second sleep quarter first
        custom_sleep = ModuleDefinition(
            spec=ModuleSpec(
                module_id="custom_sleep",
                type=ModuleType.SLEEP_QUARTER,
                name="Custom Sleep Quarter",
                bbox_m=BoundingBox(x=2.0, y=2.0, z=2.5),
                mass_kg=450.0,
                power_w=75.0,
                stowage_m3=1.2,
                connectivity_ports=["port_main"]
            ),
            asset=AssetReference(file_path="custom_sleep.glb", format="glb")
        )
        
        module_library.add_custom_module(custom_sleep)
        sleep_modules = module_library.get_modules_by_type(ModuleType.SLEEP_QUARTER)
        assert len(sleep_modules) == 2
    
    def test_search_modules(self, module_library):
        """Test module search functionality"""
        # Search by query text
        galley_results = module_library.search_modules(query="galley")
        assert len(galley_results) == 1
        assert galley_results[0].module_type == ModuleType.GALLEY
        
        # Search by module type
        lab_results = module_library.search_modules(module_types=[ModuleType.LABORATORY])
        assert len(lab_results) == 1
        assert lab_results[0].module_type == ModuleType.LABORATORY
        
        # Search by mass limit
        light_modules = module_library.search_modules(max_mass_kg=500.0)
        assert all(m.spec.mass_kg <= 500.0 for m in light_modules)
        
        # Search by power limit
        low_power_modules = module_library.search_modules(max_power_w=100.0)
        assert all(m.spec.power_w <= 100.0 for m in low_power_modules)
    
    def test_add_custom_module(self, module_library, sample_custom_module, temp_assets_dir):
        """Test adding custom modules"""
        # Create placeholder asset file
        asset_file = temp_assets_dir / "test_storage.glb"
        asset_file.write_text("placeholder content")
        
        # Add custom module
        success = module_library.add_custom_module(sample_custom_module)
        assert success
        
        # Verify module was added
        retrieved = module_library.get_module("test_custom_module")
        assert retrieved is not None
        assert retrieved.spec.name == "Test Custom Storage"
        
        # Test adding duplicate module ID
        duplicate_success = module_library.add_custom_module(sample_custom_module)
        assert not duplicate_success
    
    def test_remove_module(self, module_library, sample_custom_module, temp_assets_dir):
        """Test removing modules"""
        # Create placeholder asset file
        asset_file = temp_assets_dir / "test_storage.glb"
        asset_file.write_text("placeholder content")
        
        # Add and then remove custom module
        module_library.add_custom_module(sample_custom_module)
        success = module_library.remove_module("test_custom_module")
        assert success
        
        # Verify module was removed
        retrieved = module_library.get_module("test_custom_module")
        assert retrieved is None
        
        # Test removing standard module (should fail)
        std_remove_success = module_library.remove_module("std_sleep_quarter")
        assert not std_remove_success
        
        # Test removing non-existent module
        non_existent_success = module_library.remove_module("non_existent")
        assert not non_existent_success
    
    def test_validate_module(self, module_library, sample_custom_module):
        """Test module validation"""
        # Valid module should have no errors
        errors = module_library.validate_module(sample_custom_module)
        assert len(errors) > 0  # Will have asset file error since file doesn't exist
        
        # Test module with invalid power consumption
        invalid_module = ModuleDefinition(
            spec=ModuleSpec(
                module_id="invalid_power_module",
                type=ModuleType.STORAGE,
                name="Invalid Power Module",
                bbox_m=BoundingBox(x=2.0, y=2.0, z=2.0),
                mass_kg=400.0,
                power_w=6000.0,  # Exceeds 5kW limit
                stowage_m3=6.0,
                connectivity_ports=["port_main"]
            ),
            asset=AssetReference(file_path="invalid.glb", format="glb")
        )
        
        errors = module_library.validate_module(invalid_module)
        assert any("power consumption exceeds 5kW" in error for error in errors)
        
        # Test module with invalid mass
        invalid_mass_module = ModuleDefinition(
            spec=ModuleSpec(
                module_id="invalid_mass_module",
                type=ModuleType.STORAGE,
                name="Invalid Mass Module",
                bbox_m=BoundingBox(x=2.0, y=2.0, z=2.0),
                mass_kg=2500.0,  # Exceeds 2000kg limit
                power_w=100.0,
                stowage_m3=6.0,
                connectivity_ports=["port_main"]
            ),
            asset=AssetReference(file_path="invalid.glb", format="glb")
        )
        
        errors = module_library.validate_module(invalid_mass_module)
        assert any("mass exceeds 2000kg" in error for error in errors)
    
    def test_compatibility_matrix(self, module_library):
        """Test compatibility matrix generation"""
        matrix = module_library.get_compatibility_matrix()
        
        # Check matrix structure
        assert isinstance(matrix, dict)
        assert len(matrix) == len(module_library._modules)
        
        # Check specific compatibility rules
        sleep_quarter_compat = matrix.get("std_sleep_quarter", {})
        
        # Sleep quarter should prefer medical and galley
        assert sleep_quarter_compat.get("std_medical") == "preferred"
        assert sleep_quarter_compat.get("std_galley") == "preferred"
        
        # Sleep quarter should restrict mechanical and airlock
        assert sleep_quarter_compat.get("std_mechanical") == "restricted"
        assert sleep_quarter_compat.get("std_airlock") == "restricted"
        
        # Self-reference should be "self"
        assert sleep_quarter_compat.get("std_sleep_quarter") == "self"
    
    def test_library_stats(self, module_library):
        """Test library statistics"""
        stats = module_library.get_library_stats()
        
        # Check required fields
        assert "total_modules" in stats
        assert "module_types" in stats
        assert "total_mass_kg" in stats
        assert "total_power_w" in stats
        assert "total_stowage_m3" in stats
        assert "cache_metadata" in stats
        
        # Check values
        assert stats["total_modules"] == 8  # 8 standard modules
        assert stats["total_mass_kg"] > 0
        assert stats["total_power_w"] > 0
        assert stats["total_stowage_m3"] > 0
        
        # Check module type counts
        type_counts = stats["module_types"]
        assert all(count == 1 for count in type_counts.values())  # Each type appears once
    
    def test_export_import_library(self, module_library, sample_custom_module, temp_assets_dir):
        """Test library export and import functionality"""
        # Create placeholder asset file
        asset_file = temp_assets_dir / "test_storage.glb"
        asset_file.write_text("placeholder content")
        
        # Add custom module
        module_library.add_custom_module(sample_custom_module)
        
        # Export library
        export_file = temp_assets_dir / "library_export.json"
        export_success = module_library.export_library(export_file)
        assert export_success
        assert export_file.exists()
        
        # Verify export content
        with open(export_file, 'r') as f:
            export_data = json.load(f)
        
        assert "metadata" in export_data
        assert "modules" in export_data
        assert len(export_data["modules"]) == 9  # 8 standard + 1 custom
        
        # Create new library and import
        new_library = ModuleLibrary(assets_path=temp_assets_dir)
        import_success = new_library.import_library(export_file, merge=True)
        assert import_success
        
        # Verify imported module
        imported_module = new_library.get_module("test_custom_module")
        assert imported_module is not None
        assert imported_module.spec.name == "Test Custom Storage"
    
    def test_global_library_instance(self):
        """Test global library instance management"""
        # Get default instance
        library1 = get_module_library()
        library2 = get_module_library()
        
        # Should be the same instance
        assert library1 is library2
        
        # Initialize with custom settings
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_library = initialize_module_library(
                assets_path=Path(temp_dir),
                cache_ttl_hours=48
            )
            
            # Should be different from default
            assert custom_library is not library1
            
            # New calls should return the custom instance
            library3 = get_module_library()
            assert library3 is custom_library


class TestAssetReference:
    """Test cases for AssetReference model"""
    
    def test_valid_asset_reference(self):
        """Test creating valid asset references"""
        asset = AssetReference(
            file_path="test_module.glb",
            format="glb",
            scale=1.0,
            checksum="abc123"
        )
        
        assert asset.file_path == "test_module.glb"
        assert asset.format == "glb"
        assert asset.scale == 1.0
        assert asset.checksum == "abc123"
    
    def test_invalid_format(self):
        """Test validation of asset format"""
        with pytest.raises(ValueError, match="Asset format must be one of"):
            AssetReference(
                file_path="test.xyz",
                format="xyz"  # Invalid format
            )
    
    def test_format_normalization(self):
        """Test that format is normalized to lowercase"""
        asset = AssetReference(
            file_path="test.GLB",
            format="GLB"
        )
        
        assert asset.format == "glb"


class TestModuleDefinition:
    """Test cases for ModuleDefinition model"""
    
    def test_module_definition_properties(self):
        """Test ModuleDefinition computed properties"""
        spec = ModuleSpec(
            module_id="test_module",
            type=ModuleType.STORAGE,
            name="Test Module",
            bbox_m=BoundingBox(x=2.0, y=2.0, z=2.0),
            mass_kg=400.0,
            power_w=100.0,
            stowage_m3=6.0,
            connectivity_ports=["port_main"]
        )
        
        asset = AssetReference(
            file_path="test.glb",
            format="glb"
        )
        
        module_def = ModuleDefinition(
            spec=spec,
            asset=asset,
            tags=["test", "storage"]
        )
        
        # Test computed properties
        assert module_def.module_id == "test_module"
        assert module_def.module_type == ModuleType.STORAGE
        
        # Test timestamps
        assert isinstance(module_def.created_at, datetime)
        assert isinstance(module_def.updated_at, datetime)


if __name__ == "__main__":
    pytest.main([__file__])