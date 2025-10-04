"""
Module Library for HabitatCanvas

This module defines the standard habitat modules with their specifications,
metadata, and provides functionality for loading, validating, and caching
module definitions.
"""

from typing import Dict, List, Optional, Set, Any
from pathlib import Path
import json
import hashlib
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, field_validator
import logging

from .base import ModuleSpec, ModuleType, BoundingBox, ModuleMetadata

logger = logging.getLogger(__name__)


class AssetReference(BaseModel):
    """Reference to a 3D asset file"""
    file_path: str = Field(..., description="Path to the 3D asset file")
    format: str = Field(..., description="Asset format (gltf, glb)")
    scale: float = Field(default=1.0, gt=0, description="Scale factor for the asset")
    checksum: Optional[str] = Field(None, description="File checksum for validation")
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        allowed_formats = {'gltf', 'glb', 'obj', 'fbx'}
        if v.lower() not in allowed_formats:
            raise ValueError(f'Asset format must be one of: {allowed_formats}')
        return v.lower()


class ModuleDefinition(BaseModel):
    """Extended module specification with 3D assets and validation rules"""
    spec: ModuleSpec = Field(..., description="Core module specification")
    asset: AssetReference = Field(..., description="3D asset reference")
    validation_rules: Dict[str, Any] = Field(default_factory=dict, description="Custom validation rules")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def module_id(self) -> str:
        return self.spec.module_id
    
    @property
    def module_type(self) -> ModuleType:
        return self.spec.type


class ModuleLibraryCache(BaseModel):
    """Cache metadata for module library"""
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    cache_version: str = Field(default="1.0")
    module_count: int = Field(default=0)
    checksum: Optional[str] = Field(None)


