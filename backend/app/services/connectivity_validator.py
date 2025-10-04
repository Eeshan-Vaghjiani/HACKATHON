"""
Advanced Connectivity Validation System for HabitatCanvas

This module implements graph-based connectivity validation using NetworkX,
pathfinding algorithms for transit time calculations, and validation for
airlock placement and external access requirements.
"""

import math
import numpy as np
from typing import List, Dict, Set, Tuple, Optional, Union
import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logging.warning("NetworkX not available, falling back to basic graph operations")

from app.models.base import ModulePlacement, ModuleType
from app.models.module_library import get_module_library, ModuleDefinition

logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    """Types of connections between modules"""
    PRESSURIZED = "pressurized"  # Standard pressurized connection
    EMERGENCY = "emergency"      # Emergency access only
    SERVICE = "service"          # Service/utility connection
    EXTERNAL = "external"        # External/EVA access


@dataclass
class ConnectionSpec:
    """Specification for a connection between modules"""
    source_module: str
    target_module: str
    connection_type: ConnectionType
    distance: float
    port_source: Optional[str] = None
    port_target: Optional[str] = None
    is_bidirectional: bool = True
    capacity_rating: float = 1.0  # Relative capacity (1.0 = standard)


@dataclass
class PathfindingResult:
    """Result of pathfinding operation"""
    path: List[str]
    total_distance: float
    transit_time: float
    connection_types: List[ConnectionType]
    bottlenecks: List[str] = None
    
    def __post_init__(self):
        if self.bottlenecks is None:
            self.bottlenecks = []


class ConnectivityMetrics:
    """Comprehensive connectivity metrics"""
    
    def __init__(self):
        self.is_connected: bool = False
        self.component_count: int = 0
        self.largest_component_size: int = 0
        self.average_path_length: float = 0.0
        self.diameter: int = 0
        self.clustering_coefficient: float = 0.0
        self.betweenness_centrality: Dict[str, float] = {}
        self.closeness_centrality: Dict[str, float] = {}
        self.degree_centrality: Dict[str, float] = {}
        self.redundancy_score: float = 0.0
        self.airlock_accessibility: Dict[str, bool] = {}
        self.critical_paths: List[List[str]] = []


logger = logging.getLogger(__name__)


