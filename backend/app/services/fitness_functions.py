"""
Fitness Functions for Multi-Objective Habitat Layout Optimization

This module defines fitness functions for evaluating habitat layouts
across multiple objectives including transit time, mass, power, safety,
thermal performance, and life support systems.
"""

import numpy as np
import math
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import networkx as nx

from app.models.base import (
    EnvelopeSpec, MissionParameters, LayoutSpec, ModulePlacement, 
    PerformanceMetrics, ModuleType
)
from app.models.module_library import get_module_library, ModuleDefinition

logger = logging.getLogger(__name__)


@dataclass
class FitnessWeights:
    """Weights for combining multiple fitness components"""
    transit_time: float = 0.25
    mass: float = 0.20
    power: float = 0.15
    safety: float = 0.30
    thermal: float = 0.05
    lss_margin: float = 0.05


class TransitTimeFitness:
    """
    Fitness function for minimizing crew transit times between modules.
    
    Calculates mean transit time based on crew activity patterns and
    module connectivity graph.
    """
    
    def __init__(self):
        self.module_library = get_module_library()
    
    def calculate_fitness(
        self,
        placements: List[ModulePlacement],
        mission_params: MissionParameters,
        envelope: EnvelopeSpec
    ) -> float:
        """
        Calculate transit time fitness (lower is better).
        
        Returns normalized fitness value between 0 and 1.
        """
        try:
            # Build connectivity graph
            graph = self._build_connectivity_graph(placements)
            
            # Calculate activity-weighted transit times
            total_weighted_time = 0.0
            total_weight = 0.0
            
            activity_weights = self._get_activity_transition_weights(mission_params)
            
            for (from_type, to_type), weight in activity_weights.items():
                # Find modules of each type
                from_modules = [p for p in placements if p.type == from_type]
                to_modules = [p for p in placements if p.type == to_type]
                
                if not from_modules or not to_modules:
                    continue
                
                # Calculate minimum transit time between module types
                min_time = float('inf')
                for from_module in from_modules:
                    for to_module in to_modules:
                        if from_module.module_id == to_module.module_id:
                            continue
                        
                        try:
                            path_length = nx.shortest_path_length(
                                graph, from_module.module_id, to_module.module_id
                            )
                            # Estimate time based on path length and walking speed
                            transit_time = self._calculate_transit_time(
                                from_module, to_module, path_length
                            )
                            min_time = min(min_time, transit_time)
                        except nx.NetworkXNoPath:
                            # No path exists, heavy penalty
                            min_time = 300.0  # 5 minutes penalty
                            break
                
                if min_time != float('inf'):
                    total_weighted_time += min_time * weight
                    total_weight += weight
            
            # Calculate mean weighted transit time
            if total_weight > 0:
                mean_transit_time = total_weighted_time / total_weight
            else:
                mean_transit_time = 300.0  # Default penalty
            
            # Normalize to 0-1 scale (0 = best, 1 = worst)
            # Assume 300 seconds (5 minutes) as maximum acceptable time
            normalized_fitness = min(1.0, mean_transit_time / 300.0)
            
            return normalized_fitness
        
        except Exception as e:
            logger.warning(f"Error calculating transit time fitness: {str(e)}")
            return 1.0  # Maximum penalty for errors
    
    def _build_connectivity_graph(self, placements: List[ModulePlacement]) -> nx.Graph:
        """Build connectivity graph between modules"""
        graph = nx.Graph()
        
        # Add nodes
        for placement in placements:
            graph.add_node(placement.module_id, placement=placement)
        
        # Add edges based on proximity and connectivity rules
        for i, placement1 in enumerate(placements):
            for j, placement2 in enumerate(placements[i+1:], i+1):
                if self._can_connect(placement1, placement2):
                    distance = self._calculate_distance(placement1, placement2)
                    graph.add_edge(placement1.module_id, placement2.module_id, weight=distance)
        
        return graph
    
    def _can_connect(self, placement1: ModulePlacement, placement2: ModulePlacement) -> bool:
        """Check if two modules can be connected"""
        # Simple proximity-based connectivity
        distance = self._calculate_distance(placement1, placement2)
        
        # Modules can connect if they're within 5 meters of each other
        max_connection_distance = 5.0
        return distance <= max_connection_distance
    
    def _calculate_distance(self, placement1: ModulePlacement, placement2: ModulePlacement) -> float:
        """Calculate Euclidean distance between two module placements"""
        pos1 = np.array(placement1.position)
        pos2 = np.array(placement2.position)
        return float(np.linalg.norm(pos1 - pos2))
    
    def _calculate_transit_time(
        self, 
        from_module: ModulePlacement, 
        to_module: ModulePlacement, 
        path_length: int
    ) -> float:
        """Calculate transit time between modules"""
        # Base time on direct distance and path complexity
        direct_distance = self._calculate_distance(from_module, to_module)
        
        # Walking speed: ~1.5 m/s in habitat
        walking_speed = 1.5
        
        # Path complexity factor (longer paths take proportionally more time)
        complexity_factor = 1.0 + (path_length - 1) * 0.2
        
        transit_time = (direct_distance / walking_speed) * complexity_factor
        
        return transit_time
    
    def _get_activity_transition_weights(self, mission_params: MissionParameters) -> Dict[Tuple[ModuleType, ModuleType], float]:
        """Get weights for transitions between different activity types"""
        # Based on typical crew activity patterns
        transitions = {
            # Sleep to other activities
            (ModuleType.SLEEP_QUARTER, ModuleType.GALLEY): 2.0,  # Morning routine
            (ModuleType.SLEEP_QUARTER, ModuleType.MEDICAL): 0.5,
            (ModuleType.SLEEP_QUARTER, ModuleType.LABORATORY): 1.5,
            
            # Work activities
            (ModuleType.LABORATORY, ModuleType.GALLEY): 3.0,  # Meal breaks
            (ModuleType.LABORATORY, ModuleType.EXERCISE): 1.0,
            (ModuleType.LABORATORY, ModuleType.STORAGE): 2.0,
            
            # Galley connections
            (ModuleType.GALLEY, ModuleType.SLEEP_QUARTER): 1.5,
            (ModuleType.GALLEY, ModuleType.LABORATORY): 2.0,
            
            # Exercise connections
            (ModuleType.EXERCISE, ModuleType.GALLEY): 1.0,
            (ModuleType.EXERCISE, ModuleType.MEDICAL): 0.5,
            
            # Emergency connections
            (ModuleType.SLEEP_QUARTER, ModuleType.AIRLOCK): 0.1,  # Emergency egress
            (ModuleType.LABORATORY, ModuleType.AIRLOCK): 0.1,
            (ModuleType.GALLEY, ModuleType.AIRLOCK): 0.1,
        }
        
        # Normalize weights based on mission duration and crew size
        duration_factor = min(1.0, mission_params.duration_days / 180.0)  # Normalize to 6 months
        crew_factor = mission_params.crew_size / 4.0  # Normalize to 4-person crew
        
        normalized_transitions = {}
        for (from_type, to_type), weight in transitions.items():
            normalized_weight = weight * duration_factor * crew_factor
            normalized_transitions[(from_type, to_type)] = normalized_weight
            # Add reverse direction with same weight
            normalized_transitions[(to_type, from_type)] = normalized_weight
        
        return normalized_transitions


