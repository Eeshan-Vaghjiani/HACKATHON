"""
Advanced Collision Detection System for HabitatCanvas

This module implements AABB collision detection with spatial indexing using trimesh,
clearance validation for walkways and emergency egress paths.
"""

import math
import numpy as np
from typing import List, Tuple, Dict, Optional, Set, Union
import logging
from dataclasses import dataclass
from enum import Enum

try:
    import trimesh
    from scipy.spatial import cKDTree
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    logging.warning("trimesh not available, falling back to basic collision detection")

from app.models.base import ModulePlacement
from app.models.module_library import ModuleDefinition, get_module_library

logger = logging.getLogger(__name__)


class CollisionType(Enum):
    """Types of collision detection"""
    AABB = "aabb"  # Axis-Aligned Bounding Box
    OBB = "obb"    # Oriented Bounding Box
    MESH = "mesh"  # Mesh-based collision


@dataclass
class ClearanceRequirement:
    """Clearance requirements for different path types"""
    walkway_width: float = 0.8  # meters
    emergency_egress_width: float = 1.2  # meters
    maintenance_access: float = 0.6  # meters
    safety_margin: float = 0.1  # meters


@dataclass
class CollisionResult:
    """Result of collision detection"""
    has_collision: bool
    collision_type: str
    penetration_depth: float = 0.0
    contact_points: List[List[float]] = None
    resolution_vector: List[float] = None
    
    def __post_init__(self):
        if self.contact_points is None:
            self.contact_points = []
        if self.resolution_vector is None:
            self.resolution_vector = [0.0, 0.0, 0.0]


class SpatialIndex:
    """Spatial indexing for efficient collision queries"""
    
    def __init__(self):
        self.bounding_boxes: Dict[str, BoundingBox3D] = {}
        self.kdtree: Optional[cKDTree] = None
        self.module_positions: Dict[str, np.ndarray] = {}
        self._dirty = True
    
    def add_module(self, module_id: str, bbox: 'BoundingBox3D'):
        """Add a module to the spatial index"""
        self.bounding_boxes[module_id] = bbox
        self.module_positions[module_id] = np.array(bbox.center)
        self._dirty = True
    
    def remove_module(self, module_id: str):
        """Remove a module from the spatial index"""
        if module_id in self.bounding_boxes:
            del self.bounding_boxes[module_id]
            del self.module_positions[module_id]
            self._dirty = True
    
    def update_module(self, module_id: str, bbox: 'BoundingBox3D'):
        """Update a module's position in the spatial index"""
        self.add_module(module_id, bbox)
    
    def _rebuild_kdtree(self):
        """Rebuild the KD-tree for spatial queries"""
        if not self.module_positions or not self._dirty:
            return
        
        positions = list(self.module_positions.values())
        if positions:
            self.kdtree = cKDTree(positions)
        self._dirty = False
    
    def query_nearby(self, position: List[float], radius: float) -> List[str]:
        """Query modules within a radius of a position"""
        if self._dirty:
            self._rebuild_kdtree()
        
        if self.kdtree is None:
            return []
        
        indices = self.kdtree.query_ball_point(position, radius)
        module_ids = list(self.module_positions.keys())
        return [module_ids[i] for i in indices if i < len(module_ids)]
    
    def query_range(self, min_bounds: List[float], max_bounds: List[float]) -> List[str]:
        """Query modules within a bounding box range"""
        nearby_modules = []
        
        for module_id, bbox in self.bounding_boxes.items():
            if self._bbox_intersects_range(bbox, min_bounds, max_bounds):
                nearby_modules.append(module_id)
        
        return nearby_modules
    
    def _bbox_intersects_range(self, bbox: 'BoundingBox3D', min_bounds: List[float], max_bounds: List[float]) -> bool:
        """Check if a bounding box intersects with a range"""
        return not (bbox.max_x < min_bounds[0] or bbox.min_x > max_bounds[0] or
                   bbox.max_y < min_bounds[1] or bbox.min_y > max_bounds[1] or
                   bbox.max_z < min_bounds[2] or bbox.min_z > max_bounds[2])


logger = logging.getLogger(__name__)


