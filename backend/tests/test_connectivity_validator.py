"""
Comprehensive unit tests for the connectivity validation system.
"""

import pytest
import math
from typing import List

from app.services.connectivity_validator import (
    ConnectivityValidator,
    ConnectivityGraph,
    ConnectionSpec,
    ConnectionType,
    PathfindingResult,
    ConnectivityMetrics
)
from app.models.base import ModulePlacement, ModuleType


class TestConnectivityGraph:
    """Test cases for ConnectivityGraph class"""
    
    def test_basic_graph_creation(self):
        """Test basic graph creation and node addition"""
        graph = ConnectivityGraph(use_networkx=False)  # Test fallback implementation
        
        module = ModulePlacement(
            module_id="test_module",
            type=ModuleType.LABORATORY,
            position=[0, 0, 0],
            rotation_deg=0,
            connections=[]
        )
        
        graph.add_node(module)
        assert "test_module" in graph.nodes
        assert graph.nodes["test_module"] == module
    
    def test_connection_addition(self):
        """Test adding connections between modules"""
        graph = ConnectivityGraph(use_networkx=False)
        
        module_a = ModulePlacement(
            module_id="module_a",
            type=ModuleType.LABORATORY,
            position=[0, 0, 0],
            rotation_deg=0,
            connections=[]
        )
        
        module_b = ModulePlacement(
            module_id="module_b",
            type=ModuleType.GALLEY,
            position=[3, 0, 0],
            rotation_deg=0,
            connections=[]
        )
        
        graph.add_node(module_a)
        graph.add_node(module_b)
        
        connection = ConnectionSpec(
            source_module="module_a",
            target_module="module_b",
            connection_type=ConnectionType.PRESSURIZED,
            distance=3.0
        )
        
        graph.add_connection(connection)
        
        # Check that connection was added
        assert ("module_a", "module_b") in graph.connections
        assert ("module_b", "module_a") in graph.connections  # Bidirectional
    
    def test_connectivity_check(self):
        """Test graph connectivity checking"""
        graph = ConnectivityGraph(use_networkx=False)
        
        # Create connected graph
        modules = [
            ModulePlacement(
                module_id=f"module_{i}",
                type=ModuleType.LABORATORY,
                position=[i * 2, 0, 0],
                rotation_deg=0,
                connections=[]
            )
            for i in range(3)
        ]
        
        for module in modules:
            graph.add_node(module)
        
        # Connect modules in a chain
        for i in range(len(modules) - 1):
            connection = ConnectionSpec(
                source_module=f"module_{i}",
                target_module=f"module_{i+1}",
                connection_type=ConnectionType.PRESSURIZED,
                distance=2.0
            )
            graph.add_connection(connection)
        
        assert graph.is_connected()
    
    def test_disconnected_components(self):
        """Test detection of disconnected components"""
        graph = ConnectivityGraph(use_networkx=False)
        
        # Create two separate components
        modules = [
            ModulePlacement(
                module_id=f"module_{i}",
                type=ModuleType.LABORATORY,
                position=[i * 2, 0, 0],
                rotation_deg=0,
                connections=[]
            )
            for i in range(4)
        ]
        
        for module in modules:
            graph.add_node(module)
        
        # Connect first two modules
        connection1 = ConnectionSpec(
            source_module="module_0",
            target_module="module_1",
            connection_type=ConnectionType.PRESSURIZED,
            distance=2.0
        )
        graph.add_connection(connection1)
        
        # Connect last two modules (separate component)
        connection2 = ConnectionSpec(
            source_module="module_2",
            target_module="module_3",
            connection_type=ConnectionType.PRESSURIZED,
            distance=2.0
        )
        graph.add_connection(connection2)
        
        assert not graph.is_connected()
        
        components = graph.get_connected_components()
        assert len(components) == 2
        assert {"module_0", "module_1"} in components
        assert {"module_2", "module_3"} in components
    
    def test_shortest_path(self):
        """Test shortest path finding"""
        graph = ConnectivityGraph(use_networkx=False)
        
        # Create linear chain of modules
        modules = [
            ModulePlacement(
                module_id=f"module_{i}",
                type=ModuleType.LABORATORY,
                position=[i * 2, 0, 0],
                rotation_deg=0,
                connections=[]
            )
            for i in range(4)
        ]
        
        for module in modules:
            graph.add_node(module)
        
        # Connect modules in a chain
        for i in range(len(modules) - 1):
            connection = ConnectionSpec(
                source_module=f"module_{i}",
                target_module=f"module_{i+1}",
                connection_type=ConnectionType.PRESSURIZED,
                distance=2.0
            )
            graph.add_connection(connection)
        
        # Test shortest path
        path = graph.shortest_path("module_0", "module_3")
        expected_path = ["module_0", "module_1", "module_2", "module_3"]
        assert path == expected_path
        
        # Test path length
        path_length = graph.shortest_path_length("module_0", "module_3")
        assert abs(path_length - 6.0) < 0.01  # 3 connections * 2.0 distance each