class MassFitness:
    """
    Fitness function for minimizing total habitat mass.
    
    Considers module masses, structural requirements, and mass penalties
    for suboptimal configurations.
    """
    
    def __init__(self):
        self.module_library = get_module_library()
    
    def calculate_fitness(
        self,
        placements: List[ModulePlacement],
        mission_params: MissionParameters,
        envelope: EnvelopeSpec
    ) -> float:
        """
        Calculate mass fitness (lower is better).
        
        Returns normalized fitness value between 0 and 1.
        """
        try:
            total_mass = 0.0
            
            # Calculate module masses
            for placement in placements:
                module_def = self._get_module_definition(placement.type)
                if module_def:
                    total_mass += module_def.spec.mass_kg
            
            # Add structural mass penalties
            structural_penalty = self._calculate_structural_penalty(placements, envelope)
            total_mass += structural_penalty
            
            # Add configuration penalties
            config_penalty = self._calculate_configuration_penalty(placements)
            total_mass += config_penalty
            
            # Normalize to 0-1 scale
            # Assume 50,000 kg as maximum acceptable mass for a habitat
            max_acceptable_mass = 50000.0
            normalized_fitness = min(1.0, total_mass / max_acceptable_mass)
            
            return normalized_fitness
        
        except Exception as e:
            logger.warning(f"Error calculating mass fitness: {str(e)}")
            return 1.0
    
    def _get_module_definition(self, module_type: ModuleType) -> Optional[ModuleDefinition]:
        """Get module definition from library"""
        modules = self.module_library.get_modules_by_type(module_type)
        return modules[0] if modules else None
    
    def _calculate_structural_penalty(
        self, 
        placements: List[ModulePlacement], 
        envelope: EnvelopeSpec
    ) -> float:
        """Calculate structural mass penalty based on layout configuration"""
        # Penalty for modules far from center (require more structure)
        center_penalty = 0.0
        
        for placement in placements:
            distance_from_center = np.linalg.norm(placement.position)
            # Penalty increases quadratically with distance
            center_penalty += (distance_from_center ** 2) * 10.0  # kg per m²
        
        # Penalty for unbalanced layouts
        balance_penalty = self._calculate_balance_penalty(placements)
        
        return center_penalty + balance_penalty
    
    def _calculate_balance_penalty(self, placements: List[ModulePlacement]) -> float:
        """Calculate penalty for unbalanced mass distribution"""
        if len(placements) < 2:
            return 0.0
        
        # Calculate center of mass
        total_mass = 0.0
        weighted_position = np.zeros(3)
        
        for placement in placements:
            module_def = self._get_module_definition(placement.type)
            if module_def:
                mass = module_def.spec.mass_kg
                total_mass += mass
                weighted_position += np.array(placement.position) * mass
        
        if total_mass > 0:
            center_of_mass = weighted_position / total_mass
            # Penalty for center of mass far from origin
            com_distance = np.linalg.norm(center_of_mass)
            return com_distance * 100.0  # kg per meter offset
        
        return 0.0
    
    def _calculate_configuration_penalty(self, placements: List[ModulePlacement]) -> float:
        """Calculate penalty for suboptimal module configurations"""
        penalty = 0.0
        
        # Penalty for isolated modules (require additional connections)
        connectivity_penalty = self._calculate_connectivity_penalty(placements)
        penalty += connectivity_penalty
        
        # Penalty for modules in difficult-to-access locations
        accessibility_penalty = self._calculate_accessibility_penalty(placements)
        penalty += accessibility_penalty
        
        return penalty
    
    def _calculate_connectivity_penalty(self, placements: List[ModulePlacement]) -> float:
        """Calculate penalty for poor connectivity"""
        penalty = 0.0
        
        for placement in placements:
            # Count nearby modules
            nearby_count = 0
            for other in placements:
                if other.module_id != placement.module_id:
                    distance = np.linalg.norm(
                        np.array(placement.position) - np.array(other.position)
                    )
                    if distance <= 5.0:  # Within connection range
                        nearby_count += 1
            
            # Penalty for isolated modules
            if nearby_count == 0:
                penalty += 500.0  # kg penalty for isolation
            elif nearby_count == 1:
                penalty += 100.0  # kg penalty for single connection
        
        return penalty
    
    def _calculate_accessibility_penalty(self, placements: List[ModulePlacement]) -> float:
        """Calculate penalty for modules in hard-to-access locations"""
        penalty = 0.0
        
        # Find airlocks
        airlocks = [p for p in placements if p.type == ModuleType.AIRLOCK]
        
        if not airlocks:
            return 1000.0  # Heavy penalty for no airlocks
        
        # Penalty for modules far from airlocks
        for placement in placements:
            if placement.type == ModuleType.AIRLOCK:
                continue
            
            min_distance_to_airlock = float('inf')
            for airlock in airlocks:
                distance = np.linalg.norm(
                    np.array(placement.position) - np.array(airlock.position)
                )
                min_distance_to_airlock = min(min_distance_to_airlock, distance)
            
            # Penalty increases with distance from nearest airlock
            if min_distance_to_airlock > 10.0:  # More than 10m from airlock
                penalty += (min_distance_to_airlock - 10.0) * 50.0  # kg per meter
        
        return penalty


