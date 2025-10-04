"""
Pareto Front Generation and Ranking System for Multi-Objective Optimization

This module provides tools for analyzing Pareto-optimal solutions,
ranking layouts based on dominance relationships, and generating
visualization data for multi-objective tradeoffs.
"""

import numpy as np
import logging
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import seaborn as sns

from app.models.base import LayoutSpec, PerformanceMetrics, MissionParameters

logger = logging.getLogger(__name__)


class DominanceRelation(str, Enum):
    """Types of dominance relationships between solutions"""
    DOMINATES = "dominates"
    DOMINATED_BY = "dominated_by"
    NON_DOMINATED = "non_dominated"
    EQUIVALENT = "equivalent"


@dataclass
class ParetoSolution:
    """Represents a solution in the Pareto analysis"""
    layout: LayoutSpec
    objectives: np.ndarray
    rank: int = 0
    crowding_distance: float = 0.0
    dominance_count: int = 0
    dominated_solutions: Set[int] = None
    
    def __post_init__(self):
        if self.dominated_solutions is None:
            self.dominated_solutions = set()


@dataclass
class ParetoFront:
    """Represents a Pareto front with associated solutions"""
    rank: int
    solutions: List[ParetoSolution]
    hypervolume: float = 0.0
    spread: float = 0.0
    
    @property
    def size(self) -> int:
        return len(self.solutions)
    
    @property
    def objective_matrix(self) -> np.ndarray:
        """Get objectives as a matrix for analysis"""
        return np.array([sol.objectives for sol in self.solutions])


