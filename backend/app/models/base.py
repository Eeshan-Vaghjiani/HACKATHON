from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator, computed_field
from enum import Enum
from datetime import datetime
import math


class ModuleType(str, Enum):
    SLEEP_QUARTER = "sleep_quarter"
    GALLEY = "galley"
    LABORATORY = "laboratory"
    AIRLOCK = "airlock"
    MECHANICAL = "mechanical"
    MEDICAL = "medical"
    EXERCISE = "exercise"
    STORAGE = "storage"


class EnvelopeType(str, Enum):
    CYLINDER = "cylinder"
    TORUS = "torus"
    BOX = "box"
    FREEFORM = "freeform"


class CoordinateFrame(str, Enum):
    LOCAL = "local"
    GLOBAL = "global"


class EnvelopeMetadata(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable envelope name")
    creator: str = Field(..., min_length=1, max_length=255, description="Creator identifier")
    created: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    version: Optional[str] = Field(None, max_length=50, description="Version identifier")
    description: Optional[str] = Field(None, max_length=1000, description="Detailed description")


class EnvelopeConstraints(BaseModel):
    min_volume: Optional[float] = Field(None, gt=0, description="Minimum volume in cubic meters")
    max_volume: Optional[float] = Field(None, gt=0, description="Maximum volume in cubic meters")
    min_dimension: Optional[float] = Field(None, gt=0, description="Minimum dimension in meters")
    max_dimension: Optional[float] = Field(None, gt=0, description="Maximum dimension in meters")

    @model_validator(mode='after')
    def validate_constraints(self):
        if self.min_volume is not None and self.max_volume is not None and self.min_volume >= self.max_volume:
            raise ValueError('min_volume must be less than max_volume')
        
        if self.min_dimension is not None and self.max_dimension is not None and self.min_dimension >= self.max_dimension:
            raise ValueError('min_dimension must be less than max_dimension')
        
        return self


class EnvelopeSpec(BaseModel):
    id: str = Field(..., min_length=1, max_length=255, description="Unique envelope identifier")
    type: EnvelopeType = Field(..., description="Envelope geometry type")
    params: Dict[str, float] = Field(..., description="Type-specific geometric parameters")
    coordinate_frame: CoordinateFrame = Field(default=CoordinateFrame.LOCAL, description="Coordinate reference frame")
    metadata: EnvelopeMetadata = Field(..., description="Envelope metadata")
    constraints: Optional[EnvelopeConstraints] = Field(None, description="Optional geometric constraints")

    @field_validator('params')
    @classmethod
    def validate_params(cls, v, info):
        envelope_type = info.data.get('type') if info.data else None
        if not envelope_type:
            return v
        
        if envelope_type == EnvelopeType.CYLINDER:
            required_params = {'radius', 'length'}
            if not required_params.issubset(v.keys()):
                raise ValueError(f'Cylinder envelope requires parameters: {required_params}')
            if v['radius'] <= 0:
                raise ValueError('Cylinder radius must be positive')
            if v['length'] <= 0:
                raise ValueError('Cylinder length must be positive')
        
        elif envelope_type == EnvelopeType.BOX:
            required_params = {'width', 'height', 'depth'}
            if not required_params.issubset(v.keys()):
                raise ValueError(f'Box envelope requires parameters: {required_params}')
            for param in required_params:
                if v[param] <= 0:
                    raise ValueError(f'Box {param} must be positive')
        
        elif envelope_type == EnvelopeType.TORUS:
            required_params = {'major_radius', 'minor_radius'}
            if not required_params.issubset(v.keys()):
                raise ValueError(f'Torus envelope requires parameters: {required_params}')
            if v['major_radius'] <= 0:
                raise ValueError('Torus major_radius must be positive')
            if v['minor_radius'] <= 0:
                raise ValueError('Torus minor_radius must be positive')
            if v['minor_radius'] >= v['major_radius']:
                raise ValueError('Torus minor_radius must be less than major_radius')
        
        return v

    @computed_field
    @property
    def volume(self) -> float:
        """Calculate envelope volume based on type and parameters"""
        if self.type == EnvelopeType.CYLINDER:
            radius = self.params['radius']
            length = self.params['length']
            return math.pi * radius * radius * length
        
        elif self.type == EnvelopeType.BOX:
            return self.params['width'] * self.params['height'] * self.params['depth']
        
        elif self.type == EnvelopeType.TORUS:
            major_r = self.params['major_radius']
            minor_r = self.params['minor_radius']
            return 2 * math.pi * math.pi * major_r * minor_r * minor_r
        
        elif self.type == EnvelopeType.FREEFORM:
            return self.params.get('volume', 0.0)
        
        return 0.0

    model_config = {
        "use_enum_values": True,
        "json_schema_extra": {
            "example": {
                "id": "envelope_001",
                "type": "cylinder",
                "params": {"radius": 3.0, "length": 12.0},
                "coordinate_frame": "local",
                "metadata": {
                    "name": "ISS Module",
                    "creator": "designer_001",
                    "created": "2024-01-01T00:00:00Z"
                },
                "constraints": {
                    "min_volume": 100.0,
                    "max_volume": 1000.0
                }
            }
        }
    }


class ModuleMetadata(BaseModel):
    description: Optional[str] = Field(None, max_length=1000, description="Module description")
    manufacturer: Optional[str] = Field(None, max_length=255, description="Manufacturer name")
    model: Optional[str] = Field(None, max_length=255, description="Model identifier")
    certification: Optional[str] = Field(None, max_length=255, description="Certification standard")


class BoundingBox(BaseModel):
    x: float = Field(..., gt=0, description="Width in meters")
    y: float = Field(..., gt=0, description="Height in meters")
    z: float = Field(..., gt=0, description="Depth in meters")

    @computed_field
    @property
    def volume(self) -> float:
        """Calculate bounding box volume"""
        return self.x * self.y * self.z

    @computed_field
    @property
    def surface_area(self) -> float:
        """Calculate bounding box surface area"""
        return 2 * (self.x * self.y + self.y * self.z + self.x * self.z)


class ModuleSpec(BaseModel):
    module_id: str = Field(..., min_length=1, max_length=255, description="Unique module identifier")
    type: ModuleType = Field(..., description="Module functional type")
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable module name")
    bbox_m: BoundingBox = Field(..., description="Bounding box dimensions in meters")
    mass_kg: float = Field(..., gt=0.1, le=50000, description="Module mass in kilograms")
    power_w: float = Field(..., ge=0, le=100000, description="Power consumption in watts")
    stowage_m3: float = Field(..., ge=0, le=1000, description="Available stowage volume in cubic meters")
    connectivity_ports: List[str] = Field(default_factory=list, description="Available connection ports")
    adjacency_preferences: List[ModuleType] = Field(default_factory=list, description="Preferred adjacent module types")
    adjacency_restrictions: List[ModuleType] = Field(default_factory=list, description="Restricted adjacent module types")
    metadata: Optional[ModuleMetadata] = Field(None, description="Optional module metadata")

    @model_validator(mode='after')
    def validate_module_constraints(self):
        # Validate stowage volume
        if self.stowage_m3 > self.bbox_m.volume:
            raise ValueError('Stowage volume cannot exceed module bounding box volume')
        
        # Validate adjacency rules
        conflicts = set(self.adjacency_preferences) & set(self.adjacency_restrictions)
        if conflicts:
            raise ValueError(f'Module types cannot be both preferred and restricted: {conflicts}')
        
        return self

    @computed_field
    @property
    def density_kg_m3(self) -> float:
        """Calculate module density in kg/m³"""
        return self.mass_kg / self.bbox_m.volume

    @computed_field
    @property
    def power_density_w_m3(self) -> float:
        """Calculate power density in W/m³"""
        return self.power_w / self.bbox_m.volume

    model_config = {
        "use_enum_values": True,
        "json_schema_extra": {
            "example": {
                "module_id": "sleep_001",
                "type": "sleep_quarter",
                "name": "Sleep Quarter A",
                "bbox_m": {"x": 2.0, "y": 2.0, "z": 2.5},
                "mass_kg": 500.0,
                "power_w": 100.0,
                "stowage_m3": 1.5,
                "connectivity_ports": ["port_1", "port_2"],
                "adjacency_preferences": ["galley", "medical"],
                "adjacency_restrictions": ["mechanical"],
                "metadata": {
                    "description": "Crew sleeping quarters with privacy partition",
                    "manufacturer": "SpaceHab Inc",
                    "model": "SQ-2024"
                }
            }
        }
    }


class ModulePlacement(BaseModel):
    module_id: str = Field(..., min_length=1, max_length=255, description="Module identifier")
    type: ModuleType = Field(..., description="Module functional type")
    position: List[float] = Field(..., min_length=3, max_length=3, description="[x, y, z] position in meters")
    rotation_deg: float = Field(..., description="Rotation around Z-axis in degrees")
    connections: List[str] = Field(default_factory=list, description="Connected module IDs")
    is_valid: Optional[bool] = Field(None, description="Validation status of placement")
    validation_errors: Optional[List[str]] = Field(None, description="List of validation error messages")

    @field_validator('position')
    @classmethod
    def validate_position(cls, v):
        if len(v) != 3:
            raise ValueError('Position must be a 3D coordinate [x, y, z]')
        
        for i, coord in enumerate(v):
            if not isinstance(coord, (int, float)) or not math.isfinite(coord):
                raise ValueError(f'Position coordinate {i} must be a finite number')
        
        return v

    @field_validator('rotation_deg')
    @classmethod
    def validate_rotation(cls, v):
        if not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError('Rotation must be a finite number')
        
        # Normalize rotation to 0-360 range
        return v % 360

    @computed_field
    @property
    def position_magnitude(self) -> float:
        """Calculate distance from origin"""
        return math.sqrt(sum(coord ** 2 for coord in self.position))

    model_config = {
        "use_enum_values": True,
        "json_schema_extra": {
            "example": {
                "module_id": "sleep_001",
                "type": "sleep_quarter",
                "position": [0.0, 0.0, 0.0],
                "rotation_deg": 0.0,
                "connections": ["galley_001"],
                "is_valid": True,
                "validation_errors": None
            }
        }
    }


class MissionConstraints(BaseModel):
    max_crew_size: Optional[int] = Field(None, gt=0, le=50, description="Maximum allowed crew size")
    max_duration: Optional[int] = Field(None, gt=0, le=5000, description="Maximum mission duration in days")
    min_safety_margin: Optional[float] = Field(None, ge=0, le=1, description="Minimum required safety margin")


class MissionParameters(BaseModel):
    crew_size: int = Field(..., gt=0, le=20, description="Number of crew members")
    duration_days: int = Field(..., gt=0, le=1000, description="Mission duration in days")
    priority_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "safety": 0.3,
            "efficiency": 0.25,
            "mass": 0.2,
            "power": 0.15,
            "comfort": 0.1
        },
        description="Optimization priority weights (must sum to 1.0)"
    )
    activity_schedule: Dict[str, float] = Field(
        default_factory=lambda: {
            "sleep": 8.0,
            "work": 8.0,
            "exercise": 2.0,
            "meals": 3.0,
            "personal": 3.0
        },
        description="Daily time allocation per activity type in hours"
    )
    emergency_scenarios: List[str] = Field(
        default_factory=lambda: ["fire", "depressurization", "medical"],
        description="Emergency scenarios to simulate"
    )
    constraints: Optional[MissionConstraints] = Field(None, description="Optional mission constraints")

    @field_validator('priority_weights')
    @classmethod
    def validate_priority_weights(cls, v):
        # Check that all weights are non-negative
        for key, weight in v.items():
            if weight < 0:
                raise ValueError(f'Priority weight for {key} cannot be negative')
        
        # Check that weights sum to approximately 1.0
        total = sum(v.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f'Priority weights must sum to 1.0, got {total:.3f}')
        
        return v

    @field_validator('activity_schedule')
    @classmethod
    def validate_activity_schedule(cls, v):
        # Check that all times are non-negative
        for activity, time in v.items():
            if time < 0:
                raise ValueError(f'Activity time for {activity} cannot be negative')
        
        # Warn if total exceeds 24 hours (but don't fail validation)
        total_time = sum(v.values())
        if total_time > 24:
            # In a real application, you might want to use logging here
            pass  # Could add warning mechanism
        
        return v

    @model_validator(mode='after')
    def validate_mission_constraints(self):
        if self.constraints:
            if self.constraints.max_crew_size and self.crew_size > self.constraints.max_crew_size:
                raise ValueError(f'Crew size {self.crew_size} exceeds maximum allowed {self.constraints.max_crew_size}')
            
            if self.constraints.max_duration and self.duration_days > self.constraints.max_duration:
                raise ValueError(f'Mission duration {self.duration_days} exceeds maximum allowed {self.constraints.max_duration}')
        
        return self

    @computed_field
    @property
    def total_crew_hours(self) -> float:
        """Calculate total crew-hours for the mission"""
        return self.crew_size * self.duration_days * 24

    @computed_field
    @property
    def daily_activity_total(self) -> float:
        """Calculate total daily activity time"""
        return sum(self.activity_schedule.values())

    model_config = {
        "json_schema_extra": {
            "example": {
                "crew_size": 4,
                "duration_days": 180,
                "priority_weights": {
                    "safety": 0.3,
                    "efficiency": 0.25,
                    "mass": 0.2,
                    "power": 0.15,
                    "comfort": 0.1
                },
                "activity_schedule": {
                    "sleep": 8.0,
                    "work": 8.0,
                    "exercise": 2.0,
                    "meals": 3.0,
                    "personal": 3.0
                },
                "emergency_scenarios": ["fire", "depressurization"],
                "constraints": {
                    "max_crew_size": 6,
                    "max_duration": 365,
                    "min_safety_margin": 0.2
                }
            }
        }
    }


