"""
Comprehensive unit tests for the collision detection system.
"""

import pytest
import numpy as np
from typing import List

from app.services.collision_detector import (
    CollisionDetector, 
    BoundingBox3D, 
    SpatialIndex,
    CollisionType,
    CollisionResult,
    ClearanceRequirement
)
from app.models.base import ModulePlacement, ModuleType
from app.models.module_library import ModuleDefinition
from app.models.base import ModuleSpec, BoundingBox


class TestBoundingBox3D:
    """Test cases for BoundingBox3D class"""
    
    def test_basic_creation(self):
        """Test basic bounding box creation"""
        bbox = BoundingBox3D([0, 0, 0], [2, 2, 2], 0)
        
        assert bbox.center.tolist() == [0, 0, 0]
        assert bbox.dimensions.tolist() == [2, 2, 2]
        assert bbox.rotation_deg == 0
        assert bbox.volume() == 8.0
    
    def test_aabb_intersection(self):
        """Test AABB intersection detection"""
        bbox1 = BoundingBox3D([0, 0, 0], [2, 2, 2], 0)
        bbox2 = BoundingBox3D([1, 0, 0], [2, 2, 2], 0)  # Overlapping
        bbox3 = BoundingBox3D([3, 0, 0], [2, 2, 2], 0)  # Non-overlapping
        
        assert bbox1.intersects(bbox2)
        assert not bbox1.intersects(bbox3)
    
    def test_clearance_intersection(self):
        """Test intersection with clearance requirements"""
        bbox1 = BoundingBox3D([0, 0, 0], [2, 2, 2], 0)
        bbox2 = BoundingBox3D([2.5, 0, 0], [2, 2, 2], 0)  # 0.5m apart
        
        # Should not intersect without clearance
        assert not bbox1.intersects(bbox2, 0.0)
        
        # Should intersect with 1m clearance requirement
        assert bbox1.intersects(bbox2, 1.0)
    
    def test_distance_calculation(self):
        """Test distance calculation between bounding boxes"""
        bbox1 = BoundingBox3D([0, 0, 0], [2, 2, 2], 0)
        bbox2 = BoundingBox3D([3, 0, 0], [2, 2, 2], 0)  # 1m apart (surface to surface)
        
        distance = bbox1.distance_to(bbox2)
        assert abs(distance - 1.0) < 0.01
    
    def test_rotated_bounding_box(self):
        """Test bounding box with rotation"""
        bbox = BoundingBox3D([0, 0, 0], [4, 2, 2], 45)  # 45-degree rotation
        
        # Check that AABB bounds are expanded due to rotation
        assert bbox.max_x > 2.0  # Should be larger than half the original width
        assert bbox.max_y > 1.0  # Should be larger than half the original height
    
    def test_point_containment(self):
        """Test point containment checking"""
        bbox = BoundingBox3D([0, 0, 0], [2, 2, 2], 0)
        
        assert bbox.contains_point([0, 0, 0])  # Center
        assert bbox.contains_point([0.9, 0.9, 0.9])  # Inside
        assert not bbox.contains_point([1.5, 1.5, 1.5])  # Outside
    
    def test_expansion(self):
        """Test bounding box expansion"""
        bbox = BoundingBox3D([0, 0, 0], [2, 2, 2], 0)
        expanded = bbox.expand(0.5)
        
        assert expanded.dimensions.tolist() == [3, 3, 3]
        assert expanded.center.tolist() == [0, 0, 0]


class TestSpatialIndex:
    """Test cases for SpatialIndex class"""
    
    def test_basic_operations(self):
        """Test basic spatial index operations"""
        index = SpatialIndex()
        bbox = BoundingBox3D([0, 0, 0], [2, 2, 2], 0)
        
        # Add module
        index.add_module("module1", bbox)
        assert "module1" in index.bounding_boxes
        
        # Remove module
        index.remove_module("module1")
        assert "module1" not in index.bounding_boxes
    
    def test_nearby_query(self):
        """Test nearby module queries"""
        index = SpatialIndex()
        
        # Add modules at different positions
        bbox1 = BoundingBox3D([0, 0, 0], [2, 2, 2], 0)
        bbox2 = BoundingBox3D([1, 0, 0], [2, 2, 2], 0)
        bbox3 = BoundingBox3D([10, 0, 0], [2, 2, 2], 0)
        
        index.add_module("module1", bbox1)
        index.add_module("module2", bbox2)
        index.add_module("module3", bbox3)
        
        # Query nearby modules
        nearby = index.query_nearby([0, 0, 0], 3.0)
        
        assert "module1" in nearby
        assert "module2" in nearby
        assert "module3" not in nearby
    
    def test_range_query(self):
        """Test range-based queries"""
        index = SpatialIndex()
        
        bbox1 = BoundingBox3D([0, 0, 0], [2, 2, 2], 0)
        bbox2 = BoundingBox3D([5, 5, 5], [2, 2, 2], 0)
        
        index.add_module("module1", bbox1)
        index.add_module("module2", bbox2)
        
        # Query range that includes only module1
        in_range = index.query_range([-2, -2, -2], [2, 2, 2])
        
        assert "module1" in in_range
        assert "module2" not in in_range


