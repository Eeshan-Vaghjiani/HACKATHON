"""
Crew Workflow Simulation Engine

This module implements an agent-based simulation system for modeling crew behavior,
movement patterns, and workflow within habitat layouts. It uses the Mesa framework
to create discrete event simulations that help analyze layout performance under
realistic operational conditions.

Key Features:
- Agent-based crew modeling with individual schedules and preferences
- Pathfinding and movement simulation within habitat layouts
- Congestion detection and queuing analysis
- Emergency evacuation scenario modeling
- Heatmap generation for traffic patterns
"""

import numpy as np
import networkx as nx
from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import ContinuousSpace
from mesa.datacollection import DataCollector
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import random
from datetime import datetime, timedelta
import logging

from ..models.base import LayoutSpec, ModulePlacement, MissionParameters, PerformanceMetrics

logger = logging.getLogger(__name__)


class ActivityType(Enum):
    """Types of crew activities"""
    SLEEP = "sleep"
    WORK = "work"
    EXERCISE = "exercise"
    MEAL = "meal"
    HYGIENE = "hygiene"
    RECREATION = "recreation"
    MAINTENANCE = "maintenance"
    EMERGENCY = "emergency"
    TRANSIT = "transit"


class CrewRole(Enum):
    """Crew member roles"""
    COMMANDER = "commander"
    PILOT = "pilot"
    ENGINEER = "engineer"
    SCIENTIST = "scientist"
    MEDIC = "medic"


@dataclass
class Activity:
    """Represents a scheduled activity"""
    activity_type: ActivityType
    start_time: float  # Hours from mission start
    duration: float    # Hours
    location_module: str
    priority: int = 1  # 1=low, 5=critical
    participants: List[str] = field(default_factory=list)


@dataclass
class MovementEvent:
    """Records crew movement for analysis"""
    agent_id: str
    timestamp: float
    from_module: str
    to_module: str
    path: List[str]
    travel_time: float
    congestion_delay: float = 0.0


@dataclass
class SimulationResults:
    """Results from crew workflow simulation"""
    total_runtime_hours: float
    movement_events: List[MovementEvent]
    module_occupancy: Dict[str, List[Tuple[float, int]]]  # module_id -> [(time, occupancy)]
    congestion_hotspots: Dict[str, float]  # module_id -> congestion_score
    emergency_evacuation_times: List[float]
    crew_utilization: Dict[str, float]  # crew_id -> utilization_percentage
    heatmap_data: Dict[str, float]  # module_id -> traffic_intensity