class PowerFitness:
    """
    Fitness function for minimizing power consumption and optimizing
    power distribution efficiency.
    """
    
    def __init__(self):
        self.module_library = get_module_library()
    
    def calculate_fitness(
        self,
        placements: List[ModulePlacement],
        mission_params: MissionParameters,
        envelope: EnvelopeSpec
    ) -> float:
        """
        Calculate power fitness (lower is better).
        
        Returns normalized fitness value between 0 and 1.
        """
        try:
            total_power = 0.0
            
            # Calculate base power consumption
            for placement in placements:
                module_def = self._get_module_definition(placement.type)
                if module_def:
                    total_power += module_def.spec.power_w
            
            # Add power distribution penalties
            distribution_penalty = self._calculate_distribution_penalty(placements)
            total_power += distribution_penalty
            
            # Add thermal coupling penalties
            thermal_penalty = self._calculate_thermal_coupling_penalty(placements)
            total_power += thermal_penalty
            
            # Normalize to 0-1 scale
            # Assume 10,000 W as maximum acceptable power
            max_acceptable_power = 10000.0
            normalized_fitness = min(1.0, total_power / max_acceptable_power)
            
            return normalized_fitness
        
        except Exception as e:
            logger.warning(f"Error calculating power fitness: {str(e)}")
            return 1.0
    
    def _get_module_definition(self, module_type: ModuleType) -> Optional[ModuleDefinition]:
        """Get module definition from library"""
        modules = self.module_library.get_modules_by_type(module_type)
        return modules[0] if modules else None
    
    def _calculate_distribution_penalty(self, placements: List[ModulePlacement]) -> float:
        """Calculate penalty for inefficient power distribution"""
        penalty = 0.0
        
        # Find power generation modules (mechanical/ECLSS)
        power_sources = [p for p in placements if p.type == ModuleType.MECHANICAL]
        
        if not power_sources:
            return 5000.0  # Heavy penalty for no power sources
        
        # Calculate power distribution distances
        for placement in placements:
            if placement.type == ModuleType.MECHANICAL:
                continue
            
            # Find nearest power source
            min_distance = float('inf')
            for source in power_sources:
                distance = np.linalg.norm(
                    np.array(placement.position) - np.array(source.position)
                )
                min_distance = min(min_distance, distance)
            
            # Power loss penalty based on distance
            # Assume 1% power loss per meter of cable
            power_loss_penalty = min_distance * 10.0  # W per meter
            penalty += power_loss_penalty
        
        return penalty
    
    def _calculate_thermal_coupling_penalty(self, placements: List[ModulePlacement]) -> float:
        """Calculate penalty for poor thermal management"""
        penalty = 0.0
        
        # High-power modules should be distributed to avoid hot spots
        high_power_modules = []
        for placement in placements:
            module_def = self._get_module_definition(placement.type)
            if module_def and module_def.spec.power_w > 500:  # High power threshold
                high_power_modules.append(placement)
        
        # Penalty for clustering high-power modules
        for i, module1 in enumerate(high_power_modules):
            for module2 in high_power_modules[i+1:]:
                distance = np.linalg.norm(
                    np.array(module1.position) - np.array(module2.position)
                )
                if distance < 3.0:  # Too close for thermal management
                    penalty += (3.0 - distance) * 200.0  # W penalty
        
        return penalty


