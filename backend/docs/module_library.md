# Module Library Documentation

## Overview

The HabitatCanvas Module Library provides a comprehensive system for managing predefined habitat modules with their specifications, 3D assets, and validation rules. It supports both standard modules (provided by the system) and custom modules (created by users).

## Features

### Standard Modules

The library includes 8 predefined standard habitat modules:

1. **Sleep Quarter** (`std_sleep_quarter`)
   - Individual crew sleeping quarters with privacy partition
   - Dimensions: 2.0 x 2.0 x 2.5 meters
   - Mass: 450 kg, Power: 75 W, Stowage: 1.2 m³
   - Prefers: Medical, Galley
   - Restricts: Mechanical, Airlock

2. **Galley** (`std_galley`)
   - Food preparation and dining area
   - Dimensions: 3.0 x 2.5 x 2.2 meters
   - Mass: 850 kg, Power: 2500 W, Stowage: 2.8 m³
   - Prefers: Sleep Quarter, Storage
   - Restricts: Laboratory, Mechanical

3. **Laboratory** (`std_laboratory`)
   - Multi-purpose research laboratory
   - Dimensions: 4.0 x 3.0 x 2.8 meters
   - Mass: 1200 kg, Power: 3500 W, Stowage: 4.5 m³
   - Prefers: Storage, Medical
   - Restricts: Galley, Sleep Quarter

4. **Airlock** (`std_airlock`)
   - EVA airlock with suit storage
   - Dimensions: 2.5 x 2.5 x 3.0 meters
   - Mass: 950 kg, Power: 500 W, Stowage: 1.8 m³
   - Prefers: Storage, Mechanical
   - Restricts: Galley, Sleep Quarter

5. **Mechanical** (`std_mechanical`)
   - Environmental Control & Life Support Systems
   - Dimensions: 3.5 x 2.8 x 2.5 meters
   - Mass: 1800 kg, Power: 1200 W, Stowage: 1.0 m³
   - Prefers: Airlock, Storage
   - Restricts: Sleep Quarter, Galley

6. **Medical** (`std_medical`)
   - Medical examination and treatment facility
   - Dimensions: 3.0 x 2.5 x 2.5 meters
   - Mass: 750 kg, Power: 800 W, Stowage: 2.2 m³
   - Prefers: Sleep Quarter, Laboratory
   - Restricts: Mechanical, Airlock

7. **Exercise** (`std_exercise`)
   - Exercise and fitness area
   - Dimensions: 4.0 x 3.5 x 2.8 meters
   - Mass: 900 kg, Power: 1500 W, Stowage: 1.5 m³
   - Prefers: Medical, Storage
   - Restricts: Laboratory, Galley

8. **Storage** (`std_storage`)
   - General storage with environmental controls
   - Dimensions: 2.5 x 2.0 x 2.0 meters
   - Mass: 300 kg, Power: 50 W, Stowage: 8.5 m³
   - Prefers: Galley, Laboratory, Airlock
   - No restrictions

### Module Library API

#### Core Endpoints

- `GET /api/v1/module-library/` - List all modules with optional filtering
- `GET /api/v1/module-library/{module_id}` - Get specific module by ID
- `GET /api/v1/module-library/types/{module_type}` - Get modules by type
- `POST /api/v1/module-library/` - Add custom module
- `DELETE /api/v1/module-library/{module_id}` - Remove custom module
- `POST /api/v1/module-library/validate` - Validate module definition

#### Search and Analysis

- `GET /api/v1/module-library/compatibility/matrix` - Get compatibility matrix
- `GET /api/v1/module-library/stats` - Get library statistics

#### Asset Management

- `GET /api/v1/module-library/{module_id}/asset` - Download 3D asset file
- `GET /api/v1/module-library/{module_id}/asset/info` - Get asset information
- `POST /api/v1/module-library/{module_id}/asset/upload` - Upload new asset
- `GET /api/v1/module-library/assets/stats` - Get asset statistics

#### Import/Export

- `POST /api/v1/module-library/export` - Export library to JSON
- `POST /api/v1/module-library/import` - Import modules from JSON

### Search Capabilities

The module library supports advanced search with multiple filters:

```python
# Search by text query
modules = library.search_modules(query="sleep")

# Filter by module types
modules = library.search_modules(module_types=[ModuleType.LABORATORY, ModuleType.MEDICAL])

# Filter by mass and power constraints
modules = library.search_modules(max_mass_kg=1000.0, max_power_w=2000.0)

# Filter by tags
modules = library.search_modules(tags=["research", "science"])

# Combined filters
modules = library.search_modules(
    query="storage",
    module_types=[ModuleType.STORAGE],
    max_mass_kg=500.0,
    tags=["supplies"]
)
```

### Validation Rules

The library enforces several validation rules:

1. **Mass Limits**: Modules cannot exceed 2000 kg
2. **Power Limits**: Modules cannot exceed 5000 W
3. **Stowage Constraints**: Stowage volume cannot exceed 90% of bounding box volume
4. **Connectivity Requirements**: Certain module types require specific ports
5. **Asset Validation**: 3D assets must exist and be in supported formats
6. **Adjacency Rules**: Modules have preferences and restrictions for neighbors

### 3D Asset Management

The asset manager handles 3D models for modules:

- **Supported Formats**: GLTF, GLB, OBJ, FBX
- **Validation**: File integrity, format checking, metadata extraction
- **Caching**: Automatic caching with checksums and access tracking
- **Scaling**: Proper scaling (1 unit = 1 meter)

### Compatibility Matrix

The library generates a compatibility matrix showing relationships between modules:

- **Preferred**: Modules that work well together
- **Restricted**: Modules that should not be adjacent
- **Neutral**: No specific preference or restriction
- **Self**: Same module (not applicable)

### Usage Examples

#### Basic Usage

```python
from app.models.module_library import get_module_library

# Get library instance
library = get_module_library()

# Get all modules
all_modules = library.get_all_modules()

# Get specific module
sleep_module = library.get_module("std_sleep_quarter")

# Search for laboratory modules
lab_modules = library.get_modules_by_type(ModuleType.LABORATORY)
```

#### Custom Module Creation

```python
from app.models.module_library import ModuleDefinition, AssetReference
from app.models.base import ModuleSpec, ModuleType, BoundingBox

# Create custom module
custom_module = ModuleDefinition(
    spec=ModuleSpec(
        module_id="custom_workshop",
        type=ModuleType.LABORATORY,
        name="Custom Workshop",
        bbox_m=BoundingBox(x=3.0, y=3.0, z=2.5),
        mass_kg=800.0,
        power_w=1500.0,
        stowage_m3=3.0,
        connectivity_ports=["port_main", "port_power"]
    ),
    asset=AssetReference(
        file_path="custom_workshop.glb",
        format="glb"
    ),
    tags=["workshop", "manufacturing", "custom"]
)

# Add to library
success = library.add_custom_module(custom_module)
```

#### Validation

```python
# Validate module
errors = library.validate_module(custom_module)
if errors:
    print(f"Validation errors: {errors}")
else:
    print("Module is valid")
```

### Configuration

The module library can be configured during initialization:

```python
from pathlib import Path
from app.models.module_library import initialize_module_library

# Initialize with custom settings
library = initialize_module_library(
    assets_path=Path("custom/assets/path"),
    cache_ttl_hours=48
)
```

### Error Handling

The library provides comprehensive error handling:

- **Validation Errors**: Detailed messages for constraint violations
- **Asset Errors**: File not found, format issues, corruption detection
- **Compatibility Errors**: Adjacency rule violations
- **Import/Export Errors**: File format issues, permission problems

### Performance Considerations

- **Caching**: Module definitions and assets are cached for performance
- **Lazy Loading**: Assets are loaded on-demand
- **Batch Operations**: Support for bulk import/export operations
- **Memory Management**: Automatic cleanup of old cache entries

### Integration with Layout Generation

The module library integrates seamlessly with the layout generation system:

1. **Module Selection**: Layout generator queries available modules
2. **Constraint Checking**: Validates adjacency rules and compatibility
3. **Asset Loading**: Provides 3D assets for visualization
4. **Performance Metrics**: Supplies module specifications for analysis

This comprehensive module library system enables rapid prototyping and iteration of habitat layouts while maintaining engineering accuracy and design constraints.