class CrewAgent(Agent):
    """Individual crew member agent"""
    
    def __init__(self, unique_id: str, model: 'CrewWorkflowModel', role: CrewRole):
        super().__init__(unique_id, model)
        self.role = role
        self.current_module = None
        self.target_module = None
        self.current_activity = None
        self.schedule: List[Activity] = []
        self.path_to_target: List[str] = []
        self.movement_speed = 1.0  # modules per time step
        self.stress_level = 0.0
        self.fatigue_level = 0.0
        
        # Movement tracking
        self.position_history: List[Tuple[float, str]] = []
        self.total_distance_traveled = 0.0
        
    def add_activity(self, activity: Activity):
        """Add an activity to the crew member's schedule"""
        self.schedule.append(activity)
        self.schedule.sort(key=lambda a: a.start_time)
    
    def get_current_activity(self, current_time: float) -> Optional[Activity]:
        """Get the current activity based on simulation time"""
        for activity in self.schedule:
            if activity.start_time <= current_time < activity.start_time + activity.duration:
                return activity
        return None
    
    def find_path_to_module(self, target_module: str) -> List[str]:
        """Find shortest path to target module using habitat connectivity graph"""
        if self.current_module == target_module:
            return []
        
        try:
            path = nx.shortest_path(
                self.model.connectivity_graph,
                self.current_module,
                target_module
            )
            return path[1:]  # Exclude current module
        except nx.NetworkXNoPath:
            logger.warning(f"No path found from {self.current_module} to {target_module}")
            return []
    
    def move_towards_target(self):
        """Move one step towards target module"""
        if not self.path_to_target:
            return
        
        next_module = self.path_to_target[0]
        
        # Check for congestion in target module
        occupancy = self.model.get_module_occupancy(next_module)
        capacity = self.model.module_capacities.get(next_module, 4)
        
        if occupancy >= capacity:
            # Module is at capacity, wait
            self.model.record_congestion_event(next_module, self.unique_id)
            return
        
        # Move to next module
        previous_module = self.current_module
        self.current_module = next_module
        self.path_to_target.pop(0)
        
        # Record movement
        self.position_history.append((self.model.current_time, self.current_module))
        self.total_distance_traveled += 1.0
        
        # Update model tracking
        self.model.record_movement_event(
            agent_id=self.unique_id,
            from_module=previous_module,
            to_module=self.current_module,
            timestamp=self.model.current_time
        )
    
    def step(self):
        """Execute one simulation step"""
        current_time = self.model.current_time
        
        # Get current scheduled activity
        scheduled_activity = self.get_current_activity(current_time)
        
        if scheduled_activity and scheduled_activity != self.current_activity:
            # New activity started
            self.current_activity = scheduled_activity
            self.target_module = scheduled_activity.location_module
            
            if self.current_module != self.target_module:
                self.path_to_target = self.find_path_to_module(self.target_module)
        
        # Move towards target if needed
        if self.path_to_target:
            self.move_towards_target()
        
        # Update stress and fatigue based on current conditions
        self._update_physiological_state()
    
    def _update_physiological_state(self):
        """Update crew member's stress and fatigue levels"""
        # Increase fatigue over time
        self.fatigue_level += 0.01
        
        # Increase stress if in congested areas
        if self.current_module:
            occupancy = self.model.get_module_occupancy(self.current_module)
            capacity = self.model.module_capacities.get(self.current_module, 4)
            if occupancy > capacity * 0.8:
                self.stress_level += 0.05
        
        # Reduce stress and fatigue during sleep
        if self.current_activity and self.current_activity.activity_type == ActivityType.SLEEP:
            self.stress_level = max(0, self.stress_level - 0.1)
            self.fatigue_level = max(0, self.fatigue_level - 0.2)
        
        # Cap values
        self.stress_level = min(1.0, self.stress_level)
        self.fatigue_level = min(1.0, self.fatigue_level)