class BoundingBox3D:
    """Enhanced 3D Axis-Aligned Bounding Box with rotation support"""
    
    def __init__(self, center: List[float], dimensions: List[float], rotation_deg: float = 0.0):
        self.center = np.array(center)  # [x, y, z]
        self.dimensions = np.array(dimensions)  # [width, height, depth]
        self.rotation_deg = rotation_deg
        
        # Calculate rotation matrix for Z-axis rotation (most common for habitat modules)
        self.rotation_matrix = self._create_rotation_matrix(rotation_deg)
        
        # Calculate oriented bounding box corners
        self.corners = self._calculate_corners()
        
        # Calculate AABB bounds from oriented corners
        self._update_aabb_bounds()
    
    def _create_rotation_matrix(self, rotation_deg: float) -> np.ndarray:
        """Create rotation matrix for Z-axis rotation"""
        theta = np.radians(rotation_deg)
        cos_theta = np.cos(theta)
        sin_theta = np.sin(theta)
        
        return np.array([
            [cos_theta, -sin_theta, 0],
            [sin_theta, cos_theta, 0],
            [0, 0, 1]
        ])
    
    def _calculate_corners(self) -> np.ndarray:
        """Calculate the 8 corners of the oriented bounding box"""
        half_dims = self.dimensions / 2
        
        # Define corners in local space
        local_corners = np.array([
            [-half_dims[0], -half_dims[1], -half_dims[2]],
            [half_dims[0], -half_dims[1], -half_dims[2]],
            [half_dims[0], half_dims[1], -half_dims[2]],
            [-half_dims[0], half_dims[1], -half_dims[2]],
            [-half_dims[0], -half_dims[1], half_dims[2]],
            [half_dims[0], -half_dims[1], half_dims[2]],
            [half_dims[0], half_dims[1], half_dims[2]],
            [-half_dims[0], half_dims[1], half_dims[2]]
        ])
        
        # Transform to world space
        world_corners = np.array([
            self.rotation_matrix @ corner + self.center
            for corner in local_corners
        ])
        
        return world_corners
    
    def _update_aabb_bounds(self):
        """Update AABB bounds from oriented corners"""
        min_coords = np.min(self.corners, axis=0)
        max_coords = np.max(self.corners, axis=0)
        
        self.min_x, self.min_y, self.min_z = min_coords
        self.max_x, self.max_y, self.max_z = max_coords
    
    def intersects(self, other: 'BoundingBox3D', clearance: float = 0.0) -> bool:
        """Check if this bounding box intersects with another (with optional clearance)"""
        if self.rotation_deg == 0 and other.rotation_deg == 0:
            # Use fast AABB test for axis-aligned boxes
            return self._aabb_intersects(other, clearance)
        else:
            # Use SAT (Separating Axis Theorem) for oriented boxes
            return self._obb_intersects(other, clearance)
    
    def _aabb_intersects(self, other: 'BoundingBox3D', clearance: float = 0.0) -> bool:
        """Fast AABB intersection test"""
        margin = clearance / 2
        
        return not (self.max_x + margin < other.min_x - margin or 
                   self.min_x - margin > other.max_x + margin or
                   self.max_y + margin < other.min_y - margin or 
                   self.min_y - margin > other.max_y + margin or
                   self.max_z + margin < other.min_z - margin or 
                   self.min_z - margin > other.max_z + margin)
    
    def _obb_intersects(self, other: 'BoundingBox3D', clearance: float = 0.0) -> bool:
        """Oriented Bounding Box intersection using Separating Axis Theorem"""
        # For simplicity, expand both boxes by clearance and use AABB test
        # In production, implement full SAT algorithm
        expanded_self = BoundingBox3D(
            self.center.tolist(),
            (self.dimensions + clearance).tolist(),
            self.rotation_deg
        )
        expanded_other = BoundingBox3D(
            other.center.tolist(),
            (other.dimensions + clearance).tolist(),
            other.rotation_deg
        )
        
        return expanded_self._aabb_intersects(expanded_other, 0.0)
    
    def distance_to(self, other: 'BoundingBox3D') -> float:
        """Calculate minimum distance between two bounding boxes"""
        if self.intersects(other):
            return 0.0
        
        # Calculate distance between closest points on each box
        closest_point_self = self._closest_point_to_box(other.center)
        closest_point_other = other._closest_point_to_box(self.center)
        
        return np.linalg.norm(closest_point_self - closest_point_other)
    
    def _closest_point_to_box(self, point: np.ndarray) -> np.ndarray:
        """Find the closest point on this box to a given point"""
        # Transform point to local space
        local_point = self.rotation_matrix.T @ (point - self.center)
        
        # Clamp to box bounds in local space
        half_dims = self.dimensions / 2
        clamped_local = np.clip(local_point, -half_dims, half_dims)
        
        # Transform back to world space
        return self.rotation_matrix @ clamped_local + self.center
    
    def volume(self) -> float:
        """Calculate bounding box volume"""
        return np.prod(self.dimensions)
    
    def surface_area(self) -> float:
        """Calculate bounding box surface area"""
        w, h, d = self.dimensions
        return 2 * (w * h + w * d + h * d)
    
    def contains_point(self, point: List[float]) -> bool:
        """Check if a point is inside this bounding box"""
        point_array = np.array(point)
        
        # Transform point to local space
        local_point = self.rotation_matrix.T @ (point_array - self.center)
        
        # Check if within local bounds
        half_dims = self.dimensions / 2
        return np.all(np.abs(local_point) <= half_dims)
    
    def expand(self, margin: float) -> 'BoundingBox3D':
        """Create an expanded version of this bounding box"""
        expanded_dims = self.dimensions + 2 * margin
        return BoundingBox3D(
            self.center.tolist(),
            expanded_dims.tolist(),
            self.rotation_deg
        )
    
    def get_mesh(self) -> Optional['trimesh.Trimesh']:
        """Get a trimesh representation of this bounding box"""
        if not TRIMESH_AVAILABLE:
            return None
        
        # Create box mesh in local space
        box_mesh = trimesh.creation.box(extents=self.dimensions)
        
        # Apply rotation and translation
        transform_matrix = np.eye(4)
        transform_matrix[:3, :3] = self.rotation_matrix
        transform_matrix[:3, 3] = self.center
        
        box_mesh.apply_transform(transform_matrix)
        return box_mesh