class TestConnectivityValidator:
    """Test cases for ConnectivityValidator class"""
    
    @pytest.fixture
    def validator(self):
        """Create a connectivity validator instance"""
        return ConnectivityValidator(use_networkx=False)  # Test fallback implementation
    
    @pytest.fixture
    def sample_modules(self):
        """Create sample module placements"""
        return [
            ModulePlacement(
                module_id="lab_001",
                type=ModuleType.LABORATORY,
                position=[0, 0, 0],
                rotation_deg=0,
                connections=[]
            ),
            ModulePlacement(
                module_id="galley_001",
                type=ModuleType.GALLEY,
                position=[4, 0, 0],
                rotation_deg=0,
                connections=[]
            ),
            ModulePlacement(
                module_id="airlock_001",
                type=ModuleType.AIRLOCK,
                position=[8, 0, 0],
                rotation_deg=0,
                connections=[]
            ),
            ModulePlacement(
                module_id="sleep_001",
                type=ModuleType.SLEEP_QUARTER,
                position=[0, 4, 0],
                rotation_deg=0,
                connections=[]
            )
        ]
    
    def test_basic_connectivity_validation(self, validator, sample_modules):
        """Test basic connectivity validation"""
        # All modules are within connection distance, so should be connected
        is_connected = validator.validate_layout_connectivity(sample_modules)
        assert is_connected
    
    def test_disconnected_layout_validation(self, validator):
        """Test validation of disconnected layout"""
        # Create modules that are too far apart
        disconnected_modules = [
            ModulePlacement(
                module_id="module_1",
                type=ModuleType.LABORATORY,
                position=[0, 0, 0],
                rotation_deg=0,
                connections=[]
            ),
            ModulePlacement(
                module_id="module_2",
                type=ModuleType.GALLEY,
                position=[20, 0, 0],  # Too far away
                rotation_deg=0,
                connections=[]
            )
        ]
        
        is_connected = validator.validate_layout_connectivity(disconnected_modules)
        assert not is_connected
    
    def test_pressurized_connectivity_validation(self, validator, sample_modules):
        """Test pressurized connectivity validation"""
        is_valid, errors = validator.validate_pressurized_connectivity(sample_modules)
        
        # Should be valid since there's an airlock and all modules are connected
        assert is_valid
        assert len(errors) == 0
    
    def test_no_airlock_validation(self, validator):
        """Test validation when no airlock is present"""
        modules_no_airlock = [
            ModulePlacement(
                module_id="lab_001",
                type=ModuleType.LABORATORY,
                position=[0, 0, 0],
                rotation_deg=0,
                connections=[]
            ),
            ModulePlacement(
                module_id="galley_001",
                type=ModuleType.GALLEY,
                position=[4, 0, 0],
                rotation_deg=0,
                connections=[]
            )
        ]
        
        is_valid, errors = validator.validate_pressurized_connectivity(modules_no_airlock)
        
        assert not is_valid
        assert any("airlock" in error.lower() for error in errors)
    
    def test_airlock_placement_validation(self, validator, sample_modules):
        """Test airlock placement validation"""
        is_valid, errors = validator.validate_airlock_placement(sample_modules)
        
        # Should have warning about single airlock
        assert not is_valid  # Single airlock should trigger warning
        assert any("one airlock" in error.lower() for error in errors)
    
    def test_multiple_airlocks_validation(self, validator):
        """Test validation with multiple airlocks"""
        modules_multi_airlock = [
            ModulePlacement(
                module_id="lab_001",
                type=ModuleType.LABORATORY,
                position=[0, 0, 0],
                rotation_deg=0,
                connections=[]
            ),
            ModulePlacement(
                module_id="airlock_001",
                type=ModuleType.AIRLOCK,
                position=[4, 0, 0],
                rotation_deg=0,
                connections=[]
            ),
            ModulePlacement(
                module_id="airlock_002",
                type=ModuleType.AIRLOCK,
                position=[15, 0, 0],  # Well separated
                rotation_deg=0,
                connections=[]
            )
        ]
        
        is_valid, errors = validator.validate_airlock_placement(modules_multi_airlock)
        
        # Should be valid with properly spaced airlocks
        assert is_valid
        assert len(errors) == 0
    
    def test_transit_time_calculation(self, validator, sample_modules):
        """Test transit time calculations"""
        transit_times = validator.calculate_transit_times(sample_modules)
        
        # Should have transit times for all module pairs
        assert len(transit_times) > 0
        
        # Check specific transit time (lab to galley should be reasonable)
        lab_to_galley = transit_times.get(("lab_001", "galley_001"))
        assert lab_to_galley is not None
        assert lab_to_galley > 0
        assert lab_to_galley < 300  # Should be less than 5 minutes
    
    def test_emergency_egress_validation(self, validator, sample_modules):
        """Test emergency egress time validation"""
        is_valid, errors, egress_times = validator.validate_emergency_egress_times(sample_modules)
        
        # Should be valid since airlock is present and reachable
        assert is_valid
        assert len(errors) == 0
        assert len(egress_times) == len(sample_modules)
        
        # Airlock should have zero egress time
        assert egress_times["airlock_001"] == 0.0
        
        # Other modules should have reasonable egress times
        for module_id, egress_time in egress_times.items():
            if module_id != "airlock_001":
                assert egress_time > 0
                assert egress_time < 300  # Should be under 5 minutes
    
    def test_comprehensive_connectivity_analysis(self, validator, sample_modules):
        """Test comprehensive connectivity analysis"""
        metrics = validator.analyze_connectivity_comprehensive(sample_modules)
        
        assert isinstance(metrics, ConnectivityMetrics)
        assert metrics.is_connected
        assert metrics.component_count == 1
        assert metrics.largest_component_size == len(sample_modules)
        
        # Should have airlock accessibility data
        assert len(metrics.airlock_accessibility) == len(sample_modules)
        
        # All modules should be able to reach airlock
        for module_id, can_reach in metrics.airlock_accessibility.items():
            assert can_reach
    
    def test_pathfinding_algorithms(self, validator, sample_modules):
        """Test pathfinding algorithms"""
        results = validator.find_optimal_paths(
            sample_modules, "lab_001", "airlock_001", "shortest"
        )
        
        assert len(results) > 0
        
        result = results[0]
        assert isinstance(result, PathfindingResult)
        assert result.path[0] == "lab_001"
        assert result.path[-1] == "airlock_001"
        assert result.total_distance > 0
        assert result.transit_time > 0
    
    def test_connection_capacity_validation(self, validator, sample_modules):
        """Test connection capacity validation"""
        # Test with default traffic patterns
        is_valid, errors = validator.validate_connection_capacity(sample_modules)
        
        # Should be valid with default traffic
        assert is_valid
        assert len(errors) == 0
    
    def test_single_module_edge_case(self, validator):
        """Test edge case with single module"""
        single_module = [
            ModulePlacement(
                module_id="solo_module",
                type=ModuleType.LABORATORY,
                position=[0, 0, 0],
                rotation_deg=0,
                connections=[]
            )
        ]
        
        # Single module should be trivially connected
        is_connected = validator.validate_layout_connectivity(single_module)
        assert is_connected
        
        # But should fail pressurized connectivity (no airlock)
        is_valid, errors = validator.validate_pressurized_connectivity(single_module)
        assert not is_valid
    
    def test_empty_layout_edge_case(self, validator):
        """Test edge case with empty layout"""
        empty_modules = []
        
        # Empty layout should be trivially connected
        is_connected = validator.validate_layout_connectivity(empty_modules)
        assert is_connected
        
        # Comprehensive analysis should handle empty case
        metrics = validator.analyze_connectivity_comprehensive(empty_modules)
        assert metrics.component_count == 0
        assert metrics.largest_component_size == 0
    
    def test_distance_calculation(self, validator):
        """Test distance calculation helper method"""
        pos1 = [0, 0, 0]
        pos2 = [3, 4, 0]
        
        distance = validator._calculate_distance(pos1, pos2)
        expected_distance = math.sqrt(3**2 + 4**2)
        
        assert abs(distance - expected_distance) < 0.01
    
    def test_connection_type_determination(self, validator):
        """Test connection type determination"""
        airlock_module = ModulePlacement(
            module_id="airlock_001",
            type=ModuleType.AIRLOCK,
            position=[0, 0, 0],
            rotation_deg=0,
            connections=[]
        )
        
        lab_module = ModulePlacement(
            module_id="lab_001",
            type=ModuleType.LABORATORY,
            position=[4, 0, 0],
            rotation_deg=0,
            connections=[]
        )
        
        # Connection involving airlock should be external
        conn_type = validator._determine_connection_type(airlock_module, lab_module)
        assert conn_type == ConnectionType.EXTERNAL
        
        # Connection between regular modules should be pressurized
        galley_module = ModulePlacement(
            module_id="galley_001",
            type=ModuleType.GALLEY,
            position=[8, 0, 0],
            rotation_deg=0,
            connections=[]
        )
        
        conn_type = validator._determine_connection_type(lab_module, galley_module)
        assert conn_type == ConnectionType.PRESSURIZED