class CrewWorkflowModel(Model):
    """Mesa model for crew workflow simulation"""
    
    def __init__(self, layout: LayoutSpec, mission_params: MissionParameters, 
                 simulation_duration_hours: float = 24.0):
        super().__init__()
        
        self.layout = layout
        self.mission_params = mission_params
        self.simulation_duration = simulation_duration_hours
        self.current_time = 0.0
        self.time_step = 0.25  # 15-minute intervals
        
        # Build connectivity graph from layout
        self.connectivity_graph = self._build_connectivity_graph()
        
        # Module capacities (crew members that can occupy simultaneously)
        self.module_capacities = self._calculate_module_capacities()
        
        # Tracking data
        self.movement_events: List[MovementEvent] = []
        self.congestion_events: List[Tuple[float, str, str]] = []  # (time, module, agent)
        self.module_occupancy_history: Dict[str, List[Tuple[float, int]]] = {}
        
        # Initialize crew agents
        self.crew_agents: List[CrewAgent] = []
        self._create_crew_agents()
        
        # Schedule activities for crew
        self._generate_crew_schedules()
        
        # Mesa components
        self.schedule = RandomActivation(self)
        for agent in self.crew_agents:
            self.schedule.add(agent)
        
        # Data collection
        self.datacollector = DataCollector(
            model_reporters={
                "total_crew": lambda m: len(m.crew_agents),
                "average_stress": lambda m: np.mean([a.stress_level for a in m.crew_agents]),
                "average_fatigue": lambda m: np.mean([a.fatigue_level for a in m.crew_agents]),
                "congestion_events": lambda m: len(m.congestion_events)
            },
            agent_reporters={
                "stress_level": "stress_level",
                "fatigue_level": "fatigue_level",
                "current_module": "current_module"
            }
        )
    
    def _build_connectivity_graph(self) -> nx.Graph:
        """Build NetworkX graph representing module connectivity"""
        G = nx.Graph()
        
        # Add all modules as nodes
        for module in self.layout.modules:
            G.add_node(module.module_id)
        
        # Add edges based on module connections
        for module in self.layout.modules:
            for connection in module.connections:
                if G.has_node(connection):
                    G.add_edge(module.module_id, connection)
        
        return G
    
    def _calculate_module_capacities(self) -> Dict[str, int]:
        """Calculate maximum occupancy for each module type"""
        capacities = {}
        
        for module in self.layout.modules:
            # Base capacity on module type and size
            module_type = module.type if isinstance(module.type, str) else module.type.value
            if module_type == "sleep_quarter":
                capacities[module.module_id] = 1  # Private quarters
            elif module_type == "galley":
                capacities[module.module_id] = min(6, self.mission_params.crew_size)
            elif module_type == "laboratory":
                capacities[module.module_id] = 3
            elif module_type == "exercise":
                capacities[module.module_id] = 2
            elif module_type == "medical":
                capacities[module.module_id] = 2
            else:
                capacities[module.module_id] = 4  # Default capacity
        
        return capacities
    
    def _create_crew_agents(self):
        """Create crew member agents based on mission parameters"""
        roles = list(CrewRole)
        
        for i in range(self.mission_params.crew_size):
            role = roles[i % len(roles)]  # Cycle through roles
            agent_id = f"crew_{i+1}"
            
            agent = CrewAgent(agent_id, self, role)
            
            # Assign initial location (sleep quarters if available)
            sleep_modules = [m for m in self.layout.modules 
                           if (m.type if isinstance(m.type, str) else m.type.value) == "sleep_quarter"]
            if sleep_modules and i < len(sleep_modules):
                agent.current_module = sleep_modules[i].module_id
            else:
                # Assign to first available module
                agent.current_module = self.layout.modules[0].module_id
            
            self.crew_agents.append(agent)
    
    def _generate_crew_schedules(self):
        """Generate realistic daily schedules for crew members"""
        # Standard daily schedule template
        base_schedule = [
            (ActivityType.SLEEP, 0.0, 8.0, "sleep_quarter"),
            (ActivityType.HYGIENE, 8.0, 0.5, "hygiene"),
            (ActivityType.MEAL, 8.5, 1.0, "galley"),
            (ActivityType.WORK, 9.5, 4.0, "laboratory"),
            (ActivityType.MEAL, 13.5, 1.0, "galley"),
            (ActivityType.WORK, 14.5, 4.0, "laboratory"),
            (ActivityType.EXERCISE, 18.5, 1.5, "exercise"),
            (ActivityType.MEAL, 20.0, 1.0, "galley"),
            (ActivityType.RECREATION, 21.0, 2.0, "galley"),
            (ActivityType.HYGIENE, 23.0, 0.5, "hygiene"),
        ]
        
        for agent in self.crew_agents:
            for activity_type, start_time, duration, preferred_module_type in base_schedule:
                # Find appropriate module for activity
                target_modules = [m for m in self.layout.modules 
                                if (m.type if isinstance(m.type, str) else m.type.value) == preferred_module_type]
                
                if not target_modules:
                    # Fallback to any available module
                    target_modules = self.layout.modules
                
                if target_modules:
                    # Add some randomization to start times
                    randomized_start = start_time + random.uniform(-0.25, 0.25)
                    randomized_duration = duration + random.uniform(-0.1, 0.1)
                    
                    activity = Activity(
                        activity_type=activity_type,
                        start_time=randomized_start,
                        duration=max(0.1, randomized_duration),
                        location_module=random.choice(target_modules).module_id,
                        priority=3 if activity_type in [ActivityType.MEAL, ActivityType.SLEEP] else 2
                    )
                    
                    agent.add_activity(activity)
    
    def get_module_occupancy(self, module_id: str) -> int:
        """Get current number of crew members in a module"""
        return sum(1 for agent in self.crew_agents if agent.current_module == module_id)
    
    def record_movement_event(self, agent_id: str, from_module: str, 
                            to_module: str, timestamp: float):
        """Record a crew movement event"""
        event = MovementEvent(
            agent_id=agent_id,
            timestamp=timestamp,
            from_module=from_module,
            to_module=to_module,
            path=[from_module, to_module],
            travel_time=self.time_step
        )
        self.movement_events.append(event)
    
    def record_congestion_event(self, module_id: str, agent_id: str):
        """Record a congestion event"""
        self.congestion_events.append((self.current_time, module_id, agent_id))
    
    def step(self):
        """Execute one simulation step"""
        self.current_time += self.time_step
        
        # Record current module occupancy
        for module in self.layout.modules:
            occupancy = self.get_module_occupancy(module.module_id)
            if module.module_id not in self.module_occupancy_history:
                self.module_occupancy_history[module.module_id] = []
            self.module_occupancy_history[module.module_id].append(
                (self.current_time, occupancy)
            )
        
        # Step all agents
        self.schedule.step()
        
        # Collect data
        self.datacollector.collect(self)
    
    def run_simulation(self) -> SimulationResults:
        """Run the complete simulation and return results"""
        logger.info(f"Starting crew workflow simulation for {self.simulation_duration} hours")
        
        steps = int(self.simulation_duration / self.time_step)
        
        for _ in range(steps):
            self.step()
        
        # Generate results
        results = self._generate_simulation_results()
        
        logger.info(f"Simulation completed. Recorded {len(self.movement_events)} movement events")
        
        return results
    
    def _generate_simulation_results(self) -> SimulationResults:
        """Generate comprehensive simulation results"""
        # Calculate congestion hotspots
        congestion_hotspots = {}
        for module_id in [m.module_id for m in self.layout.modules]:
            congestion_count = sum(1 for _, mod_id, _ in self.congestion_events if mod_id == module_id)
            congestion_hotspots[module_id] = congestion_count / self.simulation_duration
        
        # Calculate crew utilization
        crew_utilization = {}
        for agent in self.crew_agents:
            active_time = sum(activity.duration for activity in agent.schedule 
                            if activity.activity_type != ActivityType.SLEEP)
            utilization = (active_time / self.simulation_duration) * 100
            crew_utilization[agent.unique_id] = utilization
        
        # Generate heatmap data (traffic intensity)
        heatmap_data = {}
        for module_id in [m.module_id for m in self.layout.modules]:
            traffic_count = sum(1 for event in self.movement_events 
                              if event.to_module == module_id or event.from_module == module_id)
            heatmap_data[module_id] = traffic_count / self.simulation_duration
        
        # Simulate emergency evacuation (simplified)
        evacuation_times = self._simulate_emergency_evacuation()
        
        return SimulationResults(
            total_runtime_hours=self.simulation_duration,
            movement_events=self.movement_events,
            module_occupancy=self.module_occupancy_history,
            congestion_hotspots=congestion_hotspots,
            emergency_evacuation_times=evacuation_times,
            crew_utilization=crew_utilization,
            heatmap_data=heatmap_data
        )
    
    def _simulate_emergency_evacuation(self) -> List[float]:
        """Simulate emergency evacuation scenarios"""
        evacuation_times = []
        
        # Find airlock modules
        airlocks = [m for m in self.layout.modules 
                   if (m.type if isinstance(m.type, str) else m.type.value) == "airlock"]
        
        if not airlocks:
            logger.warning("No airlocks found for evacuation simulation")
            return [float('inf')] * len(self.crew_agents)
        
        for agent in self.crew_agents:
            if agent.current_module:
                # Find shortest path to nearest airlock
                min_time = float('inf')
                for airlock in airlocks:
                    try:
                        path_length = nx.shortest_path_length(
                            self.connectivity_graph,
                            agent.current_module,
                            airlock.module_id
                        )
                        # Assume 2 minutes per module during emergency
                        evacuation_time = path_length * 2.0
                        min_time = min(min_time, evacuation_time)
                    except nx.NetworkXNoPath:
                        continue
                
                evacuation_times.append(min_time)
            else:
                evacuation_times.append(0.0)
        
        return evacuation_times