class SafetyFitness:
    """
    Fitness function for maximizing habitat safety through optimal
    module placement, egress paths, and emergency response capability.
    """
    
    def __init__(self):
        self.module_library = get_module_library()
    
    def calculate_fitness(
        self,
        placements: List[ModulePlacement],
        mission_params: MissionParameters,
        envelope: EnvelopeSpec
    ) -> float:
        """
        Calculate safety fitness (lower is better for minimization).
        
        Returns normalized fitness value between 0 and 1.
        """
        try:
            safety_score = 1.0  # Start with perfect safety
            
            # Evaluate egress path quality
            egress_penalty = self._calculate_egress_penalty(placements)
            safety_score -= egress_penalty
            
            # Evaluate emergency response capability
            emergency_penalty = self._calculate_emergency_response_penalty(placements)
            safety_score -= emergency_penalty
            
            # Evaluate hazard separation
            hazard_penalty = self._calculate_hazard_separation_penalty(placements)
            safety_score -= hazard_penalty
            
            # Evaluate redundancy
            redundancy_penalty = self._calculate_redundancy_penalty(placements)
            safety_score -= redundancy_penalty
            
            # Convert to minimization objective (lower is better)
            safety_fitness = max(0.0, 1.0 - safety_score)
            
            return safety_fitness
        
        except Exception as e:
            logger.warning(f"Error calculating safety fitness: {str(e)}")
            return 1.0
    
    def _calculate_egress_penalty(self, placements: List[ModulePlacement]) -> float:
        """Calculate penalty for poor emergency egress paths"""
        penalty = 0.0
        
        # Find airlocks
        airlocks = [p for p in placements if p.type == ModuleType.AIRLOCK]
        
        if len(airlocks) == 0:
            return 0.8  # Major penalty for no airlocks
        elif len(airlocks) == 1:
            penalty += 0.2  # Moderate penalty for single airlock
        
        # Calculate egress times from each module
        for placement in placements:
            if placement.type == ModuleType.AIRLOCK:
                continue
            
            # Find shortest path to any airlock
            min_egress_time = float('inf')
            for airlock in airlocks:
                # Simple distance-based egress time estimate
                distance = np.linalg.norm(
                    np.array(placement.position) - np.array(airlock.position)
                )
                # Assume 1 m/s emergency movement speed
                egress_time = distance / 1.0
                min_egress_time = min(min_egress_time, egress_time)
            
            # Penalty for long egress times
            if min_egress_time > 300:  # More than 5 minutes
                penalty += 0.3
            elif min_egress_time > 180:  # More than 3 minutes
                penalty += 0.1
        
        return min(penalty, 0.8)
    
    def _calculate_emergency_response_penalty(self, placements: List[ModulePlacement]) -> float:
        """Calculate penalty for poor emergency response capability"""
        penalty = 0.0
        
        # Check for medical module accessibility
        medical_modules = [p for p in placements if p.type == ModuleType.MEDICAL]
        
        if not medical_modules:
            penalty += 0.3  # Penalty for no medical capability
        else:
            # Medical should be centrally located
            medical_module = medical_modules[0]
            
            # Calculate average distance to all other modules
            total_distance = 0.0
            for placement in placements:
                if placement.module_id != medical_module.module_id:
                    distance = np.linalg.norm(
                        np.array(placement.position) - np.array(medical_module.position)
                    )
                    total_distance += distance
            
            avg_distance = total_distance / max(1, len(placements) - 1)
            
            # Penalty for medical module too far from other modules
            if avg_distance > 8.0:
                penalty += 0.2
        
        return penalty
    
    def _calculate_hazard_separation_penalty(self, placements: List[ModulePlacement]) -> float:
        """Calculate penalty for inadequate hazard separation"""
        penalty = 0.0
        
        # Mechanical modules (potential fire/explosion hazard) should be separated
        mechanical_modules = [p for p in placements if p.type == ModuleType.MECHANICAL]
        sleep_modules = [p for p in placements if p.type == ModuleType.SLEEP_QUARTER]
        
        # Check separation between hazardous and crew modules
        for mechanical in mechanical_modules:
            for sleep in sleep_modules:
                distance = np.linalg.norm(
                    np.array(mechanical.position) - np.array(sleep.position)
                )
                if distance < 3.0:  # Too close
                    penalty += 0.1
        
        # Laboratory modules should be separated from galley (contamination risk)
        lab_modules = [p for p in placements if p.type == ModuleType.LABORATORY]
        galley_modules = [p for p in placements if p.type == ModuleType.GALLEY]
        
        for lab in lab_modules:
            for galley in galley_modules:
                distance = np.linalg.norm(
                    np.array(lab.position) - np.array(galley.position)
                )
                if distance < 2.0:  # Too close
                    penalty += 0.05
        
        return min(penalty, 0.3)
    
    def _calculate_redundancy_penalty(self, placements: List[ModulePlacement]) -> float:
        """Calculate penalty for lack of critical system redundancy"""
        penalty = 0.0
        
        # Count critical systems
        module_counts = {}
        for placement in placements:
            module_type = placement.type
            module_counts[module_type] = module_counts.get(module_type, 0) + 1
        
        # Check for adequate redundancy
        critical_systems = {
            ModuleType.AIRLOCK: 2,  # Should have at least 2 airlocks
            ModuleType.MECHANICAL: 1,  # At least 1 ECLSS
        }
        
        for system_type, min_count in critical_systems.items():
            actual_count = module_counts.get(system_type, 0)
            if actual_count < min_count:
                penalty += 0.2 * (min_count - actual_count)
        
        return min(penalty, 0.4)