class TestCollisionDetector:
    """Test cases for CollisionDetector class"""
    
    @pytest.fixture
    def detector(self):
        """Create a collision detector instance"""
        return CollisionDetector(use_spatial_index=True)
    
    @pytest.fixture
    def sample_module_def(self):
        """Create a sample module definition"""
        return ModuleDefinition(
            module_id="test_module",
            spec=ModuleSpec(
                module_id="test_module",
                type=ModuleType.LABORATORY,
                name="Test Module",
                bbox_m=BoundingBox(x=2.0, y=2.0, z=2.0),
                mass_kg=1000.0,
                power_w=500.0,
                stowage_m3=6.0,  # Reduced to be less than bbox volume (8.0)
                connectivity_ports=["port1"],
                adjacency_preferences=[],
                adjacency_restrictions=[]
            )
        )
    
    @pytest.fixture
    def sample_placements(self):
        """Create sample module placements"""
        return [
            ModulePlacement(
                module_id="module1",
                type=ModuleType.LABORATORY,
                position=[0, 0, 0],
                rotation_deg=0,
                connections=[]
            ),
            ModulePlacement(
                module_id="module2",
                type=ModuleType.LABORATORY,
                position=[3, 0, 0],
                rotation_deg=0,
                connections=[]
            ),
            ModulePlacement(
                module_id="module3",
                type=ModuleType.AIRLOCK,
                position=[6, 0, 0],
                rotation_deg=0,
                connections=[]
            )
        ]
    
    def test_no_collision_detection(self, detector, sample_module_def, sample_placements):
        """Test collision detection with no collisions"""
        new_placement = ModulePlacement(
            module_id="new_module",
            type=ModuleType.LABORATORY,
            position=[10, 0, 0],  # Far away
            rotation_deg=0,
            connections=[]
        )
        
        # Mock the module definition lookup
        detector._get_module_definition = lambda x: sample_module_def
        
        result = detector.check_module_collisions(
            new_placement, sample_module_def, sample_placements
        )
        
        assert not result.has_collision
    
    def test_collision_detection(self, detector, sample_module_def, sample_placements):
        """Test collision detection with actual collision"""
        new_placement = ModulePlacement(
            module_id="new_module",
            type=ModuleType.LABORATORY,
            position=[0.5, 0, 0],  # Overlapping with module1
            rotation_deg=0,
            connections=[]
        )
        
        # Mock the module definition lookup
        detector._get_module_definition = lambda x: sample_module_def
        
        result = detector.check_module_collisions(
            new_placement, sample_module_def, sample_placements
        )
        
        assert result.has_collision
        assert result.penetration_depth > 0
    
    def test_clearance_validation(self, detector, sample_module_def, sample_placements):
        """Test clearance validation between modules"""
        # Mock the module definition lookup
        detector._get_module_definition = lambda x: sample_module_def
        
        distances = detector.calculate_clearance_distances(sample_placements)
        
        # Check that distances are calculated
        assert len(distances) > 0
        
        # Check specific distance (module1 to module2 should be ~1m surface-to-surface)
        key = ("module1", "module2")
        if key in distances:
            assert abs(distances[key] - 1.0) < 0.1
    
    def test_walkway_validation(self, detector, sample_module_def, sample_placements):
        """Test walkway clearance validation"""
        # Mock the module definition lookup
        detector._get_module_definition = lambda x: sample_module_def
        
        # Test with default generated walkways
        is_valid, errors = detector.validate_walkway_clearances(sample_placements)
        
        # Should have some validation result
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
    
    def test_emergency_egress_validation(self, detector, sample_module_def, sample_placements):
        """Test emergency egress path validation"""
        # Mock the module definition lookup
        detector._get_module_definition = lambda x: sample_module_def
        
        # Use module3 (airlock) as the egress point
        airlock_positions = [[6, 0, 0]]
        
        is_valid, errors = detector.validate_emergency_egress(
            sample_placements, airlock_positions
        )
        
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
    
    def test_batch_collision_check(self, detector, sample_module_def):
        """Test batch collision checking"""
        existing_placements = [
            ModulePlacement(
                module_id="existing1",
                type=ModuleType.LABORATORY,
                position=[0, 0, 0],
                rotation_deg=0,
                connections=[]
            )
        ]
        
        new_placements = [
            ModulePlacement(
                module_id="new1",
                type=ModuleType.LABORATORY,
                position=[5, 0, 0],  # No collision
                rotation_deg=0,
                connections=[]
            ),
            ModulePlacement(
                module_id="new2",
                type=ModuleType.LABORATORY,
                position=[0.5, 0, 0],  # Collision
                rotation_deg=0,
                connections=[]
            )
        ]
        
        # Mock the module definition lookup
        detector._get_module_definition = lambda x: sample_module_def
        
        results = detector.batch_collision_check(
            new_placements, existing_placements
        )
        
        assert "new1" in results
        assert "new2" in results
        assert not results["new1"].has_collision
        assert results["new2"].has_collision
    
    def test_collision_statistics(self, detector, sample_module_def, sample_placements):
        """Test collision statistics calculation"""
        # Mock the module definition lookup
        detector._get_module_definition = lambda x: sample_module_def
        
        stats = detector.get_collision_statistics(sample_placements)
        
        assert "total_pairs" in stats
        assert "collision_violations" in stats
        assert "min_clearance" in stats
        assert "avg_clearance" in stats
        assert "clearance_distribution" in stats
        
        # Should have some pairs for 3 modules
        assert stats["total_pairs"] > 0
    
    def test_spatial_index_integration(self, detector, sample_module_def, sample_placements):
        """Test spatial index integration"""
        # Mock the module definition lookup
        detector._get_module_definition = lambda x: sample_module_def
        
        # Update spatial index
        detector.update_spatial_index(sample_placements)
        
        # Check that spatial index was populated
        assert len(detector.spatial_index.bounding_boxes) == len(sample_placements)
    
    def test_collision_edge_cases(self, detector, sample_module_def):
        """Test edge cases in collision detection"""
        # Test with empty placements list
        new_placement = ModulePlacement(
            module_id="new_module",
            type=ModuleType.LABORATORY,
            position=[0, 0, 0],
            rotation_deg=0,
            connections=[]
        )
        
        result = detector.check_module_collisions(
            new_placement, sample_module_def, []
        )
        
        assert not result.has_collision
        
        # Test with identical positions (perfect overlap)
        existing_placements = [
            ModulePlacement(
                module_id="existing1",
                type=ModuleType.LABORATORY,
                position=[0, 0, 0],
                rotation_deg=0,
                connections=[]
            )
        ]
        
        detector._get_module_definition = lambda x: sample_module_def
        
        result = detector.check_module_collisions(
            new_placement, sample_module_def, existing_placements
        )
        
        assert result.has_collision
        assert result.penetration_depth > 0