class ParetoAnalyzer:
    """
    Analyzer for multi-objective optimization results using Pareto dominance.
    
    Provides methods for ranking solutions, calculating Pareto fronts,
    and generating visualization data for multi-objective tradeoffs.
    """
    
    def __init__(self):
        self.reference_point = None
        self.ideal_point = None
        self.nadir_point = None
    
    def analyze_solutions(
        self, 
        layouts: List[LayoutSpec],
        objectives: List[str] = None
    ) -> List[ParetoFront]:
        """
        Analyze a set of layouts and return ranked Pareto fronts.
        
        Args:
            layouts: List of layout specifications to analyze
            objectives: List of objective names to consider (if None, uses all)
            
        Returns:
            List of ParetoFront objects ranked by dominance
        """
        if not layouts:
            return []
        
        logger.info(f"Analyzing {len(layouts)} solutions for Pareto optimality")
        
        # Extract objective values
        solutions = self._create_pareto_solutions(layouts, objectives)
        
        # Calculate reference points
        self._calculate_reference_points(solutions)
        
        # Perform non-dominated sorting
        pareto_fronts = self._non_dominated_sort(solutions)
        
        # Calculate crowding distances
        for front in pareto_fronts:
            self._calculate_crowding_distance(front)
        
        # Calculate front metrics
        for front in pareto_fronts:
            front.hypervolume = self._calculate_hypervolume(front)
            front.spread = self._calculate_spread(front)
        
        logger.info(f"Found {len(pareto_fronts)} Pareto fronts")
        
        return pareto_fronts
    
    def _create_pareto_solutions(
        self, 
        layouts: List[LayoutSpec], 
        objectives: List[str] = None
    ) -> List[ParetoSolution]:
        """Convert layouts to ParetoSolution objects"""
        solutions = []
        
        # Default objectives (all minimization)
        if objectives is None:
            objectives = [
                'mean_transit_time',
                'mass_total', 
                'power_budget',
                'egress_time'
            ]
        
        for i, layout in enumerate(layouts):
            # Extract objective values from performance metrics
            obj_values = []
            metrics = layout.kpis
            
            for obj_name in objectives:
                if hasattr(metrics, obj_name):
                    value = getattr(metrics, obj_name)
                    obj_values.append(value)
                else:
                    # Handle derived objectives
                    if obj_name == 'safety_risk':
                        # Convert safety score to risk (minimization)
                        safety_score = getattr(metrics, 'safety_score', 0.5)
                        obj_values.append(1.0 - safety_score)
                    elif obj_name == 'thermal_risk':
                        # Convert thermal margin to risk
                        thermal_margin = getattr(metrics, 'thermal_margin', 0.0)
                        obj_values.append(max(0, 1.0 - thermal_margin))
                    else:
                        logger.warning(f"Unknown objective: {obj_name}")
                        obj_values.append(0.0)
            
            solution = ParetoSolution(
                layout=layout,
                objectives=np.array(obj_values)
            )
            solutions.append(solution)
        
        return solutions
    
    def _calculate_reference_points(self, solutions: List[ParetoSolution]):
        """Calculate ideal and nadir points for normalization"""
        if not solutions:
            return
        
        objectives_matrix = np.array([sol.objectives for sol in solutions])
        
        # Ideal point (minimum values for minimization objectives)
        self.ideal_point = np.min(objectives_matrix, axis=0)
        
        # Nadir point (maximum values for minimization objectives)
        self.nadir_point = np.max(objectives_matrix, axis=0)
        
        # Reference point for hypervolume calculation (slightly worse than nadir)
        self.reference_point = self.nadir_point * 1.1
    
    def _non_dominated_sort(self, solutions: List[ParetoSolution]) -> List[ParetoFront]:
        """Perform non-dominated sorting using NSGA-II algorithm"""
        n = len(solutions)
        
        # Initialize dominance relationships
        for i in range(n):
            solutions[i].dominance_count = 0
            solutions[i].dominated_solutions = set()
            
            for j in range(n):
                if i != j:
                    relation = self._compare_solutions(solutions[i], solutions[j])
                    
                    if relation == DominanceRelation.DOMINATES:
                        solutions[i].dominated_solutions.add(j)
                    elif relation == DominanceRelation.DOMINATED_BY:
                        solutions[i].dominance_count += 1
        
        # Build Pareto fronts
        pareto_fronts = []
        current_front = []
        
        # First front: solutions with dominance_count = 0
        for i, solution in enumerate(solutions):
            if solution.dominance_count == 0:
                solution.rank = 0
                current_front.append(solution)
        
        front_rank = 0
        
        while current_front:
            pareto_fronts.append(ParetoFront(
                rank=front_rank,
                solutions=current_front.copy()
            ))
            
            next_front = []
            
            for solution in current_front:
                for j in solution.dominated_solutions:
                    solutions[j].dominance_count -= 1
                    if solutions[j].dominance_count == 0:
                        solutions[j].rank = front_rank + 1
                        next_front.append(solutions[j])
            
            current_front = next_front
            front_rank += 1
        
        return pareto_fronts
    
    def _compare_solutions(
        self, 
        sol1: ParetoSolution, 
        sol2: ParetoSolution
    ) -> DominanceRelation:
        """Compare two solutions for dominance relationship"""
        obj1 = sol1.objectives
        obj2 = sol2.objectives
        
        # Check if sol1 dominates sol2
        dominates = True
        strictly_better = False
        
        for i in range(len(obj1)):
            if obj1[i] > obj2[i]:  # Worse in this objective (minimization)
                dominates = False
                break
            elif obj1[i] < obj2[i]:  # Better in this objective
                strictly_better = True
        
        if dominates and strictly_better:
            return DominanceRelation.DOMINATES
        
        # Check if sol2 dominates sol1
        dominates = True
        strictly_better = False
        
        for i in range(len(obj1)):
            if obj2[i] > obj1[i]:  # sol2 worse in this objective
                dominates = False
                break
            elif obj2[i] < obj1[i]:  # sol2 better in this objective
                strictly_better = True
        
        if dominates and strictly_better:
            return DominanceRelation.DOMINATED_BY
        
        # Check for equivalence
        if np.allclose(obj1, obj2, rtol=1e-6):
            return DominanceRelation.EQUIVALENT
        
        return DominanceRelation.NON_DOMINATED
    
    def _calculate_crowding_distance(self, front: ParetoFront):
        """Calculate crowding distance for solutions in a front"""
        if front.size <= 2:
            # Boundary solutions get infinite distance
            for solution in front.solutions:
                solution.crowding_distance = float('inf')
            return
        
        n_objectives = len(front.solutions[0].objectives)
        
        # Initialize distances
        for solution in front.solutions:
            solution.crowding_distance = 0.0
        
        # Calculate distance for each objective
        for obj_idx in range(n_objectives):
            # Sort solutions by this objective
            front.solutions.sort(key=lambda x: x.objectives[obj_idx])
            
            # Boundary solutions get infinite distance
            front.solutions[0].crowding_distance = float('inf')
            front.solutions[-1].crowding_distance = float('inf')
            
            # Calculate objective range
            obj_range = (front.solutions[-1].objectives[obj_idx] - 
                        front.solutions[0].objectives[obj_idx])
            
            if obj_range == 0:
                continue
            
            # Calculate distances for intermediate solutions
            for i in range(1, front.size - 1):
                if front.solutions[i].crowding_distance != float('inf'):
                    distance = (front.solutions[i+1].objectives[obj_idx] - 
                              front.solutions[i-1].objectives[obj_idx]) / obj_range
                    front.solutions[i].crowding_distance += distance
    
    def _calculate_hypervolume(self, front: ParetoFront) -> float:
        """Calculate hypervolume indicator for a Pareto front"""
        if not front.solutions or self.reference_point is None:
            return 0.0
        
        try:
            # Simple 2D hypervolume calculation
            if len(front.solutions[0].objectives) == 2:
                return self._calculate_2d_hypervolume(front)
            else:
                # For higher dimensions, use approximation
                return self._calculate_approximate_hypervolume(front)
        
        except Exception as e:
            logger.warning(f"Error calculating hypervolume: {str(e)}")
            return 0.0
    
    def _calculate_2d_hypervolume(self, front: ParetoFront) -> float:
        """Calculate exact 2D hypervolume"""
        # Sort solutions by first objective
        sorted_solutions = sorted(front.solutions, key=lambda x: x.objectives[0])
        
        hypervolume = 0.0
        prev_x = self.reference_point[0]
        
        for solution in sorted_solutions:
            x, y = solution.objectives
            
            # Skip if solution is dominated by reference point
            if x >= self.reference_point[0] or y >= self.reference_point[1]:
                continue
            
            # Calculate area contribution
            width = prev_x - x
            height = self.reference_point[1] - y
            
            if width > 0 and height > 0:
                hypervolume += width * height
            
            prev_x = x
        
        return hypervolume
    
    def _calculate_approximate_hypervolume(self, front: ParetoFront) -> float:
        """Calculate approximate hypervolume for higher dimensions"""
        # Use Monte Carlo approximation
        n_samples = 10000
        n_objectives = len(front.solutions[0].objectives)
        
        # Generate random points in the objective space
        random_points = np.random.uniform(
            low=self.ideal_point,
            high=self.reference_point,
            size=(n_samples, n_objectives)
        )
        
        dominated_count = 0
        
        for point in random_points:
            # Check if point is dominated by any solution in the front
            for solution in front.solutions:
                if np.all(solution.objectives <= point):
                    dominated_count += 1
                    break
        
        # Calculate hypervolume as fraction of reference volume
        reference_volume = np.prod(self.reference_point - self.ideal_point)
        hypervolume = (dominated_count / n_samples) * reference_volume
        
        return hypervolume
    
    def _calculate_spread(self, front: ParetoFront) -> float:
        """Calculate spread metric for diversity assessment"""
        if front.size < 2:
            return 0.0
        
        try:
            objectives_matrix = front.objective_matrix
            
            # Calculate pairwise distances
            distances = []
            for i in range(front.size):
                for j in range(i + 1, front.size):
                    dist = np.linalg.norm(objectives_matrix[i] - objectives_matrix[j])
                    distances.append(dist)
            
            if not distances:
                return 0.0
            
            # Spread is the standard deviation of distances
            return float(np.std(distances))
        
        except Exception as e:
            logger.warning(f"Error calculating spread: {str(e)}")
            return 0.0
    
    def get_best_compromise_solution(
        self, 
        pareto_fronts: List[ParetoFront],
        weights: Dict[str, float] = None
    ) -> Optional[LayoutSpec]:
        """
        Find the best compromise solution using weighted sum approach.
        
        Args:
            pareto_fronts: List of Pareto fronts from analysis
            weights: Objective weights for compromise solution
            
        Returns:
            Best compromise layout or None if no solutions
        """
        if not pareto_fronts or not pareto_fronts[0].solutions:
            return None
        
        # Use first front (best Pareto front)
        first_front = pareto_fronts[0]
        
        if weights is None:
            # Equal weights for all objectives
            n_objectives = len(first_front.solutions[0].objectives)
            weights = {f"obj_{i}": 1.0/n_objectives for i in range(n_objectives)}
        
        best_solution = None
        best_score = float('inf')
        
        # Normalize objectives using ideal and nadir points
        for solution in first_front.solutions:
            normalized_objectives = self._normalize_objectives(solution.objectives)
            
            # Calculate weighted sum
            weighted_sum = 0.0
            for i, (obj_name, weight) in enumerate(weights.items()):
                if i < len(normalized_objectives):
                    weighted_sum += weight * normalized_objectives[i]
            
            if weighted_sum < best_score:
                best_score = weighted_sum
                best_solution = solution
        
        return best_solution.layout if best_solution else None
    
    def _normalize_objectives(self, objectives: np.ndarray) -> np.ndarray:
        """Normalize objectives using ideal and nadir points"""
        if self.ideal_point is None or self.nadir_point is None:
            return objectives
        
        # Avoid division by zero
        ranges = self.nadir_point - self.ideal_point
        ranges = np.where(ranges == 0, 1.0, ranges)
        
        normalized = (objectives - self.ideal_point) / ranges
        return np.clip(normalized, 0.0, 1.0)
    
    def generate_tradeoff_analysis(
        self, 
        pareto_fronts: List[ParetoFront],
        objective_names: List[str] = None
    ) -> Dict[str, any]:
        """
        Generate comprehensive tradeoff analysis data.
        
        Args:
            pareto_fronts: List of Pareto fronts
            objective_names: Names of objectives for labeling
            
        Returns:
            Dictionary containing analysis results and visualization data
        """
        if not pareto_fronts:
            return {}
        
        if objective_names is None:
            n_objectives = len(pareto_fronts[0].solutions[0].objectives)
            objective_names = [f"Objective {i+1}" for i in range(n_objectives)]
        
        analysis = {
            'summary': {
                'total_solutions': sum(front.size for front in pareto_fronts),
                'pareto_fronts': len(pareto_fronts),
                'first_front_size': pareto_fronts[0].size,
                'objective_names': objective_names
            },
            'fronts': [],
            'tradeoffs': {},
            'recommendations': []
        }
        
        # Analyze each front
        for front in pareto_fronts:
            front_data = {
                'rank': front.rank,
                'size': front.size,
                'hypervolume': front.hypervolume,
                'spread': front.spread,
                'solutions': []
            }
            
            for solution in front.solutions:
                solution_data = {
                    'layout_id': solution.layout.layout_id,
                    'objectives': solution.objectives.tolist(),
                    'crowding_distance': solution.crowding_distance,
                    'overall_score': solution.layout.kpis.overall_score
                }
                front_data['solutions'].append(solution_data)
            
            analysis['fronts'].append(front_data)
        
        # Analyze tradeoffs between objectives
        first_front = pareto_fronts[0]
        if first_front.size > 1:
            objectives_matrix = first_front.objective_matrix
            
            # Calculate correlation matrix
            correlation_matrix = np.corrcoef(objectives_matrix.T)
            
            analysis['tradeoffs'] = {
                'correlation_matrix': correlation_matrix.tolist(),
                'strong_tradeoffs': [],
                'weak_tradeoffs': []
            }
            
            # Identify strong and weak tradeoffs
            for i in range(len(objective_names)):
                for j in range(i + 1, len(objective_names)):
                    correlation = correlation_matrix[i, j]
                    
                    if correlation > 0.7:
                        analysis['tradeoffs']['strong_tradeoffs'].append({
                            'objectives': [objective_names[i], objective_names[j]],
                            'correlation': float(correlation),
                            'type': 'positive'
                        })
                    elif correlation < -0.7:
                        analysis['tradeoffs']['strong_tradeoffs'].append({
                            'objectives': [objective_names[i], objective_names[j]],
                            'correlation': float(correlation),
                            'type': 'negative'
                        })
                    elif abs(correlation) < 0.3:
                        analysis['tradeoffs']['weak_tradeoffs'].append({
                            'objectives': [objective_names[i], objective_names[j]],
                            'correlation': float(correlation)
                        })
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_recommendations(pareto_fronts)
        
        return analysis
    
    def _generate_recommendations(self, pareto_fronts: List[ParetoFront]) -> List[Dict[str, str]]:
        """Generate recommendations based on Pareto analysis"""
        recommendations = []
        
        if not pareto_fronts:
            return recommendations
        
        first_front = pareto_fronts[0]
        
        # Recommendation 1: Best overall solution
        if first_front.solutions:
            best_overall = max(
                first_front.solutions, 
                key=lambda x: x.layout.kpis.overall_score
            )
            recommendations.append({
                'type': 'best_overall',
                'layout_id': best_overall.layout.layout_id,
                'reason': f'Highest overall performance score ({best_overall.layout.kpis.overall_score:.3f})'
            })
        
        # Recommendation 2: Most diverse solution
        if len(first_front.solutions) > 1:
            most_diverse = max(
                first_front.solutions,
                key=lambda x: x.crowding_distance if x.crowding_distance != float('inf') else 0
            )
            recommendations.append({
                'type': 'most_diverse',
                'layout_id': most_diverse.layout.layout_id,
                'reason': 'Represents unique tradeoff in objective space'
            })
        
        # Recommendation 3: Safety-focused solution
        safety_focused = max(
            first_front.solutions,
            key=lambda x: x.layout.kpis.safety_score or 0.5
        )
        recommendations.append({
            'type': 'safety_focused',
            'layout_id': safety_focused.layout.layout_id,
            'reason': f'Highest safety score ({safety_focused.layout.kpis.safety_score or 0.5:.3f})'
        })
        
        # Recommendation 4: Efficiency-focused solution
        efficiency_focused = min(
            first_front.solutions,
            key=lambda x: x.layout.kpis.mean_transit_time
        )
        recommendations.append({
            'type': 'efficiency_focused',
            'layout_id': efficiency_focused.layout.layout_id,
            'reason': f'Lowest transit time ({efficiency_focused.layout.kpis.mean_transit_time:.1f}s)'
        })
        
        return recommendations


