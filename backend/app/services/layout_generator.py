"""
Basic Layout Generation Algorithm for HabitatCanvas

This module implements a simple random layout placement algorithm with
collision detection, connectivity validation, and basic scoring.
"""

import random
import math
import uuid
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime
import logging

from app.models.base import (
    EnvelopeSpec, MissionParameters, LayoutSpec, ModulePlacement, 
    PerformanceMetrics, LayoutMetadata, ModuleType, EnvelopeType
)
from app.models.module_library import get_module_library, ModuleDefinition
from app.services.collision_detector import CollisionDetector
from app.services.connectivity_validator import ConnectivityValidator
from app.services.scoring_engine import EnhancedScoringEngine

logger = logging.getLogger(__name__)


class LayoutGenerationError(Exception):
    """Exception raised when layout generation fails"""
    pass


class BasicLayoutGenerator:
    """
    Basic layout generator using random placement with constraint validation.
    
    This is a simple implementation that serves as a foundation for more
    sophisticated optimization algorithms.
    """
    
    def __init__(self):
        self.module_library = get_module_library()
        self.collision_detector = CollisionDetector()
        self.connectivity_validator = ConnectivityValidator()
        self.scoring_engine = EnhancedScoringEngine()
        
        # Generation parameters
        self.max_attempts = 1000
        self.min_clearance = 0.6  # meters
        self.placement_margin = 0.5  # meters from envelope boundary
    
    async def generate_layouts(
        self, 
        envelope: EnvelopeSpec, 
        mission_params: MissionParameters,
        count: int = 5
    ) -> List[LayoutSpec]:
        """
        Generate multiple candidate layouts for the given envelope and mission.
        
        Args:
            envelope: Habitat envelope specification
            mission_params: Mission parameters and constraints
            count: Number of layouts to generate (3-8)
            
        Returns:
            List of generated layout specifications
            
        Raises:
            LayoutGenerationError: If generation fails
        """
        if count < 1 or count > 8:
            raise LayoutGenerationError("Layout count must be between 1 and 8")
        
        logger.info(f"Generating {count} layouts for envelope {envelope.id}")
        
        # Select modules based on mission requirements
        required_modules = self._select_required_modules(mission_params)
        
        # Validate that modules can fit in envelope
        if not self._validate_envelope_capacity(envelope, required_modules):
            raise LayoutGenerationError("Selected modules cannot fit in the specified envelope")
        
        layouts = []
        generation_attempts = 0
        max_generation_attempts = count * 10  # Allow multiple attempts per layout
        
        while len(layouts) < count and generation_attempts < max_generation_attempts:
            generation_attempts += 1
            
            try:
                layout = await self._generate_single_layout(
                    envelope, mission_params, required_modules
                )
                if layout:
                    layouts.append(layout)
                    logger.info(f"Generated layout {len(layouts)}/{count}")
            except Exception as e:
                logger.warning(f"Layout generation attempt {generation_attempts} failed: {str(e)}")
                continue
        
        if len(layouts) == 0:
            raise LayoutGenerationError("Failed to generate any valid layouts")
        
        logger.info(f"Successfully generated {len(layouts)} layouts after {generation_attempts} attempts")
        return layouts
    
    def _select_required_modules(self, mission_params: MissionParameters) -> List[ModuleDefinition]:
        """Select required modules based on mission parameters"""
        required_modules = []
        crew_size = mission_params.crew_size
        
        # Essential modules for any habitat
        # Sleep quarters (one per crew member)
        sleep_modules = self.module_library.get_modules_by_type(ModuleType.SLEEP_QUARTER)
        if sleep_modules:
            for i in range(crew_size):
                required_modules.append(sleep_modules[0])  # Use standard sleep quarter
        
        # Galley (one for up to 6 crew, two for larger crews)
        galley_modules = self.module_library.get_modules_by_type(ModuleType.GALLEY)
        if galley_modules:
            galley_count = 1 if crew_size <= 6 else 2
            for i in range(galley_count):
                required_modules.append(galley_modules[0])
        
        # Airlock (at least one, two for larger habitats)
        airlock_modules = self.module_library.get_modules_by_type(ModuleType.AIRLOCK)
        if airlock_modules:
            airlock_count = 1 if crew_size <= 4 else 2
            for i in range(airlock_count):
                required_modules.append(airlock_modules[0])
        
        # Mechanical/ECLSS (one per 4 crew members)
        mechanical_modules = self.module_library.get_modules_by_type(ModuleType.MECHANICAL)
        if mechanical_modules:
            mechanical_count = max(1, (crew_size + 3) // 4)  # Ceiling division
            for i in range(mechanical_count):
                required_modules.append(mechanical_modules[0])
        
        # Medical (one for any crew size)
        medical_modules = self.module_library.get_modules_by_type(ModuleType.MEDICAL)
        if medical_modules:
            required_modules.append(medical_modules[0])
        
        # Laboratory (for missions longer than 30 days)
        if mission_params.duration_days > 30:
            lab_modules = self.module_library.get_modules_by_type(ModuleType.LABORATORY)
            if lab_modules:
                required_modules.append(lab_modules[0])
        
        # Exercise (for missions longer than 14 days)
        if mission_params.duration_days > 14:
            exercise_modules = self.module_library.get_modules_by_type(ModuleType.EXERCISE)
            if exercise_modules:
                required_modules.append(exercise_modules[0])
        
        # Storage (scale with crew size and duration)
        storage_modules = self.module_library.get_modules_by_type(ModuleType.STORAGE)
        if storage_modules:
            storage_count = max(1, crew_size // 2)  # One storage per 2 crew members
            for i in range(storage_count):
                required_modules.append(storage_modules[0])
        
        logger.info(f"Selected {len(required_modules)} required modules for crew of {crew_size}")
        return required_modules
    
    def _validate_envelope_capacity(
        self, 
        envelope: EnvelopeSpec, 
        modules: List[ModuleDefinition]
    ) -> bool:
        """Check if all modules can theoretically fit in the envelope"""
        total_module_volume = sum(module.spec.bbox_m.volume for module in modules)
        envelope_volume = envelope.volume
        
        # Use 70% of envelope volume as practical limit (accounting for clearances)
        usable_volume = envelope_volume * 0.7
        
        if total_module_volume > usable_volume:
            logger.warning(
                f"Modules require {total_module_volume:.1f}m³ but envelope only has "
                f"{usable_volume:.1f}m³ usable volume"
            )
            return False
        
        return True
    
    async def _generate_single_layout(
        self,
        envelope: EnvelopeSpec,
        mission_params: MissionParameters,
        required_modules: List[ModuleDefinition]
    ) -> Optional[LayoutSpec]:
        """Generate a single valid layout"""
        
        # Create unique module instances with IDs
        module_placements = []
        placement_bounds = self._calculate_placement_bounds(envelope)
        
        for i, module_def in enumerate(required_modules):
            # Generate unique module ID
            module_type_str = module_def.spec.type if isinstance(module_def.spec.type, str) else module_def.spec.type.value
            module_id = f"{module_type_str}_{i+1:03d}_{uuid.uuid4().hex[:8]}"
            
            # Attempt to place module
            placement = self._place_module_randomly(
                module_def, module_id, placement_bounds, module_placements
            )
            
            if placement is None:
                logger.warning(f"Failed to place module {module_id}")
                return None
            
            module_placements.append(placement)
        
        # Validate connectivity
        if not self.connectivity_validator.validate_layout_connectivity(module_placements):
            logger.warning("Layout failed connectivity validation")
            return None
        
        # Calculate performance metrics
        kpis = await self.scoring_engine.calculate_metrics(
            module_placements, envelope, mission_params
        )
        
        # Generate explainability text
        explainability = self._generate_explainability(module_placements, kpis, mission_params)
        
        # Create layout specification
        layout_id = f"layout_{uuid.uuid4().hex[:12]}"
        
        layout = LayoutSpec(
            layout_id=layout_id,
            envelope_id=envelope.id,
            modules=module_placements,
            kpis=kpis,
            explainability=explainability,
            metadata=LayoutMetadata(
                name=f"Generated Layout {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                generation_params={
                    "algorithm": "random_placement",
                    "crew_size": mission_params.crew_size,
                    "duration_days": mission_params.duration_days,
                    "module_count": len(module_placements)
                }
            )
        )
        
        return layout
    
    def _calculate_placement_bounds(self, envelope: EnvelopeSpec) -> Dict[str, float]:
        """Calculate valid placement bounds within the envelope"""
        margin = self.placement_margin
        
        if envelope.type == EnvelopeType.CYLINDER:
            radius = envelope.params['radius'] - margin
            length = envelope.params['length'] - 2 * margin
            return {
                'type': 'cylinder',
                'radius': radius,
                'length': length,
                'center_x': 0.0,
                'center_y': 0.0,
                'center_z': 0.0
            }
        
        elif envelope.type == EnvelopeType.BOX:
            return {
                'type': 'box',
                'min_x': -envelope.params['width']/2 + margin,
                'max_x': envelope.params['width']/2 - margin,
                'min_y': -envelope.params['height']/2 + margin,
                'max_y': envelope.params['height']/2 - margin,
                'min_z': -envelope.params['depth']/2 + margin,
                'max_z': envelope.params['depth']/2 - margin
            }
        
        elif envelope.type == EnvelopeType.TORUS:
            major_radius = envelope.params['major_radius'] - margin
            minor_radius = envelope.params['minor_radius'] - margin
            return {
                'type': 'torus',
                'major_radius': major_radius,
                'minor_radius': minor_radius,
                'center_x': 0.0,
                'center_y': 0.0,
                'center_z': 0.0
            }
        
        else:
            # Fallback to box bounds for freeform
            return {
                'type': 'box',
                'min_x': -5.0, 'max_x': 5.0,
                'min_y': -5.0, 'max_y': 5.0,
                'min_z': -5.0, 'max_z': 5.0
            }
    
    def _place_module_randomly(
        self,
        module_def: ModuleDefinition,
        module_id: str,
        bounds: Dict[str, float],
        existing_placements: List[ModulePlacement]
    ) -> Optional[ModulePlacement]:
        """Attempt to place a module randomly within bounds without collisions"""
        
        for attempt in range(self.max_attempts):
            # Generate random position within bounds
            position = self._generate_random_position(bounds, module_def.spec.bbox_m)
            
            # Generate random rotation (0, 90, 180, 270 degrees for simplicity)
            rotation = random.choice([0, 90, 180, 270])
            
            # Create placement candidate
            placement = ModulePlacement(
                module_id=module_id,
                type=module_def.spec.type,
                position=position,
                rotation_deg=rotation,
                connections=[]  # Will be populated by connectivity validator
            )
            
            # Check for collisions with existing modules
            if not self._check_collisions(placement, module_def, existing_placements):
                # Check if position is within envelope bounds
                if self._is_within_bounds(placement, module_def, bounds):
                    return placement
        
        return None
    
    def _generate_random_position(
        self, 
        bounds: Dict[str, float], 
        bbox: 'BoundingBox'
    ) -> List[float]:
        """Generate a random position within the given bounds, biased toward center for better connectivity"""
        
        if bounds['type'] == 'cylinder':
            # Random position within cylinder, biased toward center
            max_radius = bounds['radius'] - max(bbox.x, bbox.y) / 2
            length = bounds['length'] - bbox.z
            
            # Use a bias toward smaller radii for better connectivity
            # Generate two random numbers and take the minimum to bias toward center
            r1 = random.uniform(0, max_radius)
            r2 = random.uniform(0, max_radius)
            r = min(r1, r2)  # Bias toward smaller radii
            
            angle = random.uniform(0, 2 * math.pi)
            x = r * math.cos(angle)
            y = r * math.sin(angle)
            
            # Bias toward center of length as well
            z1 = random.uniform(-length/2, length/2)
            z2 = random.uniform(-length/2, length/2)
            z = (z1 + z2) / 2  # Average to bias toward center
            
            return [x, y, z]
        
        elif bounds['type'] == 'box':
            # Bias toward center of box
            center_x = (bounds['min_x'] + bounds['max_x']) / 2
            center_y = (bounds['min_y'] + bounds['max_y']) / 2
            center_z = (bounds['min_z'] + bounds['max_z']) / 2
            
            # Generate positions with bias toward center
            range_x = bounds['max_x'] - bounds['min_x'] - bbox.x
            range_y = bounds['max_y'] - bounds['min_y'] - bbox.y
            range_z = bounds['max_z'] - bounds['min_z'] - bbox.z
            
            # Use triangular distribution to bias toward center
            x = random.triangular(bounds['min_x'] + bbox.x/2, bounds['max_x'] - bbox.x/2, center_x)
            y = random.triangular(bounds['min_y'] + bbox.y/2, bounds['max_y'] - bbox.y/2, center_y)
            z = random.triangular(bounds['min_z'] + bbox.z/2, bounds['max_z'] - bbox.z/2, center_z)
            
            return [x, y, z]
        
        elif bounds['type'] == 'torus':
            # Simplified torus placement - place on the major radius circle
            major_radius = bounds['major_radius'] - max(bbox.x, bbox.y) / 2
            
            angle = random.uniform(0, 2 * math.pi)
            x = major_radius * math.cos(angle)
            y = major_radius * math.sin(angle)
            z = random.uniform(-bbox.z/2, bbox.z/2)
            
            return [x, y, z]
        
        else:
            # Default to origin
            return [0.0, 0.0, 0.0]
    
    def _check_collisions(
        self,
        placement: ModulePlacement,
        module_def: ModuleDefinition,
        existing_placements: List[ModulePlacement]
    ) -> bool:
        """Check if placement collides with existing modules"""
        return self.collision_detector.check_module_collisions(
            placement, module_def, existing_placements, self.min_clearance
        )
    
    def _is_within_bounds(
        self,
        placement: ModulePlacement,
        module_def: ModuleDefinition,
        bounds: Dict[str, float]
    ) -> bool:
        """Check if module placement is within envelope bounds"""
        bbox = module_def.spec.bbox_m
        pos = placement.position
        
        if bounds['type'] == 'cylinder':
            # Check if module fits within cylinder
            radius = bounds['radius']
            length = bounds['length']
            
            # Check radial constraint
            module_radius = math.sqrt(pos[0]**2 + pos[1]**2) + max(bbox.x, bbox.y) / 2
            if module_radius > radius:
                return False
            
            # Check length constraint
            if abs(pos[2]) + bbox.z / 2 > length / 2:
                return False
            
            return True
        
        elif bounds['type'] == 'box':
            # Check if module fits within box
            if (pos[0] - bbox.x/2 < bounds['min_x'] or 
                pos[0] + bbox.x/2 > bounds['max_x']):
                return False
            if (pos[1] - bbox.y/2 < bounds['min_y'] or 
                pos[1] + bbox.y/2 > bounds['max_y']):
                return False
            if (pos[2] - bbox.z/2 < bounds['min_z'] or 
                pos[2] + bbox.z/2 > bounds['max_z']):
                return False
            
            return True
        
        elif bounds['type'] == 'torus':
            # Simplified torus bounds check
            major_radius = bounds['major_radius']
            minor_radius = bounds['minor_radius']
            
            distance_from_center = math.sqrt(pos[0]**2 + pos[1]**2)
            if distance_from_center + max(bbox.x, bbox.y)/2 > major_radius + minor_radius:
                return False
            if distance_from_center - max(bbox.x, bbox.y)/2 < major_radius - minor_radius:
                return False
            
            return True
        
        return True
    
    def _generate_explainability(
        self,
        modules: List[ModulePlacement],
        kpis: PerformanceMetrics,
        mission_params: MissionParameters
    ) -> str:
        """Generate natural language explanation for layout decisions"""
        
        explanations = []
        
        # Analyze module placement patterns
        module_types = [m.type for m in modules]
        airlock_count = sum(1 for t in module_types if t == ModuleType.AIRLOCK)
        
        if airlock_count >= 2:
            explanations.append("Multiple airlocks provide redundant emergency egress paths")
        elif airlock_count == 1:
            explanations.append("Single airlock provides emergency egress capability")
        
        # Analyze performance metrics
        if kpis.egress_time < 180:  # Less than 3 minutes
            explanations.append("Layout optimized for rapid emergency evacuation")
        elif kpis.egress_time > 300:  # More than 5 minutes
            explanations.append("Layout prioritizes operational efficiency over egress speed")
        
        if kpis.mean_transit_time < 60:  # Less than 1 minute
            explanations.append("Compact layout minimizes crew transit times")
        elif kpis.mean_transit_time > 120:  # More than 2 minutes
            explanations.append("Distributed layout provides crew privacy and noise isolation")
        
        # Analyze mission-specific considerations
        if mission_params.duration_days > 180:
            explanations.append("Long-duration mission layout emphasizes crew comfort and psychological well-being")
        elif mission_params.duration_days < 30:
            explanations.append("Short-duration mission layout prioritizes operational efficiency")
        
        if mission_params.crew_size > 6:
            explanations.append("Large crew size requires distributed social spaces and privacy zones")
        
        # Safety considerations
        if kpis.safety_score and kpis.safety_score > 0.8:
            explanations.append("High safety score achieved through redundant systems and clear egress paths")
        
        # Combine explanations
        if explanations:
            return ". ".join(explanations) + "."
        else:
            return "Layout generated using random placement algorithm with collision avoidance and connectivity validation."