class TestConnectionSpec:
    """Test cases for ConnectionSpec dataclass"""
    
    def test_connection_spec_creation(self):
        """Test connection specification creation"""
        connection = ConnectionSpec(
            source_module="module_a",
            target_module="module_b",
            connection_type=ConnectionType.PRESSURIZED,
            distance=5.0,
            port_source="port_1",
            port_target="port_2",
            capacity_rating=1.5
        )
        
        assert connection.source_module == "module_a"
        assert connection.target_module == "module_b"
        assert connection.connection_type == ConnectionType.PRESSURIZED
        assert connection.distance == 5.0
        assert connection.port_source == "port_1"
        assert connection.port_target == "port_2"
        assert connection.capacity_rating == 1.5
        assert connection.is_bidirectional  # Default should be True


class TestPathfindingResult:
    """Test cases for PathfindingResult dataclass"""
    
    def test_pathfinding_result_creation(self):
        """Test pathfinding result creation"""
        result = PathfindingResult(
            path=["module_a", "module_b", "module_c"],
            total_distance=10.0,
            transit_time=120.0,
            connection_types=[ConnectionType.PRESSURIZED, ConnectionType.PRESSURIZED],
            bottlenecks=["module_b"]
        )
        
        assert result.path == ["module_a", "module_b", "module_c"]
        assert result.total_distance == 10.0
        assert result.transit_time == 120.0
        assert len(result.connection_types) == 2
        assert result.bottlenecks == ["module_b"]
    
    def test_pathfinding_result_defaults(self):
        """Test pathfinding result with default values"""
        result = PathfindingResult(
            path=["module_a", "module_b"],
            total_distance=5.0,
            transit_time=60.0,
            connection_types=[ConnectionType.PRESSURIZED]
        )
        
        assert result.bottlenecks == []  # Should default to empty list


if __name__ == "__main__":
    pytest.main([__file__])