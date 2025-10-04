"""
Human Factors Analysis Engine for HabitatCanvas

This module implements comprehensive human factors analysis including:
- Mean transit time calculation using shortest path algorithms
- Emergency egress time computation with bottleneck detection
- Accessibility scoring for crew with mobility constraints
- Stowage utilization calculator based on crew requirements

Requirements: 4.1, 4.2, 4.5, 5.4
"""

import math
import networkx as nx
from typing import List, Dict, Tuple, Optional, Set, Any
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import logging

from app.models.base import (
    ModulePlacement, EnvelopeSpec, MissionParameters, ModuleType
)
from app.models.module_library import get_module_library, ModuleDefinition

logger = logging.getLogger(__name__)


class MobilityLevel(str, Enum):
    """Crew mobility constraint levels"""
    FULL = "full"
    LIMITED = "limited"
    WHEELCHAIR = "wheelchair"
    EMERGENCY_ONLY = "emergency_only"


class ActivityType(str, Enum):
    """Types of crew activities for transit analysis"""
    SLEEP_TO_WORK = "sleep_to_work"
    WORK_TO_GALLEY = "work_to_galley"
    GALLEY_TO_EXERCISE = "galley_to_exercise"
    EXERCISE_TO_MEDICAL = "exercise_to_medical"
    ANY_TO_AIRLOCK = "any_to_airlock"
    EMERGENCY_EGRESS = "emergency_egress"


@dataclass
class TransitPath:
    """Represents a path between two modules"""
    start_module: str
    end_module: str
    distance: float
    travel_time: float
    bottlenecks: List[str]
    accessibility_score: float


@dataclass
class EgressAnalysis:
    """Emergency egress analysis results"""
    max_egress_time: float
    avg_egress_time: float
    bottlenecks: List[Dict[str, Any]]
    critical_paths: List[TransitPath]
    airlock_utilization: Dict[str, float]


@dataclass
class AccessibilityAnalysis:
    """Accessibility analysis for different mobility levels"""
    mobility_level: MobilityLevel
    accessible_modules: Set[str]
    inaccessible_modules: Set[str]
    accessibility_score: float
    required_modifications: List[str]


@dataclass
class StowageAnalysis:
    """Stowage utilization analysis"""
    total_available_m3: float
    total_required_m3: float
    utilization_ratio: float
    per_module_utilization: Dict[str, float]
    overcrowded_modules: List[str]
    underutilized_modules: List[str]
    recommendations: List[str]


@dataclass
class HumanFactorsMetrics:
    """Comprehensive human factors analysis results"""
    mean_transit_time: float
    egress_analysis: EgressAnalysis
    accessibility_analyses: Dict[MobilityLevel, AccessibilityAnalysis]
    stowage_analysis: StowageAnalysis
    activity_transit_times: Dict[ActivityType, float]
    congestion_hotspots: List[Dict[str, Any]]
    overall_human_factors_score: float