class ConnectivityGraph:
    """Enhanced graph representation of module connectivity with NetworkX integration"""
    
    def __init__(self, use_networkx: bool = True):
        self.use_networkx = use_networkx and NETWORKX_AVAILABLE
        self.nodes: Dict[str, ModulePlacement] = {}
        self.connections: Dict[Tuple[str, str], ConnectionSpec] = {}
        
        if self.use_networkx:
            self.graph = nx.Graph()
        else:
            # Fallback to basic graph representation
            self.edges: Dict[str, Set[str]] = defaultdict(set)
            self.distances: Dict[Tuple[str, str], float] = {}
    
    def add_node(self, module: ModulePlacement, **attributes):
        """Add a module as a node in the graph"""
        self.nodes[module.module_id] = module
        
        if self.use_networkx:
            self.graph.add_node(
                module.module_id,
                module_type=module.type,
                position=module.position,
                rotation=module.rotation_deg,
                **attributes
            )
        else:
            if module.module_id not in self.edges:
                self.edges[module.module_id] = set()
    
    def add_connection(self, connection: ConnectionSpec):
        """Add a connection between two modules"""
        key = (connection.source_module, connection.target_module)
        self.connections[key] = connection
        
        if connection.is_bidirectional:
            reverse_key = (connection.target_module, connection.source_module)
            reverse_connection = ConnectionSpec(
                source_module=connection.target_module,
                target_module=connection.source_module,
                connection_type=connection.connection_type,
                distance=connection.distance,
                port_source=connection.port_target,
                port_target=connection.port_source,
                is_bidirectional=True,
                capacity_rating=connection.capacity_rating
            )
            self.connections[reverse_key] = reverse_connection
        
        if self.use_networkx:
            self.graph.add_edge(
                connection.source_module,
                connection.target_module,
                weight=connection.distance,
                connection_type=connection.connection_type,
                capacity=connection.capacity_rating,
                port_source=connection.port_source,
                port_target=connection.port_target
            )
        else:
            # Fallback implementation
            self.edges[connection.source_module].add(connection.target_module)
            if connection.is_bidirectional:
                self.edges[connection.target_module].add(connection.source_module)
            
            self.distances[key] = connection.distance
            if connection.is_bidirectional:
                reverse_key = (connection.target_module, connection.source_module)
                self.distances[reverse_key] = connection.distance
    
    def is_connected(self) -> bool:
        """Check if all nodes are connected (graph connectivity)"""
        if not self.nodes:
            return True
        
        if self.use_networkx:
            return nx.is_connected(self.graph)
        else:
            # Fallback BFS implementation
            start_node = next(iter(self.nodes.keys()))
            visited = set()
            queue = deque([start_node])
            visited.add(start_node)
            
            while queue:
                current = queue.popleft()
                for neighbor in self.edges[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            
            return len(visited) == len(self.nodes)
    
    def get_connected_components(self) -> List[Set[str]]:
        """Get all connected components in the graph"""
        if self.use_networkx:
            return [set(component) for component in nx.connected_components(self.graph)]
        else:
            # Fallback implementation
            visited = set()
            components = []
            
            for node_id in self.nodes:
                if node_id not in visited:
                    component = set()
                    queue = deque([node_id])
                    
                    while queue:
                        current = queue.popleft()
                        if current not in visited:
                            visited.add(current)
                            component.add(current)
                            
                            for neighbor in self.edges[current]:
                                if neighbor not in visited:
                                    queue.append(neighbor)
                    
                    components.append(component)
            
            return components
    
    def shortest_path(self, start: str, end: str, weight: str = 'weight') -> Optional[List[str]]:
        """Find shortest path between two nodes"""
        if start not in self.nodes or end not in self.nodes:
            return None
        
        if start == end:
            return [start]
        
        if self.use_networkx:
            try:
                return nx.shortest_path(self.graph, start, end, weight=weight)
            except nx.NetworkXNoPath:
                return None
        else:
            # Fallback BFS implementation
            queue = deque([(start, [start])])
            visited = {start}
            
            while queue:
                current, path = queue.popleft()
                
                for neighbor in self.edges[current]:
                    if neighbor == end:
                        return path + [neighbor]
                    
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, path + [neighbor]))
            
            return None
    
    def shortest_path_length(self, start: str, end: str, weight: str = 'weight') -> float:
        """Calculate shortest path length between two nodes"""
        if self.use_networkx:
            try:
                return nx.shortest_path_length(self.graph, start, end, weight=weight)
            except nx.NetworkXNoPath:
                return float('inf')
        else:
            path = self.shortest_path(start, end)
            if not path:
                return float('inf')
            
            total_distance = 0.0
            for i in range(len(path) - 1):
                key = (path[i], path[i + 1])
                total_distance += self.distances.get(key, 0.0)
            
            return total_distance
    
    def all_pairs_shortest_path_length(self) -> Dict[Tuple[str, str], float]:
        """Calculate shortest path lengths between all pairs of nodes"""
        if self.use_networkx:
            return dict(nx.all_pairs_shortest_path_length(self.graph, weight='weight'))
        else:
            # Fallback implementation using Floyd-Warshall
            nodes = list(self.nodes.keys())
            n = len(nodes)
            
            # Initialize distance matrix
            dist = {}
            for i, node_i in enumerate(nodes):
                for j, node_j in enumerate(nodes):
                    if i == j:
                        dist[(node_i, node_j)] = 0.0
                    elif (node_i, node_j) in self.distances:
                        dist[(node_i, node_j)] = self.distances[(node_i, node_j)]
                    else:
                        dist[(node_i, node_j)] = float('inf')
            
            # Floyd-Warshall algorithm
            for k in nodes:
                for i in nodes:
                    for j in nodes:
                        if dist[(i, k)] + dist[(k, j)] < dist[(i, j)]:
                            dist[(i, j)] = dist[(i, k)] + dist[(k, j)]
            
            return dist
    
    def calculate_centrality_metrics(self) -> Dict[str, Dict[str, float]]:
        """Calculate various centrality metrics for all nodes"""
        if not self.use_networkx:
            return {}
        
        metrics = {}
        
        try:
            # Degree centrality
            degree_centrality = nx.degree_centrality(self.graph)
            
            # Betweenness centrality
            betweenness_centrality = nx.betweenness_centrality(self.graph, weight='weight')
            
            # Closeness centrality
            closeness_centrality = nx.closeness_centrality(self.graph, distance='weight')
            
            # Eigenvector centrality (if graph is connected)
            eigenvector_centrality = {}
            if nx.is_connected(self.graph):
                eigenvector_centrality = nx.eigenvector_centrality(self.graph, weight='weight')
            
            for node in self.graph.nodes():
                metrics[node] = {
                    'degree': degree_centrality.get(node, 0.0),
                    'betweenness': betweenness_centrality.get(node, 0.0),
                    'closeness': closeness_centrality.get(node, 0.0),
                    'eigenvector': eigenvector_centrality.get(node, 0.0)
                }
        
        except Exception as e:
            logger.warning(f"Error calculating centrality metrics: {e}")
        
        return metrics
    
    def find_critical_paths(self, airlocks: List[str]) -> List[List[str]]:
        """Find critical paths to airlocks for emergency egress"""
        critical_paths = []
        
        for node_id in self.nodes:
            if node_id in airlocks:
                continue  # Skip airlocks themselves
            
            # Find shortest paths to all airlocks
            paths_to_airlocks = []
            for airlock_id in airlocks:
                path = self.shortest_path(node_id, airlock_id)
                if path:
                    path_length = self.shortest_path_length(node_id, airlock_id)
                    paths_to_airlocks.append((path, path_length))
            
            # Sort by path length and take the shortest
            if paths_to_airlocks:
                paths_to_airlocks.sort(key=lambda x: x[1])
                critical_paths.append(paths_to_airlocks[0][0])
        
        return critical_paths
    
    def detect_bottlenecks(self) -> List[str]:
        """Detect bottleneck nodes using betweenness centrality"""
        if not self.use_networkx:
            return []
        
        try:
            betweenness = nx.betweenness_centrality(self.graph, weight='weight')
            
            # Nodes with high betweenness centrality are potential bottlenecks
            threshold = 0.1  # Adjust based on graph size and requirements
            bottlenecks = [
                node for node, centrality in betweenness.items()
                if centrality > threshold
            ]
            
            return bottlenecks
        
        except Exception as e:
            logger.warning(f"Error detecting bottlenecks: {e}")
            return []
    
    def calculate_redundancy_score(self, airlocks: List[str]) -> float:
        """Calculate redundancy score based on multiple paths to airlocks"""
        if len(airlocks) < 2:
            return 0.0  # No redundancy with less than 2 airlocks
        
        total_redundancy = 0.0
        node_count = 0
        
        for node_id in self.nodes:
            if node_id in airlocks:
                continue
            
            # Count how many airlocks are reachable
            reachable_airlocks = 0
            for airlock_id in airlocks:
                if self.shortest_path(node_id, airlock_id):
                    reachable_airlocks += 1
            
            # Redundancy score for this node (0 to 1)
            node_redundancy = min(1.0, (reachable_airlocks - 1) / (len(airlocks) - 1))
            total_redundancy += node_redundancy
            node_count += 1
        
        return total_redundancy / node_count if node_count > 0 else 0.0