class ModuleLibrary:
    """
    Module library manager for loading, validating, and caching habitat modules.
    
    Provides access to predefined standard modules and supports custom module
    definitions with 3D assets and validation.
    """
    
    def __init__(self, assets_path: Optional[Path] = None, cache_ttl_hours: int = 24):
        self.assets_path = assets_path or Path("assets/modules")
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self._modules: Dict[str, ModuleDefinition] = {}
        self._cache_metadata: Optional[ModuleLibraryCache] = None
        self._initialized = False
        
        # Initialize with standard modules
        self._load_standard_modules()
    
    def _load_standard_modules(self):
        """Load predefined standard habitat modules"""
        
        # Sleep Quarter Module
        sleep_quarter = ModuleDefinition(
            spec=ModuleSpec(
                module_id="std_sleep_quarter",
                type=ModuleType.SLEEP_QUARTER,
                name="Standard Sleep Quarter",
                bbox_m=BoundingBox(x=2.0, y=2.0, z=2.5),
                mass_kg=450.0,
                power_w=75.0,
                stowage_m3=1.2,
                connectivity_ports=["port_main", "port_emergency"],
                adjacency_preferences=[ModuleType.MEDICAL, ModuleType.GALLEY],
                adjacency_restrictions=[ModuleType.MECHANICAL, ModuleType.AIRLOCK],
                metadata=ModuleMetadata(
                    description="Individual crew sleeping quarters with privacy partition and personal storage",
                    manufacturer="SpaceHab Systems",
                    model="SQ-2024",
                    certification="NASA-STD-3001"
                )
            ),
            asset=AssetReference(
                file_path="sleep_quarter.glb",
                format="glb",
                scale=1.0
            ),
            tags=["crew", "privacy", "rest", "personal"],
            validation_rules={
                "min_clearance_m": 0.6,
                "requires_ventilation": True,
                "noise_isolation": True
            }
        )
        
        # Galley Module
        galley = ModuleDefinition(
            spec=ModuleSpec(
                module_id="std_galley",
                type=ModuleType.GALLEY,
                name="Standard Galley",
                bbox_m=BoundingBox(x=3.0, y=2.5, z=2.2),
                mass_kg=850.0,
                power_w=2500.0,
                stowage_m3=2.8,
                connectivity_ports=["port_main", "port_service"],
                adjacency_preferences=[ModuleType.SLEEP_QUARTER, ModuleType.STORAGE],
                adjacency_restrictions=[ModuleType.LABORATORY, ModuleType.MECHANICAL],
                metadata=ModuleMetadata(
                    description="Food preparation and dining area with water recycling and waste management",
                    manufacturer="Galactic Kitchens Ltd",
                    model="GK-Pro-2024",
                    certification="FDA-Space-Approved"
                )
            ),
            asset=AssetReference(
                file_path="galley.glb",
                format="glb",
                scale=1.0
            ),
            tags=["food", "dining", "water", "waste", "social"],
            validation_rules={
                "requires_water_connection": True,
                "requires_waste_management": True,
                "fire_suppression": True,
                "ventilation_cfm": 150
            }
        )
        
        # Laboratory Module
        laboratory = ModuleDefinition(
            spec=ModuleSpec(
                module_id="std_laboratory",
                type=ModuleType.LABORATORY,
                name="Multi-Purpose Laboratory",
                bbox_m=BoundingBox(x=4.0, y=3.0, z=2.8),
                mass_kg=1200.0,
                power_w=3500.0,
                stowage_m3=4.5,
                connectivity_ports=["port_main", "port_data", "port_service"],
                adjacency_preferences=[ModuleType.STORAGE, ModuleType.MEDICAL],
                adjacency_restrictions=[ModuleType.GALLEY, ModuleType.SLEEP_QUARTER],
                metadata=ModuleMetadata(
                    description="Research laboratory with workbenches, microscopy, and sample storage",
                    manufacturer="Scientific Systems Corp",
                    model="Lab-Flex-2024",
                    certification="ISO-14644-Class-7"
                )
            ),
            asset=AssetReference(
                file_path="laboratory.glb",
                format="glb",
                scale=1.0
            ),
            tags=["research", "science", "experiments", "analysis"],
            validation_rules={
                "contamination_control": True,
                "vibration_isolation": True,
                "data_connectivity": True,
                "sample_storage_temp_c": [-80, 4]
            }
        )
        
        # Airlock Module
        airlock = ModuleDefinition(
            spec=ModuleSpec(
                module_id="std_airlock",
                type=ModuleType.AIRLOCK,
                name="Standard EVA Airlock",
                bbox_m=BoundingBox(x=2.5, y=2.5, z=3.0),
                mass_kg=950.0,
                power_w=500.0,
                stowage_m3=1.8,
                connectivity_ports=["port_internal", "port_external"],
                adjacency_preferences=[ModuleType.STORAGE, ModuleType.MECHANICAL],
                adjacency_restrictions=[ModuleType.GALLEY, ModuleType.SLEEP_QUARTER],
                metadata=ModuleMetadata(
                    description="EVA airlock with suit storage and life support interface",
                    manufacturer="Pressure Systems Inc",
                    model="AL-EVA-2024",
                    certification="NASA-STD-3001-Vol2"
                )
            ),
            asset=AssetReference(
                file_path="airlock.glb",
                format="glb",
                scale=1.0
            ),
            tags=["eva", "suits", "external", "pressure", "safety"],
            validation_rules={
                "pressure_rating_psi": 14.7,
                "suit_capacity": 2,
                "emergency_access": True,
                "external_connection": True
            }
        )
        
        # Mechanical Module
        mechanical = ModuleDefinition(
            spec=ModuleSpec(
                module_id="std_mechanical",
                type=ModuleType.MECHANICAL,
                name="Environmental Control & Life Support",
                bbox_m=BoundingBox(x=3.5, y=2.8, z=2.5),
                mass_kg=1800.0,
                power_w=1200.0,
                stowage_m3=1.0,
                connectivity_ports=["port_main", "port_service_1", "port_service_2"],
                adjacency_preferences=[ModuleType.AIRLOCK, ModuleType.STORAGE],
                adjacency_restrictions=[ModuleType.SLEEP_QUARTER, ModuleType.GALLEY],
                metadata=ModuleMetadata(
                    description="ECLSS systems including atmosphere processing, thermal control, and power distribution",
                    manufacturer="Life Support Technologies",
                    model="ECLSS-Integrated-2024",
                    certification="NASA-STD-3001-Vol1"
                )
            ),
            asset=AssetReference(
                file_path="mechanical.glb",
                format="glb",
                scale=1.0
            ),
            tags=["eclss", "atmosphere", "thermal", "power", "maintenance"],
            validation_rules={
                "noise_level_db": 65,
                "vibration_isolation": True,
                "maintenance_access": True,
                "redundancy_level": 2
            }
        )
        
        # Medical Module
        medical = ModuleDefinition(
            spec=ModuleSpec(
                module_id="std_medical",
                type=ModuleType.MEDICAL,
                name="Medical Bay",
                bbox_m=BoundingBox(x=3.0, y=2.5, z=2.5),
                mass_kg=750.0,
                power_w=800.0,
                stowage_m3=2.2,
                connectivity_ports=["port_main", "port_emergency"],
                adjacency_preferences=[ModuleType.SLEEP_QUARTER, ModuleType.LABORATORY],
                adjacency_restrictions=[ModuleType.MECHANICAL, ModuleType.AIRLOCK],
                metadata=ModuleMetadata(
                    description="Medical examination and treatment facility with emergency care capabilities",
                    manufacturer="Space Medical Systems",
                    model="MedBay-Compact-2024",
                    certification="FDA-Medical-Device"
                )
            ),
            asset=AssetReference(
                file_path="medical.glb",
                format="glb",
                scale=1.0
            ),
            tags=["medical", "health", "emergency", "treatment"],
            validation_rules={
                "sterile_environment": True,
                "emergency_access": True,
                "medical_gas_supply": True,
                "isolation_capability": True
            }
        )
        
        # Exercise Module
        exercise = ModuleDefinition(
            spec=ModuleSpec(
                module_id="std_exercise",
                type=ModuleType.EXERCISE,
                name="Exercise & Fitness Module",
                bbox_m=BoundingBox(x=4.0, y=3.5, z=2.8),
                mass_kg=900.0,
                power_w=1500.0,
                stowage_m3=1.5,
                connectivity_ports=["port_main"],
                adjacency_preferences=[ModuleType.MEDICAL, ModuleType.STORAGE],
                adjacency_restrictions=[ModuleType.LABORATORY, ModuleType.GALLEY],
                metadata=ModuleMetadata(
                    description="Exercise equipment and fitness area for crew health maintenance",
                    manufacturer="Zero-G Fitness Corp",
                    model="Fit-Space-2024",
                    certification="NASA-Exercise-Standard"
                )
            ),
            asset=AssetReference(
                file_path="exercise.glb",
                format="glb",
                scale=1.0
            ),
            tags=["fitness", "health", "exercise", "cardio", "strength"],
            validation_rules={
                "vibration_isolation": True,
                "noise_control": True,
                "safety_restraints": True,
                "air_circulation_cfm": 200
            }
        )
        
        # Storage Module
        storage = ModuleDefinition(
            spec=ModuleSpec(
                module_id="std_storage",
                type=ModuleType.STORAGE,
                name="General Storage Module",
                bbox_m=BoundingBox(x=2.5, y=2.0, z=2.0),
                mass_kg=300.0,
                power_w=50.0,
                stowage_m3=8.5,
                connectivity_ports=["port_main"],
                adjacency_preferences=[ModuleType.GALLEY, ModuleType.LABORATORY, ModuleType.AIRLOCK],
                adjacency_restrictions=[],
                metadata=ModuleMetadata(
                    description="Configurable storage with environmental controls for supplies and equipment",
                    manufacturer="Orbital Storage Solutions",
                    model="Store-Max-2024",
                    certification="NASA-Stowage-Standard"
                )
            ),
            asset=AssetReference(
                file_path="storage.glb",
                format="glb",
                scale=1.0
            ),
            tags=["storage", "supplies", "equipment", "inventory"],
            validation_rules={
                "temperature_range_c": [-20, 40],
                "humidity_control": True,
                "inventory_tracking": True,
                "access_control": False
            }
        )
        
        # Add all modules to the library
        modules = [
            sleep_quarter, galley, laboratory, airlock, 
            mechanical, medical, exercise, storage
        ]
        
        for module in modules:
            self._modules[module.module_id] = module
        
        self._initialized = True
        self._update_cache_metadata()
        
        logger.info(f"Loaded {len(modules)} standard modules into library")
    
    def _update_cache_metadata(self):
        """Update cache metadata"""
        module_data = json.dumps([m.model_dump(mode='json') for m in self._modules.values()], sort_keys=True, default=str)
        checksum = hashlib.md5(module_data.encode()).hexdigest()
        
        self._cache_metadata = ModuleLibraryCache(
            module_count=len(self._modules),
            checksum=checksum
        )
    
    def get_module(self, module_id: str) -> Optional[ModuleDefinition]:
        """Get a module by ID"""
        return self._modules.get(module_id)
    
    def get_modules_by_type(self, module_type: ModuleType) -> List[ModuleDefinition]:
        """Get all modules of a specific type"""
        return [m for m in self._modules.values() if m.module_type == module_type]
    
    def get_all_modules(self) -> List[ModuleDefinition]:
        """Get all modules in the library"""
        return list(self._modules.values())
    
    def search_modules(self, 
                      query: Optional[str] = None,
                      module_types: Optional[List[ModuleType]] = None,
                      tags: Optional[List[str]] = None,
                      max_mass_kg: Optional[float] = None,
                      max_power_w: Optional[float] = None) -> List[ModuleDefinition]:
        """
        Search modules with various filters
        
        Args:
            query: Text search in name and description
            module_types: Filter by module types
            tags: Filter by tags (any match)
            max_mass_kg: Maximum mass filter
            max_power_w: Maximum power filter
        
        Returns:
            List of matching modules
        """
        results = list(self._modules.values())
        
        if query:
            query_lower = query.lower()
            results = [
                m for m in results 
                if (query_lower in m.spec.name.lower() or 
                    (m.spec.metadata and m.spec.metadata.description and 
                     query_lower in m.spec.metadata.description.lower()))
            ]
        
        if module_types:
            type_set = set(module_types)
            results = [m for m in results if m.module_type in type_set]
        
        if tags:
            tag_set = set(tag.lower() for tag in tags)
            results = [
                m for m in results 
                if any(tag.lower() in tag_set for tag in m.tags)
            ]
        
        if max_mass_kg is not None:
            results = [m for m in results if m.spec.mass_kg <= max_mass_kg]
        
        if max_power_w is not None:
            results = [m for m in results if m.spec.power_w <= max_power_w]
        
        return results
    
    def validate_module(self, module: ModuleDefinition) -> List[str]:
        """
        Validate a module definition
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Basic spec validation is handled by Pydantic
        try:
            module.spec.model_validate(module.spec.model_dump())
        except Exception as e:
            errors.append(f"Module spec validation failed: {str(e)}")
        
        # Asset validation
        if self.assets_path:
            asset_path = self.assets_path / module.asset.file_path
            if not asset_path.exists():
                errors.append(f"Asset file not found: {module.asset.file_path}")
        
        # Custom validation rules
        validation_rules = module.validation_rules
        
        # Check required connections for certain module types
        if module.module_type == ModuleType.AIRLOCK:
            if len(module.spec.connectivity_ports) < 2:
                errors.append("Airlock modules must have at least 2 connectivity ports")
        
        if module.module_type == ModuleType.GALLEY:
            if validation_rules.get("requires_water_connection") and "port_service" not in module.spec.connectivity_ports:
                errors.append("Galley modules require a service port for water connection")
        
        # Check power requirements
        if module.spec.power_w > 5000:
            errors.append("Module power consumption exceeds 5kW limit")
        
        # Check mass limits
        if module.spec.mass_kg > 2000:
            errors.append("Module mass exceeds 2000kg limit")
        
        # Check stowage volume vs bounding box
        if module.spec.stowage_m3 > module.spec.bbox_m.volume * 0.9:
            errors.append("Stowage volume cannot exceed 90% of module bounding box")
        
        return errors
    
    def add_custom_module(self, module: ModuleDefinition) -> bool:
        """
        Add a custom module to the library
        
        Returns:
            True if added successfully, False if validation failed
        """
        errors = self.validate_module(module)
        if errors:
            logger.warning(f"Module validation failed for {module.module_id}: {errors}")
            return False
        
        # Check for ID conflicts
        if module.module_id in self._modules:
            logger.warning(f"Module ID {module.module_id} already exists")
            return False
        
        self._modules[module.module_id] = module
        self._update_cache_metadata()
        
        logger.info(f"Added custom module: {module.module_id}")
        return True
    
    def remove_module(self, module_id: str) -> bool:
        """Remove a module from the library"""
        if module_id.startswith("std_"):
            logger.warning(f"Cannot remove standard module: {module_id}")
            return False
        
        if module_id in self._modules:
            del self._modules[module_id]
            self._update_cache_metadata()
            logger.info(f"Removed module: {module_id}")
            return True
        
        return False
    
    def get_compatibility_matrix(self) -> Dict[str, Dict[str, str]]:
        """
        Generate module compatibility matrix
        
        Returns:
            Dict mapping module pairs to compatibility status
        """
        matrix = {}
        modules = list(self._modules.values())
        
        for i, module_a in enumerate(modules):
            matrix[module_a.module_id] = {}
            
            for module_b in modules:
                if module_a.module_id == module_b.module_id:
                    matrix[module_a.module_id][module_b.module_id] = "self"
                elif module_b.module_type in module_a.spec.adjacency_restrictions:
                    matrix[module_a.module_id][module_b.module_id] = "restricted"
                elif module_b.module_type in module_a.spec.adjacency_preferences:
                    matrix[module_a.module_id][module_b.module_id] = "preferred"
                else:
                    matrix[module_a.module_id][module_b.module_id] = "neutral"
        
        return matrix
    
    def get_library_stats(self) -> Dict[str, Any]:
        """Get library statistics"""
        modules = list(self._modules.values())
        
        type_counts = {}
        total_mass = 0
        total_power = 0
        total_stowage = 0
        
        for module in modules:
            if hasattr(module.module_type, 'value'):
                module_type = module.module_type.value
            else:
                module_type = str(module.module_type)
            type_counts[module_type] = type_counts.get(module_type, 0) + 1
            total_mass += module.spec.mass_kg
            total_power += module.spec.power_w
            total_stowage += module.spec.stowage_m3
        
        return {
            "total_modules": len(modules),
            "module_types": type_counts,
            "total_mass_kg": total_mass,
            "total_power_w": total_power,
            "total_stowage_m3": total_stowage,
            "cache_metadata": self._cache_metadata.model_dump() if self._cache_metadata else None
        }
    
    def export_library(self, file_path: Path) -> bool:
        """Export library to JSON file"""
        try:
            export_data = {
                "metadata": self._cache_metadata.model_dump(mode='json') if self._cache_metadata else None,
                "modules": [m.model_dump(mode='json') for m in self._modules.values()]
            }
            
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Exported library to {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to export library: {str(e)}")
            return False
    
    def import_library(self, file_path: Path, merge: bool = True) -> bool:
        """Import library from JSON file"""
        try:
            with open(file_path, 'r') as f:
                import_data = json.load(f)
            
            if not merge:
                # Clear existing custom modules (keep standard ones)
                self._modules = {
                    k: v for k, v in self._modules.items() 
                    if k.startswith("std_")
                }
            
            # Import modules
            imported_count = 0
            for module_data in import_data.get("modules", []):
                try:
                    module = ModuleDefinition.model_validate(module_data)
                    if self.add_custom_module(module):
                        imported_count += 1
                except Exception as e:
                    logger.warning(f"Failed to import module: {str(e)}")
            
            logger.info(f"Imported {imported_count} modules from {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to import library: {str(e)}")
            return False


# Global module library instance
_module_library: Optional[ModuleLibrary] = None


def get_module_library() -> ModuleLibrary:
    """Get the global module library instance"""
    global _module_library
    if _module_library is None:
        _module_library = ModuleLibrary()
    return _module_library


def initialize_module_library(assets_path: Optional[Path] = None, cache_ttl_hours: int = 24) -> ModuleLibrary:
    """Initialize the global module library with custom settings"""
    global _module_library
    _module_library = ModuleLibrary(assets_path=assets_path, cache_ttl_hours=cache_ttl_hours)
    return _module_library