class PerformanceMetrics(BaseModel):
    mean_transit_time: float = Field(..., ge=0, description="Average transit time between modules in seconds")
    egress_time: float = Field(..., ge=0, description="Emergency egress time to airlocks in seconds")
    mass_total: float = Field(..., ge=0, description="Total habitat mass in kilograms")
    power_budget: float = Field(..., ge=0, description="Total power consumption in watts")
    thermal_margin: float = Field(..., ge=-1, le=1, description="Thermal margin as fraction (negative means over budget)")
    lss_margin: float = Field(..., ge=-1, le=1, description="Life Support Systems margin as fraction")
    stowage_utilization: float = Field(..., ge=0, le=2, description="Stowage utilization ratio (>1 means overcrowded)")
    
    # Additional computed metrics
    connectivity_score: Optional[float] = Field(None, ge=0, le=1, description="Module connectivity quality score")
    safety_score: Optional[float] = Field(None, ge=0, le=1, description="Overall safety assessment score")
    efficiency_score: Optional[float] = Field(None, ge=0, le=1, description="Operational efficiency score")
    volume_utilization: Optional[float] = Field(None, ge=0, le=1, description="Habitat volume utilization ratio")

    @field_validator('thermal_margin')
    @classmethod
    def validate_thermal_margin(cls, v):
        if v < -0.5:
            raise ValueError('Thermal margin cannot be less than -50% (critical thermal overload)')
        return v

    @field_validator('lss_margin')
    @classmethod
    def validate_lss_margin(cls, v):
        if v < -0.2:
            raise ValueError('LSS margin cannot be less than -20% (life support failure risk)')
        return v

    @computed_field
    @property
    def overall_score(self) -> float:
        """Calculate weighted overall performance score"""
        # Base scores from required metrics
        transit_score = max(0, 1 - (self.mean_transit_time / 300))  # Normalize against 5-minute baseline
        egress_score = max(0, 1 - (self.egress_time / 600))  # Normalize against 10-minute baseline
        thermal_score = max(0, self.thermal_margin)
        lss_score = max(0, self.lss_margin)
        stowage_score = max(0, 1 - abs(self.stowage_utilization - 0.8))  # Optimal around 80%
        
        # Include optional scores if available
        scores = [transit_score, egress_score, thermal_score, lss_score, stowage_score]
        weights = [0.2, 0.25, 0.2, 0.25, 0.1]
        
        if self.connectivity_score is not None:
            scores.append(self.connectivity_score)
            weights.append(0.1)
        
        if self.safety_score is not None:
            scores.append(self.safety_score)
            weights.append(0.15)
        
        if self.efficiency_score is not None:
            scores.append(self.efficiency_score)
            weights.append(0.1)
        
        # Normalize weights
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        return sum(score * weight for score, weight in zip(scores, normalized_weights))

    @computed_field
    @property
    def critical_issues(self) -> List[str]:
        """Identify critical performance issues"""
        issues = []
        
        if self.thermal_margin < 0.1:
            issues.append("Low thermal margin - cooling system may be inadequate")
        
        if self.lss_margin < 0.2:
            issues.append("Low LSS margin - life support capacity may be insufficient")
        
        if self.stowage_utilization > 1.0:
            issues.append("Stowage overcrowding - insufficient storage capacity")
        
        if self.egress_time > 300:  # 5 minutes
            issues.append("Excessive egress time - emergency evacuation may be compromised")
        
        if self.mean_transit_time > 180:  # 3 minutes
            issues.append("High transit times - operational efficiency may be impacted")
        
        return issues

    model_config = {
        "json_schema_extra": {
            "example": {
                "mean_transit_time": 45.5,
                "egress_time": 120.0,
                "mass_total": 15000.0,
                "power_budget": 2500.0,
                "thermal_margin": 0.155,
                "lss_margin": 0.20,
                "stowage_utilization": 0.85,
                "connectivity_score": 0.92,
                "safety_score": 0.88,
                "efficiency_score": 0.76,
                "volume_utilization": 0.68
            }
        }
    }