# Factory function for easy instantiation
def create_pareto_analyzer() -> ParetoAnalyzer:
    """Create a new Pareto analyzer instance"""
    return ParetoAnalyzer()


# Utility functions for visualization data generation
def generate_pareto_plot_data(
    pareto_fronts: List[ParetoFront],
    obj_x_idx: int = 0,
    obj_y_idx: int = 1
) -> Dict[str, any]:
    """
    Generate data for 2D Pareto front visualization.
    
    Args:
        pareto_fronts: List of Pareto fronts
        obj_x_idx: Index of objective for x-axis
        obj_y_idx: Index of objective for y-axis
        
    Returns:
        Dictionary with plot data
    """
    plot_data = {
        'fronts': [],
        'all_points': [],
        'axis_labels': [f'Objective {obj_x_idx + 1}', f'Objective {obj_y_idx + 1}']
    }
    
    for front in pareto_fronts:
        front_points = []
        
        for solution in front.solutions:
            point = {
                'x': float(solution.objectives[obj_x_idx]),
                'y': float(solution.objectives[obj_y_idx]),
                'layout_id': solution.layout.layout_id,
                'rank': front.rank,
                'crowding_distance': solution.crowding_distance
            }
            front_points.append(point)
            plot_data['all_points'].append(point)
        
        plot_data['fronts'].append({
            'rank': front.rank,
            'points': front_points,
            'size': len(front_points)
        })
    
    return plot_data