class HumanFactorsAnalyzer:
    """
    Comprehensive human factors analysis engine for habitat layouts.
    
    Analyzes crew movement patterns, accessibility, emergency egress,
    and stowage utilization to optimize habitat design for human performance.
    """
    
    def __init__(self):
        self.module_library = get_module_library()
        
        # Movement parameters
        self.walking_speeds = {
            MobilityLevel.FULL: 1.4,  # m/s - normal walking speed
            MobilityLevel.LIMITED: 1.0,  # m/s - reduced mobility
            MobilityLevel.WHEELCHAIR: 0.8,  # m/s - wheelchair navigation
            MobilityLevel.EMERGENCY_ONLY: 0.3  # m/s - emergency assistance required
        }
        
        self.emergency_speed_multiplier = 1.8  # Emergency movement speed increase
        
        # Corridor and clearance requirements
        self.min_corridor_width = {
            MobilityLevel.FULL: 0.8,  # meters
            MobilityLevel.LIMITED: 0.9,  # meters
            MobilityLevel.WHEELCHAIR: 1.2,  # meters
            MobilityLevel.EMERGENCY_ONLY: 1.4  # meters - for assistance
        }
        
        # Stowage requirements per crew member (m³/person/day)
        self.stowage_requirements = {
            "food": 0.003,  # Food and consumables
            "clothing": 0.002,  # Clothing and personal items
            "tools": 0.004,  # Tools and equipment
            "science": 0.005,  # Science equipment and samples
            "emergency": 0.002,  # Emergency supplies
            "spare_parts": 0.003,  # Spare parts and maintenance
        }
        
        # Activity frequency weights (trips per day)
        self.activity_frequencies = {
            ActivityType.SLEEP_TO_WORK: 2.0,  # Morning and evening
            ActivityType.WORK_TO_GALLEY: 3.0,  # Meals
            ActivityType.GALLEY_TO_EXERCISE: 1.0,  # Daily exercise
            ActivityType.EXERCISE_TO_MEDICAL: 0.2,  # Weekly checkups
            ActivityType.ANY_TO_AIRLOCK: 0.1,  # EVA activities
        }
    
    async def analyze_human_factors(
        self,
        modules: List[ModulePlacement],
        envelope: EnvelopeSpec,
        mission_params: MissionParameters
    ) -> HumanFactorsMetrics:
        """
        Perform comprehensive human factors analysis.
        
        Args:
            modules: List of module placements
            envelope: Habitat envelope specification
            mission_params: Mission parameters and constraints
            
        Returns:
            Comprehensive human factors metrics
        """
        logger.info(f"Starting human factors analysis for {len(modules)} modules")
        
        # Build detailed connectivity graph with pathways
        connectivity_graph = self._build_detailed_connectivity_graph(modules, envelope)
        
        # Calculate mean transit time using shortest path algorithms
        mean_transit_time = await self._calculate_mean_transit_time(
            modules, connectivity_graph, mission_params
        )
        
        # Perform emergency egress analysis with bottleneck detection
        egress_analysis = await self._analyze_emergency_egress(
            modules, connectivity_graph, mission_params
        )
        
        # Analyze accessibility for different mobility levels
        accessibility_analyses = await self._analyze_accessibility(
            modules, connectivity_graph, envelope
        )
        
        # Calculate stowage utilization based on crew requirements
        stowage_analysis = await self._analyze_stowage_utilization(
            modules, mission_params
        )
        
        # Calculate activity-specific transit times
        activity_transit_times = await self._calculate_activity_transit_times(
            modules, connectivity_graph
        )
        
        # Identify congestion hotspots
        congestion_hotspots = await self._identify_congestion_hotspots(
            modules, connectivity_graph, mission_params
        )
        
        # Calculate overall human factors score
        overall_score = self._calculate_overall_human_factors_score(
            mean_transit_time, egress_analysis, accessibility_analyses, 
            stowage_analysis, mission_params
        )
        
        return HumanFactorsMetrics(
            mean_transit_time=mean_transit_time,
            egress_analysis=egress_analysis,
            accessibility_analyses=accessibility_analyses,
            stowage_analysis=stowage_analysis,
            activity_transit_times=activity_transit_times,
            congestion_hotspots=congestion_hotspots,
            overall_human_factors_score=overall_score
        )
    
    def _build_detailed_connectivity_graph(
        self, 
        modules: List[ModulePlacement], 
        envelope: EnvelopeSpec
    ) -> nx.Graph:
        """
        Build detailed connectivity graph using NetworkX with pathway analysis.
        
        Creates a graph where nodes are modules and edges represent pathways
        with attributes for distance, width, and accessibility constraints.
        """
        G = nx.Graph()
        
        # Add module nodes with attributes
        for module in modules:
            module_def = self._get_module_definition(module.module_id)
            G.add_node(
                module.module_id,
                position=module.position,
                module_type=module.type,
                bbox=module_def.spec.bbox_m if module_def else None,
                connections=module.connections
            )
        
        # Add edges based on connectivity and spatial relationships
        for i, module_a in enumerate(modules):
            for module_b in modules[i+1:]:
                # Calculate pathway characteristics
                pathway = self._analyze_pathway(module_a, module_b, modules, envelope)
                
                if pathway['is_connected']:
                    G.add_edge(
                        module_a.module_id,
                        module_b.module_id,
                        distance=pathway['distance'],
                        width=pathway['width'],
                        clearance=pathway['clearance'],
                        accessibility_level=pathway['accessibility_level'],
                        bottleneck_factor=pathway['bottleneck_factor']
                    )
        
        return G
    
    def _analyze_pathway(
        self, 
        module_a: ModulePlacement, 
        module_b: ModulePlacement,
        all_modules: List[ModulePlacement],
        envelope: EnvelopeSpec
    ) -> Dict[str, Any]:
        """
        Analyze pathway characteristics between two modules.
        
        Returns pathway properties including distance, width, clearance,
        and accessibility constraints.
        """
        # Calculate direct distance
        distance = self._calculate_distance(module_a.position, module_b.position)
        
        # Check if modules are explicitly connected
        is_explicitly_connected = (
            module_b.module_id in module_a.connections or
            module_a.module_id in module_b.connections
        )
        
        # Determine if pathway exists based on distance and obstacles
        max_connection_distance = 8.0  # meters - maximum reasonable pathway length
        is_connected = is_explicitly_connected or distance <= max_connection_distance
        
        # Check for obstacles (other modules blocking the path)
        obstacles = self._check_pathway_obstacles(module_a, module_b, all_modules)
        
        # Calculate effective pathway width considering obstacles
        base_width = 1.2  # meters - standard corridor width
        width_reduction = len(obstacles) * 0.2  # Reduce width for each obstacle
        effective_width = max(0.6, base_width - width_reduction)
        
        # Calculate clearance (minimum distance to obstacles)
        clearance = self._calculate_pathway_clearance(module_a, module_b, all_modules)
        
        # Determine accessibility level based on width and clearance
        accessibility_level = self._determine_accessibility_level(effective_width, clearance)
        
        # Calculate bottleneck factor (1.0 = no bottleneck, >1.0 = bottleneck)
        bottleneck_factor = max(1.0, base_width / effective_width)
        
        return {
            'is_connected': is_connected and not obstacles,
            'distance': distance,
            'width': effective_width,
            'clearance': clearance,
            'accessibility_level': accessibility_level,
            'bottleneck_factor': bottleneck_factor,
            'obstacles': obstacles
        }
    
    def _check_pathway_obstacles(
        self, 
        module_a: ModulePlacement, 
        module_b: ModulePlacement,
        all_modules: List[ModulePlacement]
    ) -> List[str]:
        """Check for modules that obstruct the pathway between two modules."""
        obstacles = []
        
        # Simple line-of-sight check
        for module in all_modules:
            if module.module_id in [module_a.module_id, module_b.module_id]:
                continue
            
            # Check if module intersects with the pathway
            if self._point_to_line_distance(
                module.position, module_a.position, module_b.position
            ) < 1.5:  # 1.5m obstacle detection radius
                obstacles.append(module.module_id)
        
        return obstacles
    
    def _point_to_line_distance(
        self, 
        point: List[float], 
        line_start: List[float], 
        line_end: List[float]
    ) -> float:
        """Calculate minimum distance from point to line segment."""
        # Vector from line_start to line_end
        line_vec = [line_end[i] - line_start[i] for i in range(3)]
        # Vector from line_start to point
        point_vec = [point[i] - line_start[i] for i in range(3)]
        
        # Calculate line length squared
        line_len_sq = sum(v * v for v in line_vec)
        
        if line_len_sq == 0:
            # Line is a point
            return self._calculate_distance(point, line_start)
        
        # Calculate projection parameter
        t = max(0, min(1, sum(point_vec[i] * line_vec[i] for i in range(3)) / line_len_sq))
        
        # Calculate closest point on line
        closest_point = [line_start[i] + t * line_vec[i] for i in range(3)]
        
        # Return distance to closest point
        return self._calculate_distance(point, closest_point)
    
    def _calculate_pathway_clearance(
        self, 
        module_a: ModulePlacement, 
        module_b: ModulePlacement,
        all_modules: List[ModulePlacement]
    ) -> float:
        """Calculate minimum clearance along pathway."""
        min_clearance = float('inf')
        
        for module in all_modules:
            if module.module_id in [module_a.module_id, module_b.module_id]:
                continue
            
            clearance = self._point_to_line_distance(
                module.position, module_a.position, module_b.position
            )
            min_clearance = min(min_clearance, clearance)
        
        return min_clearance if min_clearance != float('inf') else 5.0
    
    def _determine_accessibility_level(self, width: float, clearance: float) -> MobilityLevel:
        """Determine accessibility level based on pathway characteristics."""
        if width >= self.min_corridor_width[MobilityLevel.WHEELCHAIR] and clearance >= 1.0:
            return MobilityLevel.FULL
        elif width >= self.min_corridor_width[MobilityLevel.LIMITED] and clearance >= 0.8:
            return MobilityLevel.LIMITED
        elif width >= self.min_corridor_width[MobilityLevel.WHEELCHAIR]:
            return MobilityLevel.WHEELCHAIR
        else:
            return MobilityLevel.EMERGENCY_ONLY
    
    async def _calculate_mean_transit_time(
        self,
        modules: List[ModulePlacement],
        graph: nx.Graph,
        mission_params: MissionParameters
    ) -> float:
        """
        Calculate weighted mean transit time using shortest path algorithms.
        
        Uses NetworkX shortest path algorithms and weights paths by activity frequency.
        """
        if len(modules) < 2:
            return 0.0
        
        total_weighted_time = 0.0
        total_weight = 0.0
        
        # Calculate activity-weighted transit times
        for activity_type, frequency in self.activity_frequencies.items():
            module_pairs = self._get_activity_module_pairs(modules, activity_type)
            
            for start_module, end_module in module_pairs:
                try:
                    # Use NetworkX shortest path with distance weights
                    path_length = nx.shortest_path_length(
                        graph, start_module, end_module, weight='distance'
                    )
                    
                    # Convert distance to time using normal walking speed
                    transit_time = path_length / self.walking_speeds[MobilityLevel.FULL]
                    
                    # Weight by activity frequency
                    weighted_time = transit_time * frequency
                    total_weighted_time += weighted_time
                    total_weight += frequency
                    
                except nx.NetworkXNoPath:
                    # No path exists - assign penalty time
                    penalty_time = 300.0  # 5 minutes penalty
                    weighted_time = penalty_time * frequency
                    total_weighted_time += weighted_time
                    total_weight += frequency
        
        return total_weighted_time / total_weight if total_weight > 0 else 0.0
    
    def _get_activity_module_pairs(
        self, 
        modules: List[ModulePlacement], 
        activity_type: ActivityType
    ) -> List[Tuple[str, str]]:
        """Get module pairs for specific activity types."""
        pairs = []
        
        if activity_type == ActivityType.SLEEP_TO_WORK:
            sleep_modules = [m for m in modules if m.type == ModuleType.SLEEP_QUARTER]
            work_modules = [m for m in modules if m.type in [ModuleType.LABORATORY, ModuleType.GALLEY]]
            pairs = [(s.module_id, w.module_id) for s in sleep_modules for w in work_modules]
        
        elif activity_type == ActivityType.WORK_TO_GALLEY:
            work_modules = [m for m in modules if m.type == ModuleType.LABORATORY]
            galley_modules = [m for m in modules if m.type == ModuleType.GALLEY]
            pairs = [(w.module_id, g.module_id) for w in work_modules for g in galley_modules]
        
        elif activity_type == ActivityType.GALLEY_TO_EXERCISE:
            galley_modules = [m for m in modules if m.type == ModuleType.GALLEY]
            exercise_modules = [m for m in modules if m.type == ModuleType.EXERCISE]
            pairs = [(g.module_id, e.module_id) for g in galley_modules for e in exercise_modules]
        
        elif activity_type == ActivityType.EXERCISE_TO_MEDICAL:
            exercise_modules = [m for m in modules if m.type == ModuleType.EXERCISE]
            medical_modules = [m for m in modules if m.type == ModuleType.MEDICAL]
            pairs = [(e.module_id, m.module_id) for e in exercise_modules for m in medical_modules]
        
        elif activity_type == ActivityType.ANY_TO_AIRLOCK:
            non_airlock_modules = [m for m in modules if m.type != ModuleType.AIRLOCK]
            airlock_modules = [m for m in modules if m.type == ModuleType.AIRLOCK]
            pairs = [(n.module_id, a.module_id) for n in non_airlock_modules for a in airlock_modules]
        
        return pairs
    
    async def _analyze_emergency_egress(
        self,
        modules: List[ModulePlacement],
        graph: nx.Graph,
        mission_params: MissionParameters
    ) -> EgressAnalysis:
        """
        Analyze emergency egress with bottleneck detection.
        
        Calculates egress times, identifies bottlenecks, and analyzes
        airlock utilization during emergency scenarios.
        """
        airlocks = [m for m in modules if m.type == ModuleType.AIRLOCK]
        
        if not airlocks:
            return EgressAnalysis(
                max_egress_time=999.0,
                avg_egress_time=999.0,
                bottlenecks=[{"type": "critical", "description": "No airlocks available"}],
                critical_paths=[],
                airlock_utilization={}
            )
        
        egress_times = []
        critical_paths = []
        bottlenecks = []
        airlock_usage = defaultdict(int)
        
        # Analyze egress from each non-airlock module
        for module in modules:
            if module.type == ModuleType.AIRLOCK:
                continue
            
            best_egress_time = float('inf')
            best_airlock = None
            best_path = None
            
            # Find shortest egress path to any airlock
            for airlock in airlocks:
                try:
                    path = nx.shortest_path(
                        graph, module.module_id, airlock.module_id, weight='distance'
                    )
                    path_length = nx.shortest_path_length(
                        graph, module.module_id, airlock.module_id, weight='distance'
                    )
                    
                    # Calculate emergency egress time (faster movement)
                    emergency_speed = (
                        self.walking_speeds[MobilityLevel.FULL] * 
                        self.emergency_speed_multiplier
                    )
                    egress_time = path_length / emergency_speed
                    
                    # Check for bottlenecks along path
                    path_bottlenecks = self._analyze_path_bottlenecks(graph, path)
                    
                    # Apply bottleneck penalties
                    for bottleneck in path_bottlenecks:
                        egress_time *= bottleneck['delay_factor']
                    
                    if egress_time < best_egress_time:
                        best_egress_time = egress_time
                        best_airlock = airlock.module_id
                        best_path = path
                
                except nx.NetworkXNoPath:
                    # No path exists - use direct distance with penalty
                    direct_distance = self._calculate_distance(module.position, airlock.position)
                    penalty_time = direct_distance / (self.walking_speeds[MobilityLevel.FULL] * self.emergency_speed_multiplier) * 3
                    if penalty_time < best_egress_time:
                        best_egress_time = penalty_time
                        best_airlock = airlock.module_id
                        best_path = None
            
            if best_egress_time != float('inf'):
                egress_times.append(best_egress_time)
                airlock_usage[best_airlock] += 1
                
                # Track critical paths (>3 minutes)
                if best_egress_time > 180.0:
                    critical_paths.append(TransitPath(
                        start_module=module.module_id,
                        end_module=best_airlock,
                        distance=nx.shortest_path_length(
                            graph, module.module_id, best_airlock, weight='distance'
                        ),
                        travel_time=best_egress_time,
                        bottlenecks=self._analyze_path_bottlenecks(graph, best_path),
                        accessibility_score=self._calculate_path_accessibility(graph, best_path)
                    ))
        
        # Identify system-wide bottlenecks
        bottlenecks.extend(self._identify_egress_bottlenecks(graph, airlock_usage, mission_params))
        
        # Calculate airlock utilization percentages
        total_usage = sum(airlock_usage.values())
        airlock_utilization = {
            airlock_id: (usage / total_usage * 100) if total_usage > 0 else 0
            for airlock_id, usage in airlock_usage.items()
        }
        
        return EgressAnalysis(
            max_egress_time=max(egress_times) if egress_times else 999.0,
            avg_egress_time=sum(egress_times) / len(egress_times) if egress_times else 999.0,
            bottlenecks=bottlenecks,
            critical_paths=critical_paths,
            airlock_utilization=airlock_utilization
        )
    
    def _analyze_path_bottlenecks(self, graph: nx.Graph, path: List[str]) -> List[Dict[str, Any]]:
        """Analyze bottlenecks along a specific path."""
        bottlenecks = []
        
        for i in range(len(path) - 1):
            edge_data = graph.get_edge_data(path[i], path[i + 1])
            if edge_data and edge_data.get('bottleneck_factor', 1.0) > 1.2:
                bottlenecks.append({
                    'location': f"{path[i]} -> {path[i + 1]}",
                    'type': 'width_restriction',
                    'severity': edge_data['bottleneck_factor'],
                    'delay_factor': edge_data['bottleneck_factor']
                })
        
        return bottlenecks
    
    def _calculate_path_accessibility(self, graph: nx.Graph, path: List[str]) -> float:
        """Calculate accessibility score for a path."""
        if not path or len(path) < 2:
            return 1.0
        
        accessibility_scores = []
        
        for i in range(len(path) - 1):
            edge_data = graph.get_edge_data(path[i], path[i + 1])
            if edge_data:
                # Convert accessibility level to score
                level = edge_data.get('accessibility_level', MobilityLevel.FULL)
                if level == MobilityLevel.FULL:
                    score = 1.0
                elif level == MobilityLevel.LIMITED:
                    score = 0.8
                elif level == MobilityLevel.WHEELCHAIR:
                    score = 0.6
                else:  # EMERGENCY_ONLY
                    score = 0.3
                accessibility_scores.append(score)
        
        return sum(accessibility_scores) / len(accessibility_scores) if accessibility_scores else 1.0
    
    def _identify_egress_bottlenecks(
        self, 
        graph: nx.Graph, 
        airlock_usage: Dict[str, int],
        mission_params: MissionParameters
    ) -> List[Dict[str, Any]]:
        """Identify system-wide egress bottlenecks."""
        bottlenecks = []
        
        # Check airlock capacity vs crew size
        total_airlocks = len([n for n in graph.nodes() 
                            if graph.nodes[n].get('module_type') == ModuleType.AIRLOCK])
        
        if total_airlocks == 0:
            bottlenecks.append({
                'type': 'critical',
                'description': 'No airlocks available for emergency egress',
                'severity': 'critical',
                'delay_factor': 10.0
            })
        elif total_airlocks < mission_params.crew_size / 4:  # Target: 1 airlock per 4 crew
            bottlenecks.append({
                'type': 'capacity',
                'description': f'Insufficient airlocks for crew size ({total_airlocks} for {mission_params.crew_size} crew)',
                'severity': 'high',
                'delay_factor': 2.0
            })
        
        # Check for overutilized airlocks
        max_usage = max(airlock_usage.values()) if airlock_usage else 0
        total_modules = len([n for n in graph.nodes() 
                           if graph.nodes[n].get('module_type') != ModuleType.AIRLOCK])
        
        if max_usage > total_modules * 0.6:  # More than 60% of modules use same airlock
            bottlenecks.append({
                'type': 'distribution',
                'description': 'Uneven airlock utilization - some airlocks overloaded',
                'severity': 'medium',
                'delay_factor': 1.5
            })
        
        return bottlenecks
    
    async def _analyze_accessibility(
        self,
        modules: List[ModulePlacement],
        graph: nx.Graph,
        envelope: EnvelopeSpec
    ) -> Dict[MobilityLevel, AccessibilityAnalysis]:
        """Analyze accessibility for different mobility constraint levels."""
        analyses = {}
        
        for mobility_level in MobilityLevel:
            accessible_modules = set()
            inaccessible_modules = set()
            required_modifications = []
            
            # Check accessibility of each module
            for module in modules:
                is_accessible = self._check_module_accessibility(
                    module, graph, mobility_level
                )
                
                if is_accessible:
                    accessible_modules.add(module.module_id)
                else:
                    inaccessible_modules.add(module.module_id)
                    # Suggest modifications
                    modifications = self._suggest_accessibility_modifications(
                        module, graph, mobility_level
                    )
                    required_modifications.extend(modifications)
            
            # Calculate accessibility score
            total_modules = len(modules)
            accessibility_score = (
                len(accessible_modules) / total_modules if total_modules > 0 else 0.0
            )
            
            analyses[mobility_level] = AccessibilityAnalysis(
                mobility_level=mobility_level,
                accessible_modules=accessible_modules,
                inaccessible_modules=inaccessible_modules,
                accessibility_score=accessibility_score,
                required_modifications=required_modifications
            )
        
        return analyses
    
    def _check_module_accessibility(
        self, 
        module: ModulePlacement, 
        graph: nx.Graph, 
        mobility_level: MobilityLevel
    ) -> bool:
        """Check if a module is accessible for given mobility level."""
        # Check if module has any accessible paths
        for neighbor in graph.neighbors(module.module_id):
            edge_data = graph.get_edge_data(module.module_id, neighbor)
            if edge_data:
                path_accessibility = edge_data.get('accessibility_level', MobilityLevel.FULL)
                
                # Check if path meets mobility requirements
                if self._mobility_level_compatible(path_accessibility, mobility_level):
                    return True
        
        return False
    
    def _mobility_level_compatible(
        self, 
        path_level: MobilityLevel, 
        required_level: MobilityLevel
    ) -> bool:
        """Check if path accessibility level meets required mobility level."""
        level_hierarchy = {
            MobilityLevel.FULL: 4,
            MobilityLevel.LIMITED: 3,
            MobilityLevel.WHEELCHAIR: 2,
            MobilityLevel.EMERGENCY_ONLY: 1
        }
        
        return level_hierarchy[path_level] >= level_hierarchy[required_level]
    
    def _suggest_accessibility_modifications(
        self, 
        module: ModulePlacement, 
        graph: nx.Graph, 
        mobility_level: MobilityLevel
    ) -> List[str]:
        """Suggest modifications to improve module accessibility."""
        modifications = []
        
        min_width = self.min_corridor_width[mobility_level]
        
        for neighbor in graph.neighbors(module.module_id):
            edge_data = graph.get_edge_data(module.module_id, neighbor)
            if edge_data:
                current_width = edge_data.get('width', 0.8)
                
                if current_width < min_width:
                    width_increase = min_width - current_width
                    modifications.append(
                        f"Widen pathway from {module.module_id} to {neighbor} "
                        f"by {width_increase:.1f}m (current: {current_width:.1f}m, "
                        f"required: {min_width:.1f}m)"
                    )
        
        return modifications
    
    async def _analyze_stowage_utilization(
        self,
        modules: List[ModulePlacement],
        mission_params: MissionParameters
    ) -> StowageAnalysis:
        """Calculate stowage utilization based on crew requirements."""
        # Calculate total available stowage
        total_available = 0.0
        per_module_available = {}
        
        for module in modules:
            module_def = self._get_module_definition(module.module_id)
            if module_def:
                stowage = module_def.spec.stowage_m3
                total_available += stowage
                per_module_available[module.module_id] = stowage
        
        # Calculate required stowage based on mission parameters
        crew_size = mission_params.crew_size
        duration_days = mission_params.duration_days
        
        total_required = 0.0
        for category, daily_req in self.stowage_requirements.items():
            category_total = crew_size * duration_days * daily_req
            total_required += category_total
        
        # Calculate utilization ratio
        utilization_ratio = total_required / total_available if total_available > 0 else 2.0
        
        # Analyze per-module utilization (simplified distribution)
        per_module_utilization = {}
        overcrowded_modules = []
        underutilized_modules = []
        
        # Distribute required stowage proportionally to available capacity
        for module_id, available in per_module_available.items():
            if total_available > 0:
                allocated = total_required * (available / total_available)
                module_utilization = allocated / available if available > 0 else 0.0
                per_module_utilization[module_id] = module_utilization
                
                if module_utilization > 1.0:
                    overcrowded_modules.append(module_id)
                elif module_utilization < 0.3:
                    underutilized_modules.append(module_id)
        
        # Generate recommendations
        recommendations = self._generate_stowage_recommendations(
            utilization_ratio, overcrowded_modules, underutilized_modules, mission_params
        )
        
        return StowageAnalysis(
            total_available_m3=total_available,
            total_required_m3=total_required,
            utilization_ratio=utilization_ratio,
            per_module_utilization=per_module_utilization,
            overcrowded_modules=overcrowded_modules,
            underutilized_modules=underutilized_modules,
            recommendations=recommendations
        )
    
    def _generate_stowage_recommendations(
        self,
        utilization_ratio: float,
        overcrowded_modules: List[str],
        underutilized_modules: List[str],
        mission_params: MissionParameters
    ) -> List[str]:
        """Generate stowage optimization recommendations."""
        recommendations = []
        
        if utilization_ratio > 1.2:
            recommendations.append(
                f"Overall stowage overcrowded ({utilization_ratio:.1f}x capacity). "
                "Consider adding storage modules or reducing mission duration."
            )
        elif utilization_ratio > 1.0:
            recommendations.append(
                f"Stowage at capacity ({utilization_ratio:.1f}x). "
                "Monitor consumption rates and consider contingency storage."
            )
        
        if overcrowded_modules:
            recommendations.append(
                f"Redistribute stowage from overcrowded modules: {', '.join(overcrowded_modules[:3])}"
            )
        
        if underutilized_modules and overcrowded_modules:
            recommendations.append(
                f"Move items from overcrowded to underutilized modules: {', '.join(underutilized_modules[:3])}"
            )
        
        if utilization_ratio < 0.6:
            recommendations.append(
                "Stowage underutilized. Consider reducing storage modules or extending mission duration."
            )
        
        return recommendations
    
    async def _calculate_activity_transit_times(
        self,
        modules: List[ModulePlacement],
        graph: nx.Graph
    ) -> Dict[ActivityType, float]:
        """Calculate transit times for specific activity types."""
        activity_times = {}
        
        for activity_type in ActivityType:
            if activity_type == ActivityType.EMERGENCY_EGRESS:
                continue  # Handled separately in egress analysis
            
            module_pairs = self._get_activity_module_pairs(modules, activity_type)
            
            if not module_pairs:
                activity_times[activity_type] = 0.0
                continue
            
            total_time = 0.0
            valid_pairs = 0
            
            for start_module, end_module in module_pairs:
                try:
                    path_length = nx.shortest_path_length(
                        graph, start_module, end_module, weight='distance'
                    )
                    transit_time = path_length / self.walking_speeds[MobilityLevel.FULL]
                    total_time += transit_time
                    valid_pairs += 1
                except nx.NetworkXNoPath:
                    # Skip disconnected pairs
                    continue
            
            activity_times[activity_type] = (
                total_time / valid_pairs if valid_pairs > 0 else 0.0
            )
        
        return activity_times
    
    async def _identify_congestion_hotspots(
        self,
        modules: List[ModulePlacement],
        graph: nx.Graph,
        mission_params: MissionParameters
    ) -> List[Dict[str, Any]]:
        """Identify potential congestion hotspots based on traffic patterns."""
        hotspots = []
        
        # Calculate betweenness centrality to identify high-traffic pathways
        try:
            centrality = nx.betweenness_centrality(graph, weight='distance')
            
            # Identify nodes with high centrality (potential bottlenecks)
            high_centrality_threshold = 0.1
            for node_id, centrality_score in centrality.items():
                if centrality_score > high_centrality_threshold:
                    # Check if this node has narrow pathways
                    narrow_pathways = []
                    for neighbor in graph.neighbors(node_id):
                        edge_data = graph.get_edge_data(node_id, neighbor)
                        if edge_data and edge_data.get('width', 1.2) < 1.0:
                            narrow_pathways.append(neighbor)
                    
                    if narrow_pathways:
                        hotspots.append({
                            'location': node_id,
                            'type': 'high_traffic_narrow_pathway',
                            'centrality_score': centrality_score,
                            'narrow_connections': narrow_pathways,
                            'severity': 'high' if centrality_score > 0.2 else 'medium',
                            'recommendation': f"Widen pathways from {node_id} to reduce congestion"
                        })
        
        except nx.NetworkXError:
            # Graph might be disconnected
            pass
        
        # Check for modules with many connections (potential gathering points)
        for module in modules:
            connection_count = len(list(graph.neighbors(module.module_id)))
            if connection_count > 4:  # More than 4 connections
                hotspots.append({
                    'location': module.module_id,
                    'type': 'high_connectivity_hub',
                    'connection_count': connection_count,
                    'severity': 'medium',
                    'recommendation': f"Monitor traffic flow at {module.module_id} hub"
                })
        
        return hotspots
    
    def _calculate_overall_human_factors_score(
        self,
        mean_transit_time: float,
        egress_analysis: EgressAnalysis,
        accessibility_analyses: Dict[MobilityLevel, AccessibilityAnalysis],
        stowage_analysis: StowageAnalysis,
        mission_params: MissionParameters
    ) -> float:
        """Calculate overall human factors performance score."""
        
        # Transit time score (target: < 60 seconds)
        transit_score = max(0, 1 - (mean_transit_time / 60.0))
        
        # Egress score (target: < 180 seconds)
        egress_score = max(0, 1 - (egress_analysis.max_egress_time / 180.0))
        
        # Accessibility score (average across mobility levels, weighted)
        accessibility_weights = {
            MobilityLevel.FULL: 0.4,
            MobilityLevel.LIMITED: 0.3,
            MobilityLevel.WHEELCHAIR: 0.2,
            MobilityLevel.EMERGENCY_ONLY: 0.1
        }
        
        weighted_accessibility = sum(
            accessibility_analyses[level].accessibility_score * weight
            for level, weight in accessibility_weights.items()
        )
        
        # Stowage score (target: 0.7-0.9 utilization)
        optimal_utilization = 0.8
        stowage_score = max(0, 1 - abs(stowage_analysis.utilization_ratio - optimal_utilization))
        
        # Combine scores with weights
        overall_score = (
            transit_score * 0.25 +
            egress_score * 0.35 +
            weighted_accessibility * 0.25 +
            stowage_score * 0.15
        )
        
        return max(0.0, min(1.0, overall_score))
    
    def _calculate_distance(self, pos1: List[float], pos2: List[float]) -> float:
        """Calculate Euclidean distance between two positions."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(pos1, pos2)))
    
    def _get_module_definition(self, module_id: str) -> Optional[ModuleDefinition]:
        """Get module definition by ID, handling both library and instance IDs."""
        # First try direct lookup
        module_def = self.module_library.get_module(module_id)
        if module_def:
            return module_def
        
        # If not found, try to extract base type from instance ID
        if '_' in module_id:
            parts = module_id.split('_')
            if len(parts) >= 3:
                module_type = '_'.join(parts[:-2])
                std_module_id = f"std_{module_type}"
                module_def = self.module_library.get_module(std_module_id)
                if module_def:
                    return module_def
        
        return None