class TestClearanceRequirements:
    """Test cases for clearance requirements"""
    
    def test_clearance_requirement_defaults(self):
        """Test default clearance requirements"""
        req = ClearanceRequirement()
        
        assert req.walkway_width == 0.8
        assert req.emergency_egress_width == 1.2
        assert req.maintenance_access == 0.6
        assert req.safety_margin == 0.1
    
    def test_custom_clearance_requirements(self):
        """Test custom clearance requirements"""
        req = ClearanceRequirement(
            walkway_width=1.0,
            emergency_egress_width=1.5,
            maintenance_access=0.8,
            safety_margin=0.2
        )
        
        assert req.walkway_width == 1.0
        assert req.emergency_egress_width == 1.5
        assert req.maintenance_access == 0.8
        assert req.safety_margin == 0.2


class TestCollisionResult:
    """Test cases for CollisionResult dataclass"""
    
    def test_collision_result_creation(self):
        """Test collision result creation"""
        result = CollisionResult(
            has_collision=True,
            collision_type="aabb",
            penetration_depth=0.5,
            contact_points=[[0, 0, 0]],
            resolution_vector=[1, 0, 0]
        )
        
        assert result.has_collision
        assert result.collision_type == "aabb"
        assert result.penetration_depth == 0.5
        assert result.contact_points == [[0, 0, 0]]
        assert result.resolution_vector == [1, 0, 0]
    
    def test_collision_result_defaults(self):
        """Test collision result with default values"""
        result = CollisionResult(
            has_collision=False,
            collision_type="aabb"
        )
        
        assert not result.has_collision
        assert result.penetration_depth == 0.0
        assert result.contact_points == []
        assert result.resolution_vector == [0.0, 0.0, 0.0]


if __name__ == "__main__":
    pytest.main([__file__])