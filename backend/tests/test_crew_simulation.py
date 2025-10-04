"""
Tests for crew workflow simulation engine
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from datetime import datetime

from app.services.crew_simulation import (
    CrewAgent, CrewWorkflowModel, AgentSimulator,
    ActivityType, CrewRole, Activity, SimulationResults
)
from app.models.base import LayoutSpec, ModulePlacement, MissionParameters, ModuleType, PerformanceMetrics


@pytest.fixture
def sample_mission_params():
    """Create sample mission parameters for testing"""
    return MissionParameters(
        crew_size=4,
        duration_days=180,
        priority_weights={
            "safety": 0.4,
            "efficiency": 0.3,
            "mass": 0.2,
            "power": 0.1
        },
        activity_schedule={
            "work": 8.0,
            "sleep": 8.0,
            "meal": 3.0,
            "exercise": 1.5,
            "recreation": 2.0,
            "maintenance": 1.5
        },
        emergency_scenarios=["fire", "depressurization"]
    )


@pytest.fixture
def sample_layout():
    """Create a sample habitat layout for testing"""
    modules = [
        ModulePlacement(
            module_id="sleep_1",
            type=ModuleType.SLEEP_QUARTER,
            position=[0, 0, 0],
            rotation_deg=0,
            connections=["corridor_1"]
        ),
        ModulePlacement(
            module_id="sleep_2",
            type=ModuleType.SLEEP_QUARTER,
            position=[2, 0, 0],
            rotation_deg=0,
            connections=["corridor_1"]
        ),
        ModulePlacement(
            module_id="galley_1",
            type=ModuleType.GALLEY,
            position=[4, 0, 0],
            rotation_deg=0,
            connections=["corridor_1"]
        ),
        ModulePlacement(
            module_id="lab_1",
            type=ModuleType.LABORATORY,
            position=[6, 0, 0],
            rotation_deg=0,
            connections=["corridor_1"]
        ),
        ModulePlacement(
            module_id="corridor_1",
            type=ModuleType.STORAGE,  # Using storage as corridor placeholder
            position=[3, 0, 0],
            rotation_deg=0,
            connections=["sleep_1", "sleep_2", "galley_1", "lab_1", "airlock_1"]
        ),
        ModulePlacement(
            module_id="airlock_1",
            type=ModuleType.AIRLOCK,
            position=[8, 0, 0],
            rotation_deg=0,
            connections=["corridor_1"]
        )
    ]
    
    # Create sample performance metrics
    kpis = PerformanceMetrics(
        mean_transit_time=45.0,
        egress_time=120.0,
        mass_total=15000.0,
        power_budget=2500.0,
        thermal_margin=0.15,
        lss_margin=0.20,
        stowage_utilization=0.85
    )
    
    return LayoutSpec(
        layout_id="test_layout_1",
        envelope_id="test_envelope_1",
        modules=modules,
        kpis=kpis,
        explainability="Test layout for crew simulation"
    )


class TestCrewAgent:
    """Test cases for CrewAgent class"""
    
    def test_agent_initialization(self, sample_layout, sample_mission_params):
        """Test crew agent initialization"""
        model = CrewWorkflowModel(sample_layout, sample_mission_params, 24.0)
        agent = CrewAgent("crew_1", model, CrewRole.COMMANDER)
        
        assert agent.unique_id == "crew_1"
        assert agent.role == CrewRole.COMMANDER
        assert agent.current_module is None
        assert agent.stress_level == 0.0
        assert agent.fatigue_level == 0.0
        assert len(agent.schedule) == 0
    
    def test_add_activity(self, sample_layout, sample_mission_params):
        """Test adding activities to crew schedule"""
        model = CrewWorkflowModel(sample_layout, sample_mission_params, 24.0)
        agent = CrewAgent("crew_1", model, CrewRole.COMMANDER)
        
        activity = Activity(
            activity_type=ActivityType.WORK,
            start_time=9.0,
            duration=4.0,
            location_module="lab_1"
        )
        
        agent.add_activity(activity)
        assert len(agent.schedule) == 1
        assert agent.schedule[0].activity_type == ActivityType.WORK
    
    def test_pathfinding(self, sample_layout, sample_mission_params):
        """Test pathfinding between modules"""
        model = CrewWorkflowModel(sample_layout, sample_mission_params, 24.0)
        agent = CrewAgent("crew_1", model, CrewRole.COMMANDER)
        agent.current_module = "sleep_1"
        
        path = agent.find_path_to_module("lab_1")
        
        # Should find path through corridor
        assert len(path) >= 1
        assert "corridor_1" in path or path == ["lab_1"]  # Direct or through corridor
    
    def test_get_current_activity(self, sample_layout, sample_mission_params):
        """Test getting current activity based on time"""
        model = CrewWorkflowModel(sample_layout, sample_mission_params, 24.0)
        agent = CrewAgent("crew_1", model, CrewRole.COMMANDER)
        
        # Add activities
        agent.add_activity(Activity(ActivityType.SLEEP, 0.0, 8.0, "sleep_1"))
        agent.add_activity(Activity(ActivityType.WORK, 9.0, 4.0, "lab_1"))
        
        # Test different times
        assert agent.get_current_activity(5.0).activity_type == ActivityType.SLEEP
        assert agent.get_current_activity(10.0).activity_type == ActivityType.WORK
        assert agent.get_current_activity(15.0) is None  # No activity scheduled


class TestCrewWorkflowModel:
    """Test cases for CrewWorkflowModel class"""
    
    def test_model_initialization(self, sample_layout, sample_mission_params):
        """Test model initialization"""
        model = CrewWorkflowModel(sample_layout, sample_mission_params, 24.0)
        
        assert len(model.crew_agents) == sample_mission_params.crew_size
        assert model.simulation_duration == 24.0
        assert model.current_time == 0.0
        assert len(model.connectivity_graph.nodes()) == len(sample_layout.modules)
    
    def test_connectivity_graph_creation(self, sample_layout, sample_mission_params):
        """Test connectivity graph creation from layout"""
        model = CrewWorkflowModel(sample_layout, sample_mission_params, 24.0)
        
        # Check that all modules are nodes
        for module in sample_layout.modules:
            assert module.module_id in model.connectivity_graph.nodes()
        
        # Check that connections exist
        assert model.connectivity_graph.has_edge("sleep_1", "corridor_1")
        assert model.connectivity_graph.has_edge("corridor_1", "lab_1")
    
    def test_module_capacity_calculation(self, sample_layout, sample_mission_params):
        """Test module capacity calculation"""
        model = CrewWorkflowModel(sample_layout, sample_mission_params, 24.0)
        
        # Sleep quarters should have capacity 1
        assert model.module_capacities["sleep_1"] == 1
        assert model.module_capacities["sleep_2"] == 1
        
        # Galley should accommodate crew size
        assert model.module_capacities["galley_1"] <= sample_mission_params.crew_size
    
    def test_crew_schedule_generation(self, sample_layout, sample_mission_params):
        """Test automatic crew schedule generation"""
        model = CrewWorkflowModel(sample_layout, sample_mission_params, 24.0)
        
        # All crew should have schedules
        for agent in model.crew_agents:
            assert len(agent.schedule) > 0
            
            # Should have basic activities
            activity_types = [activity.activity_type for activity in agent.schedule]
            assert ActivityType.SLEEP in activity_types
            assert ActivityType.WORK in activity_types
            assert ActivityType.MEAL in activity_types
    
    def test_module_occupancy_tracking(self, sample_layout, sample_mission_params):
        """Test module occupancy tracking"""
        model = CrewWorkflowModel(sample_layout, sample_mission_params, 24.0)
        
        # Clear initial positions and place agents in specific modules
        for agent in model.crew_agents:
            agent.current_module = None
        
        model.crew_agents[0].current_module = "galley_1"
        model.crew_agents[1].current_module = "galley_1"
        model.crew_agents[2].current_module = "lab_1"
        
        assert model.get_module_occupancy("galley_1") == 2
        assert model.get_module_occupancy("lab_1") == 1
        assert model.get_module_occupancy("sleep_1") == 0
    
    def test_simulation_step(self, sample_layout, sample_mission_params):
        """Test single simulation step execution"""
        model = CrewWorkflowModel(sample_layout, sample_mission_params, 24.0)
        
        initial_time = model.current_time
        model.step()
        
        # Time should advance
        assert model.current_time > initial_time
        
        # Occupancy history should be recorded
        assert len(model.module_occupancy_history) > 0
    
    def test_emergency_evacuation_simulation(self, sample_layout, sample_mission_params):
        """Test emergency evacuation simulation"""
        model = CrewWorkflowModel(sample_layout, sample_mission_params, 24.0)
        
        # Place agents in various modules
        for i, agent in enumerate(model.crew_agents):
            agent.current_module = sample_layout.modules[i % len(sample_layout.modules)].module_id
        
        evacuation_times = model._simulate_emergency_evacuation()
        
        assert len(evacuation_times) == len(model.crew_agents)
        assert all(time >= 0 for time in evacuation_times)


class TestAgentSimulator:
    """Test cases for AgentSimulator class"""
    
    @pytest.mark.asyncio
    async def test_simulate_crew_workflow(self, sample_layout, sample_mission_params):
        """Test crew workflow simulation"""
        simulator = AgentSimulator()
        
        results = await simulator.simulate_crew_workflow(
            layout=sample_layout,
            mission_params=sample_mission_params,
            simulation_duration_hours=2.0  # Short simulation for testing
        )
        
        assert isinstance(results, SimulationResults)
        assert results.total_runtime_hours == 2.0
        assert len(results.crew_utilization) == sample_mission_params.crew_size
        assert isinstance(results.heatmap_data, dict)
        assert isinstance(results.congestion_hotspots, dict)
    
    @pytest.mark.asyncio
    async def test_simulate_emergency_evacuation(self, sample_layout, sample_mission_params):
        """Test emergency evacuation simulation"""
        simulator = AgentSimulator()
        
        results = await simulator.simulate_emergency_evacuation(
            layout=sample_layout,
            mission_params=sample_mission_params,
            emergency_type="fire"
        )
        
        assert results["emergency_type"] == "fire"
        assert "evacuation_times_minutes" in results
        assert "max_evacuation_time" in results
        assert "average_evacuation_time" in results
        assert len(results["crew_positions"]) == sample_mission_params.crew_size
    
    def test_generate_heatmap_data(self, sample_layout, sample_mission_params):
        """Test heatmap data generation"""
        simulator = AgentSimulator()
        
        # Create mock simulation results
        mock_results = SimulationResults(
            total_runtime_hours=24.0,
            movement_events=[],
            module_occupancy={},
            congestion_hotspots={},
            emergency_evacuation_times=[],
            crew_utilization={},
            heatmap_data={"galley_1": 0.8, "lab_1": 0.6, "sleep_1": 0.2}
        )
        
        heatmap = simulator.generate_heatmap_data(mock_results)
        
        assert isinstance(heatmap, dict)
        assert "galley_1" in heatmap
        assert heatmap["galley_1"] == 0.8
    
    def test_analyze_congestion_patterns(self, sample_layout, sample_mission_params):
        """Test congestion pattern analysis"""
        simulator = AgentSimulator()
        
        # Create mock simulation results with congestion
        mock_results = SimulationResults(
            total_runtime_hours=24.0,
            movement_events=[],
            module_occupancy={
                "galley_1": [(0.0, 2), (1.0, 4), (2.0, 3)],
                "lab_1": [(0.0, 1), (1.0, 2), (2.0, 1)]
            },
            congestion_hotspots={"galley_1": 0.15, "lab_1": 0.05},
            emergency_evacuation_times=[],
            crew_utilization={},
            heatmap_data={}
        )
        
        analysis = simulator.analyze_congestion_patterns(mock_results)
        
        assert "peak_congestion" in analysis
        assert "bottlenecks" in analysis
        assert "total_congestion_events" in analysis
        assert "most_congested_module" in analysis
        
        # Galley should be identified as most congested
        assert analysis["most_congested_module"] == "galley_1"


class TestActivityAndScheduling:
    """Test cases for activity scheduling and management"""
    
    def test_activity_creation(self):
        """Test activity creation and properties"""
        activity = Activity(
            activity_type=ActivityType.WORK,
            start_time=9.0,
            duration=4.0,
            location_module="lab_1",
            priority=3
        )
        
        assert activity.activity_type == ActivityType.WORK
        assert activity.start_time == 9.0
        assert activity.duration == 4.0
        assert activity.location_module == "lab_1"
        assert activity.priority == 3
    
    def test_schedule_sorting(self, sample_layout, sample_mission_params):
        """Test that activities are sorted by start time"""
        model = CrewWorkflowModel(sample_layout, sample_mission_params, 24.0)
        agent = CrewAgent("crew_1", model, CrewRole.COMMANDER)
        
        # Add activities out of order
        agent.add_activity(Activity(ActivityType.MEAL, 12.0, 1.0, "galley_1"))
        agent.add_activity(Activity(ActivityType.WORK, 9.0, 3.0, "lab_1"))
        agent.add_activity(Activity(ActivityType.SLEEP, 0.0, 8.0, "sleep_1"))
        
        # Should be sorted by start time
        start_times = [activity.start_time for activity in agent.schedule]
        assert start_times == sorted(start_times)


class TestSimulationIntegration:
    """Integration tests for complete simulation workflow"""
    
    @pytest.mark.asyncio
    async def test_full_simulation_workflow(self, sample_layout, sample_mission_params):
        """Test complete simulation workflow from start to finish"""
        simulator = AgentSimulator()
        
        # Run simulation
        results = await simulator.simulate_crew_workflow(
            layout=sample_layout,
            mission_params=sample_mission_params,
            simulation_duration_hours=4.0
        )
        
        # Verify results structure
        assert isinstance(results, SimulationResults)
        assert results.total_runtime_hours == 4.0
        
        # Generate heatmap
        heatmap = simulator.generate_heatmap_data(results)
        assert isinstance(heatmap, dict)
        
        # Analyze congestion
        congestion_analysis = simulator.analyze_congestion_patterns(results)
        assert "peak_congestion" in congestion_analysis
        assert "bottlenecks" in congestion_analysis
    
    def test_simulation_with_no_airlocks(self, sample_mission_params):
        """Test simulation behavior when no airlocks are present"""
        # Create layout without airlocks
        modules = [
            ModulePlacement(
                module_id="galley_1",
                type=ModuleType.GALLEY,
                position=[0, 0, 0],
                rotation_deg=0,
                connections=[]
            )
        ]
        
        kpis = PerformanceMetrics(
            mean_transit_time=45.0,
            egress_time=120.0,
            mass_total=15000.0,
            power_budget=2500.0,
            thermal_margin=0.15,
            lss_margin=0.20,
            stowage_utilization=0.85
        )
        
        layout = LayoutSpec(
            layout_id="no_airlock_layout",
            envelope_id="test_envelope",
            modules=modules,
            kpis=kpis,
            explainability="Layout without airlocks"
        )
        
        model = CrewWorkflowModel(layout, sample_mission_params, 1.0)
        evacuation_times = model._simulate_emergency_evacuation()
        
        # Should return infinite times when no airlocks available
        assert all(time == float('inf') for time in evacuation_times)
    
    def test_simulation_with_disconnected_modules(self, sample_mission_params):
        """Test simulation behavior with disconnected modules"""
        # Create layout with disconnected modules
        modules = [
            ModulePlacement(
                module_id="galley_1",
                type=ModuleType.GALLEY,
                position=[0, 0, 0],
                rotation_deg=0,
                connections=[]
            ),
            ModulePlacement(
                module_id="lab_1",
                type=ModuleType.LABORATORY,
                position=[10, 0, 0],
                rotation_deg=0,
                connections=[]
            )
        ]
        
        kpis = PerformanceMetrics(
            mean_transit_time=45.0,
            egress_time=120.0,
            mass_total=15000.0,
            power_budget=2500.0,
            thermal_margin=0.15,
            lss_margin=0.20,
            stowage_utilization=0.85
        )
        
        layout = LayoutSpec(
            layout_id="disconnected_layout",
            envelope_id="test_envelope",
            modules=modules,
            kpis=kpis,
            explainability="Layout with disconnected modules"
        )
        
        model = CrewWorkflowModel(layout, sample_mission_params, 1.0)
        agent = model.crew_agents[0]
        agent.current_module = "galley_1"
        
        # Should return empty path for unreachable modules
        path = agent.find_path_to_module("lab_1")
        assert len(path) == 0


if __name__ == "__main__":
    pytest.main([__file__])