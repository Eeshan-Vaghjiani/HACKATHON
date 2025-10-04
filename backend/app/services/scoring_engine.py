"""
Enhanced Scoring Engine for HabitatCanvas

This module implements comprehensive performance metric calculations for habitat layouts.
It integrates human factors analysis, life support systems modeling, and power/thermal
analysis to provide detailed performance assessments.
"""

import math
from typing import List, Dict, Tuple, Optional, Set
import logging
from collections import defaultdict, deque

from app.models.base import (
    ModulePlacement, PerformanceMetrics, EnvelopeSpec, MissionParameters, ModuleType
)
from app.models.module_library import get_module_library, ModuleDefinition
from app.services.human_factors_analyzer import HumanFactorsAnalyzer
from app.services.lss_model import LSSModel, AtmosphereComposition
from app.services.power_thermal_analyzer import PowerThermalAnalyzer

logger = logging.getLogger(__name__)


class EnhancedScoringEngine:
    """
    Enhanced scoring engine that calculates comprehensive performance metrics for habitat layouts.
    
    Integrates specialized analysis engines for human factors, life support systems,
    and power/thermal analysis to provide detailed performance assessments.
    """
    
    def __init__(self):
        self.module_library = get_module_library()
        
        # Initialize specialized analysis engines
        self.human_factors_analyzer = HumanFactorsAnalyzer()
        self.lss_model = LSSModel()
        self.power_thermal_analyzer = PowerThermalAnalyzer()
        
        # Basic system parameters (for fallback calculations)
        self.crew_walking_speed = 1.2  # m/s
        self.corridor_width = 1.0  # meters
        self.emergency_speed_factor = 1.5  # multiplier for emergency movement
    
    async def calculate_metrics(
        self,
        modules: List[ModulePlacement],
        envelope: EnvelopeSpec,
        mission_params: MissionParameters
    ) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics for a layout using specialized analysis engines.
        
        Args:
            modules: List of module placements
            envelope: Habitat envelope specification
            mission_params: Mission parameters and constraints
            
        Returns:
            Computed performance metrics
        """
        logger.info(f"Calculating enhanced metrics for layout with {len(modules)} modules")
        
        try:
            # Perform comprehensive human factors analysis
            human_factors_metrics = await self.human_factors_analyzer.analyze_human_factors(
                modules, envelope, mission_params
            )
            
            # Perform life support systems analysis
            lss_analysis = await self.lss_model.analyze_lss_requirements(
                modules, envelope, mission_params, AtmosphereComposition.SPACE_STATION
            )
            
            # Perform power and thermal analysis
            power_thermal_analysis = await self.power_thermal_analyzer.analyze_power_thermal(
                modules, envelope, mission_params
            )
            
            # Extract key metrics from detailed analyses
            mean_transit_time = human_factors_metrics.mean_transit_time
            egress_time = human_factors_metrics.egress_analysis.max_egress_time
            
            # Calculate mass budget
            mass_total = self._calculate_total_mass(modules)
            mass_total += lss_analysis.total_mass_kg  # Add LSS equipment mass
            mass_total += power_thermal_analysis.power_budget.total_generation_capacity_w * 0.01  # Rough power system mass
            
            # Use power/thermal analysis results
            power_budget = power_thermal_analysis.power_budget.total_consumption_w
            thermal_margin = power_thermal_analysis.thermal_budget.thermal_margin
            
            # Use LSS analysis results
            lss_margin = lss_analysis.lss_margin
            
            # Use human factors stowage analysis
            stowage_utilization = human_factors_metrics.stowage_analysis.utilization_ratio
            
            # Calculate additional scores using enhanced data
            connectivity_score = self._calculate_enhanced_connectivity_score(human_factors_metrics)
            safety_score = self._calculate_enhanced_safety_score(
                human_factors_metrics, lss_analysis, power_thermal_analysis
            )
            efficiency_score = human_factors_metrics.overall_human_factors_score
            volume_utilization = self._calculate_volume_utilization(modules, envelope)
            
            return PerformanceMetrics(
                mean_transit_time=mean_transit_time,
                egress_time=egress_time,
                mass_total=mass_total,
                power_budget=power_budget,
                thermal_margin=thermal_margin,
                lss_margin=lss_margin,
                stowage_utilization=stowage_utilization,
                connectivity_score=connectivity_score,
                safety_score=safety_score,
                efficiency_score=efficiency_score,
                volume_utilization=volume_utilization
            )
            
        except Exception as e:
            logger.warning(f"Enhanced analysis failed, falling back to basic calculations: {str(e)}")
            # Fallback to basic calculations if enhanced analysis fails
            return await self._calculate_basic_metrics(modules, envelope, mission_params)
    
    def _build_connectivity_graph(self, modules: List[ModulePlacement]) -> Dict[str, Dict[str, float]]:
        """Build a graph representing module connectivity"""
        # Simple adjacency list representation: {node_id: {neighbor_id: distance}}
        graph = {}
        
        # Initialize all nodes
        for module in modules:
            graph[module.module_id] = {}
        
        # Add edges based on proximity (simplified connectivity model)
        for i, module_a in enumerate(modules):
            for module_b in modules[i+1:]:
                distance = self._calculate_distance(module_a.position, module_b.position)
                
                # Connect modules if they're within reasonable distance
                # This is a simplified model - real connectivity would consider actual pathways
                max_connection_distance = 5.0  # meters
                if distance <= max_connection_distance:
                    graph[module_a.module_id][module_b.module_id] = distance
                    graph[module_b.module_id][module_a.module_id] = distance
        
        return graph
    
    def _calculate_distance(self, pos1: List[float], pos2: List[float]) -> float:
        """Calculate Euclidean distance between two positions"""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(pos1, pos2)))
    
    def _calculate_mean_transit_time(
        self, 
        modules: List[ModulePlacement], 
        graph: Dict[str, Dict[str, float]]
    ) -> float:
        """Calculate mean transit time between all module pairs"""
        if len(modules) < 2:
            return 0.0
        
        total_time = 0.0
        path_count = 0
        
        # Calculate shortest path times between all pairs
        for i, module_a in enumerate(modules):
            for module_b in modules[i+1:]:
                # Find shortest path using simple BFS
                path_distance = self._find_shortest_path_distance(
                    graph, module_a.module_id, module_b.module_id
                )
                
                if path_distance is not None:
                    # Convert to time (distance / speed)
                    transit_time = path_distance / self.crew_walking_speed
                    total_time += transit_time
                    path_count += 1
                else:
                    # If no path exists, use direct distance as penalty
                    direct_distance = self._calculate_distance(module_a.position, module_b.position)
                    penalty_time = direct_distance / self.crew_walking_speed * 2  # Penalty factor
                    total_time += penalty_time
                    path_count += 1
        
        return total_time / path_count if path_count > 0 else 0.0
    
    def _calculate_egress_time(
        self, 
        modules: List[ModulePlacement], 
        graph: Dict[str, Dict[str, float]]
    ) -> float:
        """Calculate maximum emergency egress time to nearest airlock"""
        # Find all airlocks
        airlocks = [m for m in modules if m.type == ModuleType.AIRLOCK]
        
        if not airlocks:
            # No airlocks - critical safety issue
            return 999.0  # Very high penalty time
        
        max_egress_time = 0.0
        
        # For each non-airlock module, find time to nearest airlock
        for module in modules:
            if module.type == ModuleType.AIRLOCK:
                continue  # Skip airlocks themselves
            
            min_time_to_airlock = float('inf')
            
            for airlock in airlocks:
                # Find shortest path to airlock
                path_distance = self._find_shortest_path_distance(
                    graph, module.module_id, airlock.module_id
                )
                
                if path_distance is not None:
                    # Convert to emergency egress time (faster movement)
                    egress_time = path_distance / (self.crew_walking_speed * self.emergency_speed_factor)
                    min_time_to_airlock = min(min_time_to_airlock, egress_time)
                else:
                    # If no path exists, use direct distance with penalty
                    direct_distance = self._calculate_distance(module.position, airlock.position)
                    penalty_time = direct_distance / (self.crew_walking_speed * self.emergency_speed_factor) * 3
                    min_time_to_airlock = min(min_time_to_airlock, penalty_time)
            
            max_egress_time = max(max_egress_time, min_time_to_airlock)
        
        return max_egress_time
    
    def _calculate_total_mass(self, modules: List[ModulePlacement]) -> float:
        """Calculate total habitat mass"""
        total_mass = 0.0
        
        for module in modules:
            module_def = self._get_module_definition(module.module_id)
            if module_def:
                total_mass += module_def.spec.mass_kg
            else:
                # Use default mass if module definition not found
                total_mass += 1000.0  # kg default
        
        return total_mass
    
    def _calculate_power_budget(
        self, 
        modules: List[ModulePlacement], 
        mission_params: MissionParameters
    ) -> float:
        """Calculate total power consumption"""
        total_power = 0.0
        
        # Module power consumption
        for module in modules:
            module_def = self._get_module_definition(module.module_id)
            if module_def:
                total_power += module_def.spec.power_w
            else:
                # Use default power if module definition not found
                total_power += 500.0  # watts default
        
        # Base crew power consumption
        crew_power = mission_params.crew_size * self.base_power_per_crew
        total_power += crew_power
        
        return total_power
    
    def _calculate_thermal_margin(
        self, 
        modules: List[ModulePlacement], 
        mission_params: MissionParameters,
        envelope: EnvelopeSpec
    ) -> float:
        """Calculate thermal margin (simplified model)"""
        # Calculate heat generation
        crew_heat = mission_params.crew_size * self.crew_heat_generation
        
        # Module heat generation (assume 10% of power becomes heat)
        module_heat = 0.0
        for module in modules:
            module_def = self._get_module_definition(module.module_id)
            if module_def:
                module_heat += module_def.spec.power_w * 0.1
        
        total_heat_generation = crew_heat + module_heat + self.base_thermal_load
        
        # Estimate heat rejection capacity based on envelope surface area
        # This is a very simplified model
        envelope_type_str = envelope.type if isinstance(envelope.type, str) else envelope.type.value
        if envelope_type_str == "cylinder":
            radius = envelope.params['radius']
            length = envelope.params['length']
            surface_area = 2 * math.pi * radius * (radius + length)
        elif envelope_type_str == "box":
            w, h, d = envelope.params['width'], envelope.params['height'], envelope.params['depth']
            surface_area = 2 * (w*h + h*d + w*d)
        else:
            # Default estimate
            surface_area = 200.0  # m²
        
        # Assume heat rejection capacity of 50 W/m² (simplified)
        heat_rejection_capacity = surface_area * 50.0
        
        # Calculate margin
        thermal_margin = (heat_rejection_capacity - total_heat_generation) / heat_rejection_capacity
        
        return max(-0.5, min(1.0, thermal_margin))  # Clamp to reasonable range
    
    def _calculate_lss_margin(
        self, 
        modules: List[ModulePlacement], 
        mission_params: MissionParameters
    ) -> float:
        """Calculate Life Support Systems margin"""
        crew_size = mission_params.crew_size
        
        # Calculate daily consumables requirements
        daily_oxygen_req = crew_size * self.oxygen_consumption_per_crew
        daily_co2_production = crew_size * self.co2_production_per_crew
        daily_water_req = crew_size * self.water_consumption_per_crew
        
        # Estimate LSS capacity based on mechanical modules
        mechanical_modules = [m for m in modules if m.type == ModuleType.MECHANICAL]
        
        if not mechanical_modules:
            return -0.5  # No LSS - critical failure
        
        # Simplified capacity model: each mechanical module supports 4 crew members
        lss_capacity = len(mechanical_modules) * 4
        
        # Calculate margin
        lss_margin = (lss_capacity - crew_size) / lss_capacity if lss_capacity > 0 else -0.5
        
        return max(-0.2, min(1.0, lss_margin))
    
    def _calculate_stowage_utilization(
        self, 
        modules: List[ModulePlacement], 
        mission_params: MissionParameters
    ) -> float:
        """Calculate stowage utilization ratio"""
        # Calculate available stowage volume
        total_stowage = 0.0
        for module in modules:
            module_def = self._get_module_definition(module.module_id)
            if module_def:
                total_stowage += module_def.spec.stowage_m3
        
        # Estimate required stowage based on crew size and mission duration
        # Simplified model: 0.5 m³ per crew member per 30 days
        required_stowage = mission_params.crew_size * (mission_params.duration_days / 30.0) * 0.5
        
        return required_stowage / total_stowage if total_stowage > 0 else 2.0  # High utilization if no stowage
    
    def _calculate_connectivity_score(
        self, 
        modules: List[ModulePlacement], 
        graph: Dict[str, Dict[str, float]]
    ) -> float:
        """Calculate connectivity quality score"""
        if len(modules) < 2:
            return 1.0
        
        # Check if graph is connected
        if not self._is_graph_connected(graph):
            return 0.0  # Disconnected layout is critical failure
        
        # Calculate average path length
        total_path_length = 0.0
        path_count = 0
        
        module_ids = list(graph.keys())
        for i, module_a in enumerate(module_ids):
            for module_b in module_ids[i+1:]:
                path_distance = self._find_shortest_path_distance(graph, module_a, module_b)
                if path_distance is not None:
                    total_path_length += path_distance
                    path_count += 1
        
        avg_path_length = total_path_length / path_count if path_count > 0 else 10.0
        
        # Normalize against ideal path length (lower is better)
        path_score = max(0, 1 - (avg_path_length / 10.0))  # 10m as reference
        
        # Simple connectivity density score
        total_possible_connections = len(modules) * (len(modules) - 1) // 2
        actual_connections = sum(len(neighbors) for neighbors in graph.values()) // 2
        density_score = actual_connections / total_possible_connections if total_possible_connections > 0 else 0
        
        # Combine metrics
        connectivity_score = (path_score + density_score) / 2
        
        return max(0.0, min(1.0, connectivity_score))
    
    def _calculate_enhanced_connectivity_score(self, human_factors_metrics) -> float:
        """Calculate connectivity score using enhanced human factors analysis."""
        # Use accessibility analysis results
        accessibility_scores = []
        for mobility_level, analysis in human_factors_metrics.accessibility_analyses.items():
            accessibility_scores.append(analysis.accessibility_score)
        
        # Average accessibility across all mobility levels
        avg_accessibility = sum(accessibility_scores) / len(accessibility_scores) if accessibility_scores else 0.0
        
        # Factor in congestion hotspots (penalize high congestion)
        congestion_penalty = min(0.2, len(human_factors_metrics.congestion_hotspots) * 0.05)
        
        connectivity_score = avg_accessibility - congestion_penalty
        return max(0.0, min(1.0, connectivity_score))
    
    def _calculate_enhanced_safety_score(
        self, 
        human_factors_metrics, 
        lss_analysis, 
        power_thermal_analysis
    ) -> float:
        """Calculate safety score using comprehensive analysis results."""
        
        # Egress safety component
        egress_score = max(0, 1 - (human_factors_metrics.egress_analysis.max_egress_time / 180.0))
        
        # LSS safety component
        lss_score = max(0, min(1, (lss_analysis.lss_margin + 0.2) / 0.4))  # Normalize -0.2 to 0.2 range
        
        # Power safety component
        power_score = max(0, min(1, (power_thermal_analysis.power_budget.power_margin + 0.1) / 0.3))
        
        # Thermal safety component
        thermal_score = max(0, min(1, (power_thermal_analysis.thermal_budget.thermal_margin + 0.1) / 0.3))
        
        # Critical failures penalty
        critical_penalty = 0.0
        if lss_analysis.critical_failures:
            critical_penalty += len([f for f in lss_analysis.critical_failures if "CRITICAL" in f]) * 0.2
        if power_thermal_analysis.integration_issues:
            critical_penalty += len([i for i in power_thermal_analysis.integration_issues if "CRITICAL" in i]) * 0.2
        
        # Combine components
        safety_score = (
            egress_score * 0.3 +
            lss_score * 0.25 +
            power_score * 0.2 +
            thermal_score * 0.25
        ) - critical_penalty
        
        return max(0.0, min(1.0, safety_score))
    
    async def _calculate_basic_metrics(
        self,
        modules: List[ModulePlacement],
        envelope: EnvelopeSpec,
        mission_params: MissionParameters
    ) -> PerformanceMetrics:
        """
        Fallback basic metric calculations when enhanced analysis fails.
        """
        logger.info("Using basic metric calculations")
        
        # Build connectivity graph
        connectivity_graph = self._build_connectivity_graph(modules)
        
        # Calculate transit metrics
        mean_transit_time = self._calculate_mean_transit_time(modules, connectivity_graph)
        egress_time = self._calculate_egress_time(modules, connectivity_graph)
        
        # Calculate mass and power budgets
        mass_total = self._calculate_total_mass(modules)
        power_budget = self._calculate_power_budget(modules, mission_params)
        
        # Calculate system margins
        thermal_margin = self._calculate_thermal_margin(modules, mission_params, envelope)
        lss_margin = self._calculate_lss_margin(modules, mission_params)
        
        # Calculate stowage utilization
        stowage_utilization = self._calculate_stowage_utilization(modules, mission_params)
        
        # Calculate additional scores
        connectivity_score = self._calculate_connectivity_score(modules, connectivity_graph)
        safety_score = self._calculate_safety_score(modules, egress_time, mission_params)
        efficiency_score = self._calculate_efficiency_score(modules, mean_transit_time, mission_params)
        volume_utilization = self._calculate_volume_utilization(modules, envelope)
        
        return PerformanceMetrics(
            mean_transit_time=mean_transit_time,
            egress_time=egress_time,
            mass_total=mass_total,
            power_budget=power_budget,
            thermal_margin=thermal_margin,
            lss_margin=lss_margin,
            stowage_utilization=stowage_utilization,
            connectivity_score=connectivity_score,
            safety_score=safety_score,
            efficiency_score=efficiency_score,
            volume_utilization=volume_utilization
        )
    
    def _calculate_safety_score(
        self, 
        modules: List[ModulePlacement], 
        egress_time: float,
        mission_params: MissionParameters
    ) -> float:
        """Calculate overall safety assessment score"""
        # Egress time component (target < 3 minutes)
        egress_score = max(0, 1 - (egress_time / 180.0))
        
        # Airlock redundancy component
        airlocks = [m for m in modules if m.type == ModuleType.AIRLOCK]
        airlock_score = min(1.0, len(airlocks) / 2.0)  # Target: 2 airlocks
        
        # Medical facility component
        medical_modules = [m for m in modules if m.type == ModuleType.MEDICAL]
        medical_score = 1.0 if medical_modules else 0.5
        
        # Combine components
        safety_score = (egress_score * 0.5 + airlock_score * 0.3 + medical_score * 0.2)
        
        return max(0.0, min(1.0, safety_score))
    
    def _calculate_efficiency_score(
        self, 
        modules: List[ModulePlacement], 
        mean_transit_time: float,
        mission_params: MissionParameters
    ) -> float:
        """Calculate operational efficiency score"""
        # Transit time component (target < 1 minute)
        transit_score = max(0, 1 - (mean_transit_time / 60.0))
        
        # Module adjacency component (check if related modules are close)
        adjacency_score = self._calculate_adjacency_score(modules)
        
        # Combine components
        efficiency_score = (transit_score * 0.7 + adjacency_score * 0.3)
        
        return max(0.0, min(1.0, efficiency_score))
    
    def _calculate_adjacency_score(self, modules: List[ModulePlacement]) -> float:
        """Calculate score based on module adjacency preferences"""
        if len(modules) < 2:
            return 1.0
        
        total_score = 0.0
        scored_pairs = 0
        
        for i, module_a in enumerate(modules):
            module_def_a = self._get_module_definition(module_a.module_id)
            if not module_def_a:
                continue
            
            for module_b in modules[i+1:]:
                distance = self._calculate_distance(module_a.position, module_b.position)
                
                # Check adjacency preferences
                if module_b.type in module_def_a.spec.adjacency_preferences:
                    # Preferred modules should be close (< 3m gets full score)
                    score = max(0, 1 - (distance / 3.0))
                    total_score += score
                    scored_pairs += 1
                elif module_b.type in module_def_a.spec.adjacency_restrictions:
                    # Restricted modules should be far (> 5m gets full score)
                    score = min(1, distance / 5.0)
                    total_score += score
                    scored_pairs += 1
        
        return total_score / scored_pairs if scored_pairs > 0 else 0.8  # Default neutral score
    
    def _calculate_volume_utilization(
        self, 
        modules: List[ModulePlacement], 
        envelope: EnvelopeSpec
    ) -> float:
        """Calculate habitat volume utilization ratio"""
        # Calculate total module volume
        total_module_volume = 0.0
        for module in modules:
            module_def = self._get_module_definition(module.module_id)
            if module_def:
                total_module_volume += module_def.spec.bbox_m.volume
        
        # Calculate envelope volume
        envelope_volume = envelope.volume
        
        utilization = total_module_volume / envelope_volume if envelope_volume > 0 else 0.0
        # Clamp to valid range for Pydantic validation (0.0 to 1.0)
        return min(1.0, max(0.0, utilization))
    
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
    
    def _find_shortest_path_distance(
        self, 
        graph: Dict[str, Dict[str, float]], 
        start: str, 
        end: str
    ) -> Optional[float]:
        """Find shortest path distance between two nodes using Dijkstra's algorithm"""
        if start not in graph or end not in graph:
            return None
        
        if start == end:
            return 0.0
        
        # Dijkstra's algorithm
        distances = {node: float('inf') for node in graph}
        distances[start] = 0.0
        visited = set()
        
        while True:
            # Find unvisited node with minimum distance
            current = None
            min_distance = float('inf')
            
            for node in graph:
                if node not in visited and distances[node] < min_distance:
                    min_distance = distances[node]
                    current = node
            
            if current is None or current == end:
                break
            
            visited.add(current)
            
            # Update distances to neighbors
            for neighbor, edge_weight in graph[current].items():
                if neighbor not in visited:
                    new_distance = distances[current] + edge_weight
                    if new_distance < distances[neighbor]:
                        distances[neighbor] = new_distance
        
        return distances[end] if distances[end] != float('inf') else None
    
    def _is_graph_connected(self, graph: Dict[str, Dict[str, float]]) -> bool:
        """Check if graph is connected using BFS"""
        if not graph:
            return True
        
        # Start BFS from first node
        start_node = next(iter(graph.keys()))
        visited = set()
        queue = deque([start_node])
        visited.add(start_node)
        
        while queue:
            current = queue.popleft()
            for neighbor in graph[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        return len(visited) == len(graph)