class CompositeFitnessFunction:
    """
    Composite fitness function that combines multiple objectives
    with configurable weights.
    """
    
    def __init__(self, weights: FitnessWeights = None):
        self.weights = weights or FitnessWeights()
        
        # Initialize individual fitness functions
        self.transit_fitness = TransitTimeFitness()
        self.mass_fitness = MassFitness()
        self.power_fitness = PowerFitness()
        self.safety_fitness = SafetyFitness()
    
    def calculate_fitness(
        self,
        placements: List[ModulePlacement],
        mission_params: MissionParameters,
        envelope: EnvelopeSpec
    ) -> Dict[str, float]:
        """
        Calculate composite fitness across all objectives.
        
        Returns dictionary with individual and composite fitness values.
        """
        try:
            # Calculate individual fitness components
            transit_fit = self.transit_fitness.calculate_fitness(
                placements, mission_params, envelope
            )
            mass_fit = self.mass_fitness.calculate_fitness(
                placements, mission_params, envelope
            )
            power_fit = self.power_fitness.calculate_fitness(
                placements, mission_params, envelope
            )
            safety_fit = self.safety_fitness.calculate_fitness(
                placements, mission_params, envelope
            )
            
            # Calculate weighted composite fitness
            composite_fitness = (
                self.weights.transit_time * transit_fit +
                self.weights.mass * mass_fit +
                self.weights.power * power_fit +
                self.weights.safety * safety_fit
            )
            
            return {
                'transit_time': transit_fit,
                'mass': mass_fit,
                'power': power_fit,
                'safety': safety_fit,
                'composite': composite_fitness
            }
        
        except Exception as e:
            logger.error(f"Error calculating composite fitness: {str(e)}")
            return {
                'transit_time': 1.0,
                'mass': 1.0,
                'power': 1.0,
                'safety': 1.0,
                'composite': 1.0
            }
    
    def update_weights(self, mission_params: MissionParameters):
        """Update fitness weights based on mission priorities"""
        priority_weights = mission_params.priority_weights
        
        # Map mission priorities to fitness weights
        self.weights.safety = priority_weights.get('safety', 0.3)
        self.weights.transit_time = priority_weights.get('efficiency', 0.25) * 0.6
        self.weights.mass = priority_weights.get('mass', 0.2)
        self.weights.power = priority_weights.get('power', 0.15)
        
        # Normalize weights to sum to 1.0
        total_weight = (
            self.weights.transit_time + self.weights.mass + 
            self.weights.power + self.weights.safety
        )
        
        if total_weight > 0:
            self.weights.transit_time /= total_weight
            self.weights.mass /= total_weight
            self.weights.power /= total_weight
            self.weights.safety /= total_weight