class CollisionDetector:
    """
    Advanced collision detection system with AABB/OBB support, spatial indexing,
    and clearance validation for walkways and emergency egress paths.
    """
    
    def __init__(self, use_spatial_index: bool = True):
        self.module_library = get_module_library()
        self.spatial_index = SpatialIndex() if use_spatial_index else None
        self.clearance_requirements = ClearanceRequirement()
        self.collision_cache: Dict[Tuple[str, str], CollisionResult] = {}
        self._cache_dirty = False
    
    def check_module_collisions(
        self,
        placement: ModulePlacement,
        module_def: ModuleDefinition,
        existing_placements: List[ModulePlacement],
        min_clearance: float = 0.6,
        collision_type: CollisionType = CollisionType.AABB
    ) -> CollisionResult:
        """
        Check if a module placement collides with existing modules.
        
        Args:
            placement: Module placement to check
            module_def: Module definition with dimensions
            existing_placements: List of existing module placements
            min_clearance: Minimum clearance distance in meters
            collision_type: Type of collision detection to use
            
        Returns:
            CollisionResult with detailed collision information
        """
        if not existing_placements:
            return CollisionResult(has_collision=False, collision_type=collision_type.value)
        
        # Create bounding box for the new placement
        new_bbox = self._create_bounding_box(placement, module_def)
        
        # Use spatial index for efficient queries if available
        if self.spatial_index:
            # Query nearby modules within a reasonable radius
            search_radius = max(new_bbox.dimensions) + min_clearance + 2.0
            nearby_module_ids = self.spatial_index.query_nearby(
                placement.position, search_radius
            )
            
            # Filter existing placements to only nearby ones
            nearby_placements = [
                p for p in existing_placements 
                if p.module_id in nearby_module_ids
            ]
        else:
            nearby_placements = existing_placements
        
        # Check against nearby placements
        for existing_placement in nearby_placements:
            existing_module_def = self._get_module_definition(existing_placement.module_id)
            if existing_module_def is None:
                logger.warning(f"Could not find module definition for {existing_placement.module_id}")
                continue
            
            existing_bbox = self._create_bounding_box(existing_placement, existing_module_def)
            
            # Check collision based on type
            collision_result = self._detect_collision(
                new_bbox, existing_bbox, min_clearance, collision_type
            )
            
            if collision_result.has_collision:
                logger.debug(
                    f"Collision detected between {placement.module_id} and {existing_placement.module_id}"
                )
                return collision_result
        
        return CollisionResult(has_collision=False, collision_type=collision_type.value)
    
    def _detect_collision(
        self,
        bbox_a: BoundingBox3D,
        bbox_b: BoundingBox3D,
        min_clearance: float,
        collision_type: CollisionType
    ) -> CollisionResult:
        """Detect collision between two bounding boxes"""
        
        if collision_type == CollisionType.AABB:
            has_collision = bbox_a.intersects(bbox_b, min_clearance)
            
            if has_collision:
                # Calculate penetration depth
                distance = bbox_a.distance_to(bbox_b)
                penetration = max(0, min_clearance - distance)
                
                # Calculate resolution vector (simplified)
                center_diff = bbox_b.center - bbox_a.center
                if np.linalg.norm(center_diff) > 0:
                    resolution_direction = center_diff / np.linalg.norm(center_diff)
                    resolution_vector = (resolution_direction * penetration).tolist()
                else:
                    resolution_vector = [penetration, 0, 0]
                
                return CollisionResult(
                    has_collision=True,
                    collision_type=collision_type.value,
                    penetration_depth=penetration,
                    resolution_vector=resolution_vector
                )
        
        elif collision_type == CollisionType.MESH and TRIMESH_AVAILABLE:
            # Use trimesh for precise mesh-based collision detection
            mesh_a = bbox_a.get_mesh()
            mesh_b = bbox_b.get_mesh()
            
            if mesh_a and mesh_b:
                # Check if meshes intersect
                collision_manager = trimesh.collision.CollisionManager()
                collision_manager.add_object('a', mesh_a)
                
                has_collision = collision_manager.in_collision_single(mesh_b)
                
                if has_collision:
                    # Calculate contact points and penetration
                    distance = mesh_a.distance(mesh_b.vertices).min()
                    penetration = max(0, min_clearance - distance)
                    
                    return CollisionResult(
                        has_collision=True,
                        collision_type=collision_type.value,
                        penetration_depth=penetration
                    )
        
        return CollisionResult(has_collision=False, collision_type=collision_type.value)
    
    def validate_walkway_clearances(
        self,
        placements: List[ModulePlacement],
        walkway_paths: List[List[List[float]]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate clearances for walkways and emergency egress paths.
        
        Args:
            placements: List of module placements
            walkway_paths: List of walkway paths as sequences of 3D points
            
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []
        
        if not walkway_paths:
            # Generate default walkway paths between modules
            walkway_paths = self._generate_default_walkways(placements)
        
        for i, path in enumerate(walkway_paths):
            path_errors = self._validate_single_walkway(path, placements)
            if path_errors:
                errors.extend([f"Walkway {i+1}: {error}" for error in path_errors])
        
        return len(errors) == 0, errors
    
    def _generate_default_walkways(self, placements: List[ModulePlacement]) -> List[List[List[float]]]:
        """Generate default walkway paths between adjacent modules"""
        walkways = []
        
        # Simple approach: create straight-line paths between module centers
        for i, placement_a in enumerate(placements):
            for placement_b in placements[i+1:]:
                # Create straight path between module centers
                start = placement_a.position
                end = placement_b.position
                
                # Add intermediate points for longer paths
                distance = np.linalg.norm(np.array(end) - np.array(start))
                if distance > 3.0:  # Add waypoints for paths longer than 3m
                    num_points = int(distance / 1.5) + 1
                    path = []
                    for j in range(num_points + 1):
                        t = j / num_points
                        point = [
                            start[0] + t * (end[0] - start[0]),
                            start[1] + t * (end[1] - start[1]),
                            start[2] + t * (end[2] - start[2])
                        ]
                        path.append(point)
                    walkways.append(path)
                else:
                    walkways.append([start, end])
        
        return walkways
    
    def _validate_single_walkway(
        self, 
        path: List[List[float]], 
        placements: List[ModulePlacement]
    ) -> List[str]:
        """Validate clearances along a single walkway path"""
        errors = []
        
        if len(path) < 2:
            return ["Walkway path must have at least 2 points"]
        
        # Check clearances along the path
        for i in range(len(path) - 1):
            start_point = np.array(path[i])
            end_point = np.array(path[i + 1])
            
            # Sample points along the segment
            segment_length = np.linalg.norm(end_point - start_point)
            num_samples = max(3, int(segment_length / 0.5))  # Sample every 0.5m
            
            for j in range(num_samples + 1):
                t = j / num_samples
                sample_point = start_point + t * (end_point - start_point)
                
                # Check clearance to all modules at this point
                min_clearance = self._calculate_point_clearance(sample_point, placements)
                
                if min_clearance < self.clearance_requirements.walkway_width:
                    errors.append(
                        f"Insufficient walkway clearance at point {sample_point.tolist()}: "
                        f"{min_clearance:.2f}m < {self.clearance_requirements.walkway_width:.2f}m required"
                    )
        
        return errors
    
    def _calculate_point_clearance(
        self, 
        point: np.ndarray, 
        placements: List[ModulePlacement]
    ) -> float:
        """Calculate minimum clearance from a point to all modules"""
        min_clearance = float('inf')
        
        for placement in placements:
            module_def = self._get_module_definition(placement.module_id)
            if module_def is None:
                continue
            
            bbox = self._create_bounding_box(placement, module_def)
            
            # Calculate distance from point to bounding box
            closest_point = bbox._closest_point_to_box(point)
            distance = np.linalg.norm(point - closest_point)
            
            min_clearance = min(min_clearance, distance)
        
        return min_clearance if min_clearance != float('inf') else 0.0
    
    def validate_emergency_egress(
        self,
        placements: List[ModulePlacement],
        airlock_positions: List[List[float]]
    ) -> Tuple[bool, List[str]]:
        """
        Validate emergency egress paths to airlocks.
        
        Args:
            placements: List of module placements
            airlock_positions: List of airlock positions
            
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []
        
        if not airlock_positions:
            errors.append("No airlocks found for emergency egress validation")
            return False, errors
        
        # Check that each module has a clear path to at least one airlock
        for placement in placements:
            if placement.type.value == "airlock":
                continue  # Skip airlocks themselves
            
            has_clear_path = False
            
            for airlock_pos in airlock_positions:
                # Check if there's a clear path to this airlock
                path_clear = self._check_emergency_path_clearance(
                    placement.position, airlock_pos, placements
                )
                
                if path_clear:
                    has_clear_path = True
                    break
            
            if not has_clear_path:
                errors.append(
                    f"Module {placement.module_id} has no clear emergency egress path to any airlock"
                )
        
        return len(errors) == 0, errors
    
    def _check_emergency_path_clearance(
        self,
        start_pos: List[float],
        end_pos: List[float],
        placements: List[ModulePlacement]
    ) -> bool:
        """Check if emergency egress path has sufficient clearance"""
        start = np.array(start_pos)
        end = np.array(end_pos)
        
        # Sample points along the path
        distance = np.linalg.norm(end - start)
        num_samples = max(5, int(distance / 0.3))  # Sample every 0.3m for emergency paths
        
        for i in range(num_samples + 1):
            t = i / num_samples
            sample_point = start + t * (end - start)
            
            clearance = self._calculate_point_clearance(sample_point, placements)
            
            if clearance < self.clearance_requirements.emergency_egress_width:
                return False
        
        return True
    
    def calculate_clearance_distances(
        self,
        placements: List[ModulePlacement]
    ) -> Dict[Tuple[str, str], float]:
        """
        Calculate clearance distances between all module pairs.
        
        Returns:
            Dictionary mapping module ID pairs to clearance distances
        """
        distances = {}
        
        # Update spatial index if available
        if self.spatial_index:
            self.spatial_index = SpatialIndex()  # Reset index
            for placement in placements:
                module_def = self._get_module_definition(placement.module_id)
                if module_def:
                    bbox = self._create_bounding_box(placement, module_def)
                    self.spatial_index.add_module(placement.module_id, bbox)
        
        for i, placement_a in enumerate(placements):
            module_def_a = self._get_module_definition(placement_a.module_id)
            if module_def_a is None:
                continue
            
            bbox_a = self._create_bounding_box(placement_a, module_def_a)
            
            for j, placement_b in enumerate(placements[i+1:], i+1):
                module_def_b = self._get_module_definition(placement_b.module_id)
                if module_def_b is None:
                    continue
                
                bbox_b = self._create_bounding_box(placement_b, module_def_b)
                distance = bbox_a.distance_to(bbox_b)
                
                # Store distance for both directions
                key_ab = (placement_a.module_id, placement_b.module_id)
                key_ba = (placement_b.module_id, placement_a.module_id)
                distances[key_ab] = distance
                distances[key_ba] = distance
        
        return distances
    
    def find_collision_violations(
        self,
        placements: List[ModulePlacement],
        min_clearance: float = 0.6
    ) -> List[Dict[str, any]]:
        """
        Find all collision violations in a layout.
        
        Returns:
            List of violation dictionaries with module IDs and clearance info
        """
        violations = []
        clearances = self.calculate_clearance_distances(placements)
        
        processed_pairs = set()
        
        for (module_a, module_b), distance in clearances.items():
            # Avoid duplicate pairs
            pair_key = tuple(sorted([module_a, module_b]))
            if pair_key in processed_pairs:
                continue
            processed_pairs.add(pair_key)
            
            if distance < min_clearance:
                violations.append({
                    'module_a': module_a,
                    'module_b': module_b,
                    'actual_clearance': distance,
                    'required_clearance': min_clearance,
                    'violation_amount': min_clearance - distance
                })
        
        return violations
    
    def validate_layout_clearances(
        self,
        placements: List[ModulePlacement],
        min_clearance: float = 0.6
    ) -> Tuple[bool, List[str]]:
        """
        Validate that all modules in a layout meet clearance requirements.
        
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        violations = self.find_collision_violations(placements, min_clearance)
        
        if not violations:
            return True, []
        
        error_messages = []
        for violation in violations:
            message = (
                f"Clearance violation between {violation['module_a']} and {violation['module_b']}: "
                f"{violation['actual_clearance']:.2f}m < {violation['required_clearance']:.2f}m required"
            )
            error_messages.append(message)
        
        return False, error_messages
    
    def suggest_collision_resolution(
        self,
        placement: ModulePlacement,
        module_def: ModuleDefinition,
        existing_placements: List[ModulePlacement],
        bounds: Dict[str, float],
        min_clearance: float = 0.6
    ) -> List[ModulePlacement]:
        """
        Suggest alternative positions to resolve collisions.
        
        Returns:
            List of alternative placements that avoid collisions
        """
        suggestions = []
        
        # Try different positions around the original placement
        original_pos = placement.position
        search_radius = 2.0  # meters
        
        for dx in [-search_radius, 0, search_radius]:
            for dy in [-search_radius, 0, search_radius]:
                for dz in [-search_radius, 0, search_radius]:
                    if dx == 0 and dy == 0 and dz == 0:
                        continue  # Skip original position
                    
                    new_position = [
                        original_pos[0] + dx,
                        original_pos[1] + dy,
                        original_pos[2] + dz
                    ]
                    
                    # Create alternative placement
                    alt_placement = ModulePlacement(
                        module_id=placement.module_id,
                        type=placement.type,
                        position=new_position,
                        rotation_deg=placement.rotation_deg,
                        connections=placement.connections
                    )
                    
                    # Check if this position avoids collisions
                    if not self.check_module_collisions(
                        alt_placement, module_def, existing_placements, min_clearance
                    ):
                        suggestions.append(alt_placement)
                        
                        # Limit number of suggestions
                        if len(suggestions) >= 5:
                            return suggestions
        
        return suggestions
    
    def update_spatial_index(self, placements: List[ModulePlacement]):
        """Update the spatial index with current module placements"""
        if not self.spatial_index:
            return
        
        # Clear existing index
        self.spatial_index = SpatialIndex()
        
        # Add all current placements
        for placement in placements:
            module_def = self._get_module_definition(placement.module_id)
            if module_def:
                bbox = self._create_bounding_box(placement, module_def)
                self.spatial_index.add_module(placement.module_id, bbox)
    
    def get_collision_mesh(self, placement: ModulePlacement, module_def: ModuleDefinition) -> Optional['trimesh.Trimesh']:
        """Get collision mesh for a module placement"""
        if not TRIMESH_AVAILABLE:
            return None
        
        bbox = self._create_bounding_box(placement, module_def)
        return bbox.get_mesh()
    
    def batch_collision_check(
        self,
        new_placements: List[ModulePlacement],
        existing_placements: List[ModulePlacement],
        min_clearance: float = 0.6
    ) -> Dict[str, CollisionResult]:
        """
        Perform batch collision checking for multiple new placements.
        
        Returns:
            Dictionary mapping module IDs to collision results
        """
        results = {}
        
        # Update spatial index with existing placements
        self.update_spatial_index(existing_placements)
        
        for placement in new_placements:
            module_def = self._get_module_definition(placement.module_id)
            if module_def:
                result = self.check_module_collisions(
                    placement, module_def, existing_placements, min_clearance
                )
                results[placement.module_id] = result
        
        return results
    
    def _create_bounding_box(
        self, 
        placement: ModulePlacement, 
        module_def: ModuleDefinition
    ) -> BoundingBox3D:
        """Create a bounding box for a module placement"""
        bbox_spec = module_def.spec.bbox_m
        dimensions = [bbox_spec.x, bbox_spec.y, bbox_spec.z]
        
        return BoundingBox3D(
            center=placement.position,
            dimensions=dimensions,
            rotation_deg=placement.rotation_deg
        )
    
    def _get_module_definition(self, module_id: str) -> Optional[ModuleDefinition]:
        """Get module definition by ID, handling both library and instance IDs"""
        # First try direct lookup
        module_def = self.module_library.get_module(module_id)
        if module_def:
            return module_def
        
        # If not found, try to extract base type from instance ID
        # Instance IDs are formatted like "sleep_quarter_001_abc123def"
        if '_' in module_id:
            parts = module_id.split('_')
            if len(parts) >= 3:  # Need at least type_number_hash
                # Try to reconstruct standard module ID
                module_type = '_'.join(parts[:-2])  # e.g., "sleep_quarter" from "sleep_quarter_001_abc123def"
                std_module_id = f"std_{module_type}"
                module_def = self.module_library.get_module(std_module_id)
                if module_def:
                    return module_def
        
        return None
    
    def get_collision_statistics(
        self, 
        placements: List[ModulePlacement]
    ) -> Dict[str, any]:
        """
        Calculate collision and clearance statistics for a layout.
        
        Returns:
            Dictionary with collision statistics
        """
        if len(placements) < 2:
            return {
                'total_pairs': 0,
                'collision_violations': 0,
                'min_clearance': float('inf'),
                'avg_clearance': 0.0,
                'clearance_distribution': {}
            }
        
        clearances = self.calculate_clearance_distances(placements)
        violations = self.find_collision_violations(placements)
        
        # Calculate statistics
        clearance_values = list(clearances.values())
        unique_clearances = []
        
        # Remove duplicates (each pair appears twice in clearances dict)
        processed_pairs = set()
        for (module_a, module_b), distance in clearances.items():
            pair_key = tuple(sorted([module_a, module_b]))
            if pair_key not in processed_pairs:
                unique_clearances.append(distance)
                processed_pairs.add(pair_key)
        
        total_pairs = len(unique_clearances)
        min_clearance = min(unique_clearances) if unique_clearances else 0.0
        avg_clearance = sum(unique_clearances) / len(unique_clearances) if unique_clearances else 0.0
        
        # Clearance distribution
        distribution = {
            'under_0.5m': sum(1 for d in unique_clearances if d < 0.5),
            '0.5m_to_1.0m': sum(1 for d in unique_clearances if 0.5 <= d < 1.0),
            '1.0m_to_2.0m': sum(1 for d in unique_clearances if 1.0 <= d < 2.0),
            'over_2.0m': sum(1 for d in unique_clearances if d >= 2.0)
        }
        
        return {
            'total_pairs': total_pairs,
            'collision_violations': len(violations),
            'min_clearance': min_clearance,
            'avg_clearance': avg_clearance,
            'clearance_distribution': distribution,
            'violation_details': violations
        }