class ConnectivityValidator:
    """
    Advanced connectivity validator with NetworkX integration, pathfinding algorithms,
    and comprehensive validation for airlock placement and external access requirements.
    """
    
    def __init__(self, use_networkx: bool = True):
        self.module_library = get_module_library()
        self.use_networkx = use_networkx and NETWORKX_AVAILABLE
        self.max_connection_distance = 6.0  # meters
        self.min_connection_distance = 0.1  # meters
        self.emergency_egress_time_limit = 300.0  # seconds (5 minutes)
        self.crew_movement_speed = 1.5  # m/s (walking speed in habitat)
    
    def validate_layout_connectivity(self, modules: List[ModulePlacement]) -> bool:
        """
        Validate that all modules in a layout are properly connected.
        
        Args:
            modules: List of module placements to validate
            
        Returns:
            True if layout has valid connectivity, False otherwise
        """
        if len(modules) < 2:
            return True  # Single module or empty layout is trivially connected
        
        # Build connectivity graph
        graph = self._build_connectivity_graph(modules)
        
        # Check if graph is connected
        is_connected = graph.is_connected()
        
        if not is_connected:
            components = graph.get_connected_components()
            logger.warning(f"Layout has {len(components)} disconnected components")
            for i, component in enumerate(components):
                logger.warning(f"Component {i+1}: {component}")
        
        return is_connected
    
    def calculate_transit_times(self, modules: List[ModulePlacement]) -> Dict[Tuple[str, str], float]:
        """
        Calculate transit times between all module pairs using pathfinding.
        
        Returns:
            Dictionary mapping module pairs to transit times in seconds
        """
        graph = self._build_connectivity_graph(modules)
        transit_times = {}
        
        # Get all pairs shortest path lengths
        if self.use_networkx:
            path_lengths = graph.all_pairs_shortest_path_length()
        else:
            path_lengths = graph.all_pairs_shortest_path_length()
        
        # Convert distances to transit times
        for (source, target), distance in path_lengths.items():
            if distance != float('inf'):
                # Add time for module traversal (assume 30 seconds per module)
                path = graph.shortest_path(source, target)
                module_traversal_time = len(path) * 30.0 if path else 0.0
                
                # Calculate movement time based on distance and speed
                movement_time = distance / self.crew_movement_speed
                
                total_time = movement_time + module_traversal_time
                transit_times[(source, target)] = total_time
            else:
                transit_times[(source, target)] = float('inf')
        
        return transit_times
    
    def validate_emergency_egress_times(
        self, 
        modules: List[ModulePlacement]
    ) -> Tuple[bool, List[str], Dict[str, float]]:
        """
        Validate emergency egress times to airlocks.
        
        Returns:
            Tuple of (is_valid, error_messages, egress_times_per_module)
        """
        errors = []
        egress_times = {}
        
        # Find airlocks
        airlocks = [m for m in modules if m.type == ModuleType.AIRLOCK]
        if not airlocks:
            errors.append("No airlocks found for emergency egress validation")
            return False, errors, egress_times
        
        # Build connectivity graph
        graph = self._build_connectivity_graph(modules)
        airlock_ids = [a.module_id for a in airlocks]
        
        # Check egress times for each module
        for module in modules:
            if module.type == ModuleType.AIRLOCK:
                egress_times[module.module_id] = 0.0
                continue
            
            # Find shortest egress time to any airlock
            min_egress_time = float('inf')
            best_airlock = None
            
            for airlock in airlocks:
                path = graph.shortest_path(module.module_id, airlock.module_id)
                if path:
                    distance = graph.shortest_path_length(module.module_id, airlock.module_id)
                    
                    # Calculate egress time (faster movement during emergency)
                    emergency_speed = self.crew_movement_speed * 1.5  # 50% faster in emergency
                    movement_time = distance / emergency_speed
                    
                    # Add time for module traversal (reduced in emergency)
                    module_traversal_time = (len(path) - 1) * 15.0  # 15 seconds per module
                    
                    total_egress_time = movement_time + module_traversal_time
                    
                    if total_egress_time < min_egress_time:
                        min_egress_time = total_egress_time
                        best_airlock = airlock.module_id
            
            egress_times[module.module_id] = min_egress_time
            
            # Check if egress time exceeds limit
            if min_egress_time > self.emergency_egress_time_limit:
                errors.append(
                    f"Module {module.module_id} egress time {min_egress_time:.1f}s "
                    f"exceeds limit of {self.emergency_egress_time_limit:.1f}s"
                )
            elif min_egress_time == float('inf'):
                errors.append(f"Module {module.module_id} has no path to any airlock")
        
        return len(errors) == 0, errors, egress_times
    
    def validate_pressurized_connectivity(self, modules: List[ModulePlacement]) -> Tuple[bool, List[str]]:
        """
        Validate pressurized connectivity requirements.
        
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []
        
        # Check basic connectivity first
        if not self.validate_layout_connectivity(modules):
            errors.append("Layout has disconnected modules - no pressurized pathway exists")
            return False, errors
        
        # Check airlock accessibility
        airlocks = [m for m in modules if m.type == ModuleType.AIRLOCK]
        if not airlocks:
            errors.append("No airlocks found - habitat cannot be accessed from outside")
            return False, errors
        
        # Build connectivity graph
        graph = self._build_connectivity_graph(modules)
        
        # Check that all modules can reach at least one airlock
        non_airlock_modules = [m for m in modules if m.type != ModuleType.AIRLOCK]
        
        for module in non_airlock_modules:
            can_reach_airlock = False
            
            for airlock in airlocks:
                path = graph.shortest_path(module.module_id, airlock.module_id)
                if path:
                    can_reach_airlock = True
                    break
            
            if not can_reach_airlock:
                errors.append(f"Module {module.module_id} cannot reach any airlock")
        
        # Check for critical path redundancy (at least 2 paths to airlocks for safety)
        if len(airlocks) == 1:
            errors.append("Only one airlock - no redundant egress path available")
        
        return len(errors) == 0, errors
    
    def validate_airlock_placement(self, modules: List[ModulePlacement]) -> Tuple[bool, List[str]]:
        """
        Validate airlock placement and external access requirements.
        
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []
        
        # Find airlocks
        airlocks = [m for m in modules if m.type == ModuleType.AIRLOCK]
        
        # Check minimum airlock requirements
        if len(airlocks) == 0:
            errors.append("No airlocks present - external access impossible")
            return False, errors
        
        if len(airlocks) == 1:
            errors.append("Only one airlock - no redundancy for emergency egress")
        
        # Check airlock distribution (should be reasonably spaced)
        if len(airlocks) >= 2:
            min_airlock_distance = float('inf')
            for i, airlock_a in enumerate(airlocks):
                for airlock_b in airlocks[i+1:]:
                    distance = self._calculate_distance(airlock_a.position, airlock_b.position)
                    min_airlock_distance = min(min_airlock_distance, distance)
            
            # Airlocks should be at least 10m apart for effective redundancy
            if min_airlock_distance < 10.0:
                errors.append(
                    f"Airlocks too close together ({min_airlock_distance:.1f}m) - "
                    "may not provide effective redundancy"
                )
        
        # Check airlock accessibility from all modules
        graph = self._build_connectivity_graph(modules)
        airlock_ids = [a.module_id for a in airlocks]
        
        for module in modules:
            if module.type == ModuleType.AIRLOCK:
                continue
            
            # Check if module can reach at least one airlock
            reachable_airlocks = 0
            for airlock_id in airlock_ids:
                if graph.shortest_path(module.module_id, airlock_id):
                    reachable_airlocks += 1
            
            if reachable_airlocks == 0:
                errors.append(f"Module {module.module_id} cannot reach any airlock")
            elif reachable_airlocks == 1 and len(airlocks) > 1:
                errors.append(
                    f"Module {module.module_id} can only reach one airlock - "
                    "no redundant egress path"
                )
        
        return len(errors) == 0, errors
    
    def analyze_connectivity_comprehensive(self, modules: List[ModulePlacement]) -> ConnectivityMetrics:
        """
        Perform comprehensive connectivity analysis.
        
        Returns:
            ConnectivityMetrics object with detailed analysis results
        """
        metrics = ConnectivityMetrics()
        
        if len(modules) < 2:
            metrics.is_connected = True
            metrics.component_count = 1 if modules else 0
            metrics.largest_component_size = len(modules)
            return metrics
        
        # Build connectivity graph
        graph = self._build_connectivity_graph(modules)
        
        # Basic connectivity metrics
        metrics.is_connected = graph.is_connected()
        components = graph.get_connected_components()
        metrics.component_count = len(components)
        metrics.largest_component_size = max(len(comp) for comp in components) if components else 0
        
        if self.use_networkx and metrics.is_connected:
            try:
                # Advanced NetworkX metrics
                metrics.diameter = nx.diameter(graph.graph)
                metrics.average_path_length = nx.average_shortest_path_length(graph.graph, weight='weight')
                metrics.clustering_coefficient = nx.average_clustering(graph.graph)
                
                # Centrality metrics
                centrality_data = graph.calculate_centrality_metrics()
                for node_id, centralities in centrality_data.items():
                    metrics.betweenness_centrality[node_id] = centralities['betweenness']
                    metrics.closeness_centrality[node_id] = centralities['closeness']
                    metrics.degree_centrality[node_id] = centralities['degree']
                
            except Exception as e:
                logger.warning(f"Error calculating advanced metrics: {e}")
        
        # Airlock-specific metrics
        airlocks = [m for m in modules if m.type == ModuleType.AIRLOCK]
        airlock_ids = [a.module_id for a in airlocks]
        
        if airlocks:
            # Check airlock accessibility for each module
            for module in modules:
                can_reach_airlock = False
                for airlock_id in airlock_ids:
                    if graph.shortest_path(module.module_id, airlock_id):
                        can_reach_airlock = True
                        break
                metrics.airlock_accessibility[module.module_id] = can_reach_airlock
            
            # Calculate redundancy score
            metrics.redundancy_score = graph.calculate_redundancy_score(airlock_ids)
            
            # Find critical paths
            metrics.critical_paths = graph.find_critical_paths(airlock_ids)
        
        return metrics
    
    def calculate_connectivity_metrics(self, modules: List[ModulePlacement]) -> Dict[str, float]:
        """
        Calculate connectivity quality metrics.
        
        Returns:
            Dictionary with connectivity metrics
        """
        if len(modules) < 2:
            return {
                'connectivity_ratio': 1.0,
                'average_path_length': 0.0,
                'clustering_coefficient': 1.0,
                'redundancy_score': 1.0
            }
        
        graph = self._build_connectivity_graph(modules)
        
        # Connectivity ratio (fraction of possible connections that exist)
        max_possible_edges = len(modules) * (len(modules) - 1) // 2
        actual_edges = sum(len(neighbors) for neighbors in graph.edges.values()) // 2
        connectivity_ratio = actual_edges / max_possible_edges if max_possible_edges > 0 else 0
        
        # Average path length
        total_path_length = 0.0
        path_count = 0
        
        module_ids = list(graph.nodes.keys())
        for i, module_a in enumerate(module_ids):
            for module_b in module_ids[i+1:]:
                path = graph.shortest_path(module_a, module_b)
                if path:
                    total_path_length += len(path) - 1  # Number of edges in path
                    path_count += 1
        
        avg_path_length = total_path_length / path_count if path_count > 0 else 0
        
        # Clustering coefficient (simplified)
        clustering_sum = 0.0
        for node_id in graph.nodes:
            neighbors = graph.edges[node_id]
            if len(neighbors) < 2:
                continue
            
            # Count triangles
            triangles = 0
            possible_triangles = len(neighbors) * (len(neighbors) - 1) // 2
            
            neighbor_list = list(neighbors)
            for i, neighbor_a in enumerate(neighbor_list):
                for neighbor_b in neighbor_list[i+1:]:
                    if neighbor_b in graph.edges[neighbor_a]:
                        triangles += 1
            
            clustering = triangles / possible_triangles if possible_triangles > 0 else 0
            clustering_sum += clustering
        
        clustering_coefficient = clustering_sum / len(graph.nodes) if graph.nodes else 0
        
        # Redundancy score (based on multiple paths to critical modules)
        airlocks = [m for m in modules if m.type == ModuleType.AIRLOCK]
        redundancy_score = min(1.0, len(airlocks) / 2.0)  # Target: 2+ airlocks
        
        return {
            'connectivity_ratio': connectivity_ratio,
            'average_path_length': avg_path_length,
            'clustering_coefficient': clustering_coefficient,
            'redundancy_score': redundancy_score
        }
    
    def suggest_connectivity_improvements(
        self, 
        modules: List[ModulePlacement]
    ) -> List[Dict[str, any]]:
        """
        Suggest improvements to layout connectivity.
        
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Check if layout is connected
        if not self.validate_layout_connectivity(modules):
            graph = self._build_connectivity_graph(modules)
            components = graph.get_connected_components()
            
            if len(components) > 1:
                suggestions.append({
                    'type': 'connectivity',
                    'priority': 'critical',
                    'description': f'Layout has {len(components)} disconnected components',
                    'recommendation': 'Move modules closer together or add connecting modules'
                })
        
        # Check airlock accessibility
        airlocks = [m for m in modules if m.type == ModuleType.AIRLOCK]
        if len(airlocks) == 0:
            suggestions.append({
                'type': 'safety',
                'priority': 'critical',
                'description': 'No airlocks present',
                'recommendation': 'Add at least one airlock module'
            })
        elif len(airlocks) == 1:
            suggestions.append({
                'type': 'safety',
                'priority': 'high',
                'description': 'Only one airlock - no redundant egress',
                'recommendation': 'Add a second airlock for redundancy'
            })
        
        # Check connectivity density
        metrics = self.calculate_connectivity_metrics(modules)
        if metrics['connectivity_ratio'] < 0.3:
            suggestions.append({
                'type': 'efficiency',
                'priority': 'medium',
                'description': 'Low connectivity density may increase transit times',
                'recommendation': 'Consider adding more connections between modules'
            })
        
        if metrics['average_path_length'] > 4:
            suggestions.append({
                'type': 'efficiency',
                'priority': 'medium',
                'description': 'Long average path lengths between modules',
                'recommendation': 'Reorganize layout to reduce distances between frequently used modules'
            })
        
        return suggestions
    
    def find_optimal_paths(
        self, 
        modules: List[ModulePlacement], 
        start_module: str, 
        end_module: str,
        path_type: str = 'shortest'
    ) -> List[PathfindingResult]:
        """
        Find optimal paths between modules using various algorithms.
        
        Args:
            modules: List of module placements
            start_module: Source module ID
            end_module: Target module ID
            path_type: Type of path ('shortest', 'fastest', 'safest')
            
        Returns:
            List of PathfindingResult objects
        """
        graph = self._build_connectivity_graph(modules)
        results = []
        
        if path_type == 'shortest':
            # Shortest distance path
            path = graph.shortest_path(start_module, end_module, weight='weight')
            if path:
                distance = graph.shortest_path_length(start_module, end_module, weight='weight')
                transit_time = distance / self.crew_movement_speed + (len(path) - 1) * 30.0
                
                # Get connection types along path
                connection_types = []
                for i in range(len(path) - 1):
                    conn_key = (path[i], path[i + 1])
                    if conn_key in graph.connections:
                        connection_types.append(graph.connections[conn_key].connection_type)
                    else:
                        connection_types.append(ConnectionType.PRESSURIZED)
                
                results.append(PathfindingResult(
                    path=path,
                    total_distance=distance,
                    transit_time=transit_time,
                    connection_types=connection_types
                ))
        
        elif path_type == 'fastest':
            # Path optimized for transit time (considering capacity constraints)
            # This would require more sophisticated pathfinding with capacity weights
            path = graph.shortest_path(start_module, end_module, weight='weight')
            if path:
                # Calculate time considering bottlenecks
                bottlenecks = graph.detect_bottlenecks()
                
                distance = graph.shortest_path_length(start_module, end_module, weight='weight')
                base_time = distance / self.crew_movement_speed + (len(path) - 1) * 30.0
                
                # Add delay for bottlenecks
                bottleneck_delay = sum(60.0 for node in path if node in bottlenecks)
                
                results.append(PathfindingResult(
                    path=path,
                    total_distance=distance,
                    transit_time=base_time + bottleneck_delay,
                    connection_types=[ConnectionType.PRESSURIZED] * (len(path) - 1),
                    bottlenecks=[node for node in path if node in bottlenecks]
                ))
        
        return results
    
    def validate_connection_capacity(
        self, 
        modules: List[ModulePlacement],
        traffic_patterns: Dict[Tuple[str, str], float] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate connection capacity against expected traffic patterns.
        
        Args:
            modules: List of module placements
            traffic_patterns: Expected traffic between module pairs (trips per hour)
            
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []
        
        if not traffic_patterns:
            # Generate default traffic patterns based on module types
            traffic_patterns = self._generate_default_traffic_patterns(modules)
        
        graph = self._build_connectivity_graph(modules)
        
        # Analyze traffic flow through each connection
        connection_loads = defaultdict(float)
        
        for (source, target), traffic_volume in traffic_patterns.items():
            path = graph.shortest_path(source, target)
            if path:
                # Distribute traffic along the path
                for i in range(len(path) - 1):
                    conn_key = (path[i], path[i + 1])
                    connection_loads[conn_key] += traffic_volume
        
        # Check capacity constraints
        for conn_key, load in connection_loads.items():
            if conn_key in graph.connections:
                connection = graph.connections[conn_key]
                capacity = connection.capacity_rating * 10.0  # Base capacity: 10 trips/hour
                
                if load > capacity:
                    errors.append(
                        f"Connection {conn_key[0]} -> {conn_key[1]} overloaded: "
                        f"{load:.1f} > {capacity:.1f} trips/hour"
                    )
        
        return len(errors) == 0, errors
    
    def _generate_default_traffic_patterns(self, modules: List[ModulePlacement]) -> Dict[Tuple[str, str], float]:
        """Generate default traffic patterns based on module types"""
        patterns = {}
        
        # Define typical traffic between module types (trips per hour)
        type_traffic = {
            (ModuleType.SLEEP_QUARTER, ModuleType.GALLEY): 3.0,
            (ModuleType.SLEEP_QUARTER, ModuleType.MEDICAL): 0.5,
            (ModuleType.GALLEY, ModuleType.STORAGE): 2.0,
            (ModuleType.LABORATORY, ModuleType.STORAGE): 1.5,
            (ModuleType.EXERCISE, ModuleType.MEDICAL): 1.0,
            (ModuleType.AIRLOCK, ModuleType.STORAGE): 1.0,
        }
        
        # Generate patterns for all module pairs
        for module_a in modules:
            for module_b in modules:
                if module_a.module_id == module_b.module_id:
                    continue
                
                # Look up traffic pattern
                traffic = 0.0
                type_pair = (module_a.type, module_b.type)
                reverse_pair = (module_b.type, module_a.type)
                
                if type_pair in type_traffic:
                    traffic = type_traffic[type_pair]
                elif reverse_pair in type_traffic:
                    traffic = type_traffic[reverse_pair]
                
                if traffic > 0:
                    patterns[(module_a.module_id, module_b.module_id)] = traffic
        
        return patterns
    
    def _build_connectivity_graph(self, modules: List[ModulePlacement]) -> ConnectivityGraph:
        """Build enhanced connectivity graph from module placements"""
        graph = ConnectivityGraph(use_networkx=self.use_networkx)
        
        # Add all modules as nodes
        for module in modules:
            graph.add_node(module)
        
        # Add connections based on proximity and module compatibility
        for i, module_a in enumerate(modules):
            for module_b in modules[i+1:]:
                distance = self._calculate_distance(module_a.position, module_b.position)
                
                # Connect modules if they're within connection distance
                if self.min_connection_distance <= distance <= self.max_connection_distance:
                    # Determine connection type based on module types
                    connection_type = self._determine_connection_type(module_a, module_b)
                    
                    # Calculate capacity based on module types and distance
                    capacity = self._calculate_connection_capacity(module_a, module_b, distance)
                    
                    connection = ConnectionSpec(
                        source_module=module_a.module_id,
                        target_module=module_b.module_id,
                        connection_type=connection_type,
                        distance=distance,
                        capacity_rating=capacity
                    )
                    
                    graph.add_connection(connection)
        
        return graph
    
    def _determine_connection_type(self, module_a: ModulePlacement, module_b: ModulePlacement) -> ConnectionType:
        """Determine the type of connection between two modules"""
        # Airlocks have external connections
        if module_a.type == ModuleType.AIRLOCK or module_b.type == ModuleType.AIRLOCK:
            return ConnectionType.EXTERNAL
        
        # Medical modules have emergency connections
        if module_a.type == ModuleType.MEDICAL or module_b.type == ModuleType.MEDICAL:
            return ConnectionType.EMERGENCY
        
        # Mechanical modules have service connections
        if module_a.type == ModuleType.MECHANICAL or module_b.type == ModuleType.MECHANICAL:
            return ConnectionType.SERVICE
        
        # Default to pressurized connection
        return ConnectionType.PRESSURIZED
    
    def _calculate_connection_capacity(
        self, 
        module_a: ModulePlacement, 
        module_b: ModulePlacement, 
        distance: float
    ) -> float:
        """Calculate connection capacity based on module types and distance"""
        base_capacity = 1.0
        
        # Larger modules can support higher capacity connections
        high_capacity_types = {ModuleType.GALLEY, ModuleType.LABORATORY, ModuleType.AIRLOCK}
        
        if module_a.type in high_capacity_types or module_b.type in high_capacity_types:
            base_capacity *= 1.5
        
        # Closer connections have higher capacity
        if distance < 3.0:
            base_capacity *= 1.2
        elif distance > 5.0:
            base_capacity *= 0.8
        
        return base_capacity
    
    def _calculate_distance(self, pos1: List[float], pos2: List[float]) -> float:
        """Calculate Euclidean distance between two positions"""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(pos1, pos2)))
    
    def validate_module_connections(
        self, 
        module: ModulePlacement, 
        connected_modules: List[ModulePlacement]
    ) -> Tuple[bool, List[str]]:
        """
        Validate connections for a specific module.
        
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []
        
        # Get module definition for validation rules
        module_def = self._get_module_definition(module.module_id)
        if not module_def:
            errors.append(f"Module definition not found for {module.module_id}")
            return False, errors
        
        # Check adjacency preferences and restrictions
        for connected_module in connected_modules:
            distance = self._calculate_distance(module.position, connected_module.position)
            
            # Check if connection violates restrictions
            if connected_module.type in module_def.spec.adjacency_restrictions:
                errors.append(
                    f"Module {module.module_id} should not be adjacent to {connected_module.type} modules"
                )
            
            # Check connection distance
            if distance > self.max_connection_distance:
                errors.append(
                    f"Connection distance {distance:.2f}m exceeds maximum {self.max_connection_distance}m"
                )
            elif distance < self.min_connection_distance:
                errors.append(
                    f"Connection distance {distance:.2f}m is below minimum {self.min_connection_distance}m"
                )
        
        return len(errors) == 0, errors
    
    def _get_module_definition(self, module_id: str) -> Optional[ModuleDefinition]:
        """Get module definition by ID, handling both library and instance IDs"""
        # First try direct lookup
        module_def = self.module_library.get_module(module_id)
        if module_def:
            return module_def
        
        # If not found, try to extract base type from instance ID
        if '_' in module_id:
            parts = module_id.split('_')
            if len(parts) >= 3:  # Need at least type_number_hash
                module_type = '_'.join(parts[:-2])  # e.g., "sleep_quarter" from "sleep_quarter_001_abc123def"
                std_module_id = f"std_{module_type}"
                module_def = self.module_library.get_module(std_module_id)
                if module_def:
                    return module_def
        
        return None