class LayoutMetadata(BaseModel):
    name: Optional[str] = Field(None, max_length=255, description="Human-readable layout name")
    created: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    generation_params: Optional[Dict[str, Any]] = Field(None, description="Parameters used for layout generation")
    version: Optional[str] = Field(None, max_length=50, description="Layout version identifier")


class LayoutConstraints(BaseModel):
    total_mass: Optional[float] = Field(None, gt=0, description="Maximum total mass in kg")
    total_power: Optional[float] = Field(None, gt=0, description="Maximum total power in watts")
    min_clearance: Optional[float] = Field(None, gt=0, description="Minimum clearance between modules in meters")


class LayoutSpec(BaseModel):
    layout_id: str = Field(..., min_length=1, max_length=255, description="Unique layout identifier")
    envelope_id: str = Field(..., min_length=1, max_length=255, description="Associated envelope identifier")
    modules: List[ModulePlacement] = Field(..., min_length=1, description="Module placements in the layout")
    kpis: PerformanceMetrics = Field(..., description="Computed performance metrics")
    explainability: str = Field(..., min_length=10, description="Natural language explanation of layout decisions")
    metadata: Optional[LayoutMetadata] = Field(None, description="Layout metadata")
    constraints: Optional[LayoutConstraints] = Field(None, description="Layout constraints")

    @field_validator('modules')
    @classmethod
    def validate_modules(cls, v):
        if not v:
            raise ValueError('Layout must contain at least one module')
        
        # Check for duplicate module IDs
        module_ids = [module.module_id for module in v]
        if len(module_ids) != len(set(module_ids)):
            raise ValueError('Layout cannot contain duplicate module IDs')
        
        return v

    @field_validator('explainability')
    @classmethod
    def validate_explainability(cls, v):
        if len(v.strip()) < 10:
            raise ValueError('Explainability text must be at least 10 characters long')
        return v.strip()

    @model_validator(mode='after')
    def validate_layout_constraints(self):
        if not self.constraints or not self.modules:
            return self
        
        # Validate total mass constraint
        if self.constraints.total_mass:
            # Note: This would require module specs to calculate actual mass
            # For now, we'll skip this validation as it requires additional data
            pass
        
        # Validate total power constraint
        if self.constraints.total_power:
            # Note: Similar to mass, this requires module specs
            pass
        
        return self

    @computed_field
    @property
    def module_count(self) -> int:
        """Number of modules in the layout"""
        return len(self.modules)

    @computed_field
    @property
    def module_types_count(self) -> Dict[str, int]:
        """Count of each module type in the layout"""
        type_counts = {}
        for module in self.modules:
            module_type = module.type if isinstance(module.type, str) else module.type.value
            type_counts[module_type] = type_counts.get(module_type, 0) + 1
        return type_counts

    @computed_field
    @property
    def has_airlock(self) -> bool:
        """Check if layout contains at least one airlock"""
        return any(module.type == ModuleType.AIRLOCK for module in self.modules)

    @computed_field
    @property
    def layout_bounds(self) -> Dict[str, float]:
        """Calculate the bounding box of all modules"""
        if not self.modules:
            return {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0, "min_z": 0, "max_z": 0}
        
        positions = [module.position for module in self.modules]
        
        return {
            "min_x": min(pos[0] for pos in positions),
            "max_x": max(pos[0] for pos in positions),
            "min_y": min(pos[1] for pos in positions),
            "max_y": max(pos[1] for pos in positions),
            "min_z": min(pos[2] for pos in positions),
            "max_z": max(pos[2] for pos in positions)
        }

    model_config = {
        "use_enum_values": True,
        "json_schema_extra": {
            "example": {
                "layout_id": "layout_001",
                "envelope_id": "envelope_001",
                "modules": [
                    {
                        "module_id": "sleep_001",
                        "type": "sleep_quarter",
                        "position": [0.0, 0.0, 0.0],
                        "rotation_deg": 0.0,
                        "connections": ["galley_001"]
                    }
                ],
                "kpis": {
                    "mean_transit_time": 45.5,
                    "egress_time": 120.0,
                    "mass_total": 15000.0,
                    "power_budget": 2500.0,
                    "thermal_margin": 0.155,
                    "lss_margin": 0.20,
                    "stowage_utilization": 0.85
                },
                "explainability": "This layout prioritizes crew safety by placing airlocks near high-traffic areas and ensuring short egress paths.",
                "metadata": {
                    "name": "Safety-Optimized Layout v1",
                    "generation_params": {"algorithm": "nsga2", "generations": 100}
                },
                "constraints": {
                    "total_mass": 20000.0,
                    "total_power": 5000.0,
                    "min_clearance": 0.6
                }
            }
        }
    }