def generate_parallel_coordinates_data(
    pareto_fronts: List[ParetoFront],
    objective_names: List[str] = None
) -> Dict[str, any]:
    """
    Generate data for parallel coordinates visualization.
    
    Args:
        pareto_fronts: List of Pareto fronts
        objective_names: Names of objectives
        
    Returns:
        Dictionary with parallel coordinates data
    """
    if not pareto_fronts or not pareto_fronts[0].solutions:
        return {}
    
    n_objectives = len(pareto_fronts[0].solutions[0].objectives)
    
    if objective_names is None:
        objective_names = [f'Obj {i+1}' for i in range(n_objectives)]
    
    # Collect all objective values for normalization
    all_objectives = []
    for front in pareto_fronts:
        for solution in front.solutions:
            all_objectives.append(solution.objectives)
    
    all_objectives = np.array(all_objectives)
    
    # Calculate normalization parameters
    min_vals = np.min(all_objectives, axis=0)
    max_vals = np.max(all_objectives, axis=0)
    ranges = max_vals - min_vals
    ranges = np.where(ranges == 0, 1.0, ranges)  # Avoid division by zero
    
    plot_data = {
        'objective_names': objective_names,
        'solutions': [],
        'normalization': {
            'min_vals': min_vals.tolist(),
            'max_vals': max_vals.tolist()
        }
    }
    
    for front in pareto_fronts:
        for solution in front.solutions:
            # Normalize objectives to 0-1 range
            normalized_objectives = (solution.objectives - min_vals) / ranges
            
            solution_data = {
                'layout_id': solution.layout.layout_id,
                'rank': front.rank,
                'objectives': solution.objectives.tolist(),
                'normalized_objectives': normalized_objectives.tolist(),
                'overall_score': solution.layout.kpis.overall_score
            }
            plot_data['solutions'].append(solution_data)
    
    return plot_data