class AgentSimulator:
    """Main interface for agent-based simulation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def simulate_crew_workflow(
        self, 
        layout: LayoutSpec, 
        mission_params: MissionParameters,
        simulation_duration_hours: float = 24.0
    ) -> SimulationResults:
        """
        Run agent-based simulation of crew daily activities
        
        Args:
            layout: The habitat layout to simulate
            mission_params: Mission parameters including crew size and duration
            simulation_duration_hours: How long to run the simulation
            
        Returns:
            SimulationResults containing movement patterns, congestion analysis, etc.
        """
        try:
            # Create and run simulation model
            model = CrewWorkflowModel(layout, mission_params, simulation_duration_hours)
            results = model.run_simulation()
            
            self.logger.info(
                f"Simulation completed successfully. "
                f"Processed {len(results.movement_events)} movement events"
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Simulation failed: {str(e)}")
            raise
    
    async def simulate_emergency_evacuation(
        self,
        layout: LayoutSpec,
        mission_params: MissionParameters,
        emergency_type: str = "fire"
    ) -> Dict[str, Any]:
        """
        Simulate emergency evacuation scenarios
        
        Args:
            layout: The habitat layout
            mission_params: Mission parameters
            emergency_type: Type of emergency to simulate
            
        Returns:
            Dictionary with evacuation analysis results
        """
        try:
            # Run short simulation focused on evacuation
            model = CrewWorkflowModel(layout, mission_params, 1.0)  # 1 hour simulation
            
            # Override crew positions to random locations for emergency scenario
            for agent in model.crew_agents:
                agent.current_module = random.choice(model.layout.modules).module_id
            
            evacuation_times = model._simulate_emergency_evacuation()
            
            return {
                "emergency_type": emergency_type,
                "evacuation_times_minutes": evacuation_times,
                "max_evacuation_time": max(evacuation_times) if evacuation_times else 0,
                "average_evacuation_time": np.mean(evacuation_times) if evacuation_times else 0,
                "crew_positions": {agent.unique_id: agent.current_module for agent in model.crew_agents}
            }
            
        except Exception as e:
            self.logger.error(f"Emergency evacuation simulation failed: {str(e)}")
            raise
    
    def generate_heatmap_data(self, simulation_results: SimulationResults) -> Dict[str, float]:
        """
        Generate heatmap data for visualization
        
        Args:
            simulation_results: Results from crew workflow simulation
            
        Returns:
            Dictionary mapping module IDs to traffic intensity values
        """
        return simulation_results.heatmap_data
    
    def analyze_congestion_patterns(self, simulation_results: SimulationResults) -> Dict[str, Any]:
        """
        Analyze congestion patterns from simulation results
        
        Args:
            simulation_results: Results from crew workflow simulation
            
        Returns:
            Dictionary with congestion analysis
        """
        # Find peak congestion times
        peak_congestion = {}
        for module_id, occupancy_history in simulation_results.module_occupancy.items():
            if occupancy_history:
                max_occupancy = max(occupancy for _, occupancy in occupancy_history)
                peak_time = next(time for time, occupancy in occupancy_history 
                               if occupancy == max_occupancy)
                peak_congestion[module_id] = {
                    "max_occupancy": max_occupancy,
                    "peak_time_hours": peak_time
                }
        
        # Identify bottlenecks
        bottlenecks = {
            module_id: score for module_id, score in simulation_results.congestion_hotspots.items()
            if score > 0.1  # Threshold for significant congestion
        }
        
        return {
            "peak_congestion": peak_congestion,
            "bottlenecks": bottlenecks,
            "total_congestion_events": sum(simulation_results.congestion_hotspots.values()),
            "most_congested_module": max(simulation_results.congestion_hotspots.items(), 
                                       key=lambda x: x[1])[0] if simulation_results.congestion_hotspots else None
        }