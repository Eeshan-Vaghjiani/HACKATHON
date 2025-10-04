"""
NSGA-II Multi-Objective Optimization Engine for HabitatCanvas

This module implements the NSGA-II genetic algorithm for multi-objective
optimization of habitat layouts, focusing on transit time, mass, power,
and safety objectives.
"""

import numpy as np
import logging
from typing import List, Dict, Tuple, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.optimize import minimize
from pymoo.core.result import Result

from app.models.base import (
    EnvelopeSpec, MissionParameters, LayoutSpec, ModulePlacement, 
    PerformanceMetrics, LayoutMetadata, ModuleType
)
from app.models.module_library import get_module_library, ModuleDefinition
from app.services.collision_detector import CollisionDetector
from app.services.connectivity_validator import ConnectivityValidator
from app.services.scoring_engine import EnhancedScoringEngine
from app.services.layout_grammar import create_layout_grammar

logger = logging.getLogger(__name__)


class OptimizationObjective(str, Enum):
    """Optimization objectives for multi-objective optimization"""
    TRANSIT_TIME = "transit_time"
    MASS = "mass"
    POWER = "power"
    SAFETY = "safety"
    THERMAL = "thermal"
    LSS_MARGIN = "lss_margin"
    VOLUME_EFFICIENCY = "volume_efficiency"


@dataclass
class OptimizationConfig:
    """Configuration for NSGA-II optimization"""
    population_size: int = 50
    generations: int = 100
    crossover_prob: float = 0.9
    mutation_prob: float = 0.1
    crossover_eta: float = 15.0
    mutation_eta: float = 20.0
    objectives: List[OptimizationObjective] = None
    objective_weights: Dict[OptimizationObjective, float] = None
    
    def __post_init__(self):
        if self.objectives is None:
            self.objectives = [
                OptimizationObjective.TRANSIT_TIME,
                OptimizationObjective.MASS,
                OptimizationObjective.POWER,
                OptimizationObjective.SAFETY
            ]
        
        if self.objective_weights is None:
            # Default equal weights
            weight = 1.0 / len(self.objectives)
            self.objective_weights = {obj: weight for obj in self.objectives}


@dataclass
class OptimizationResult:
    """Result of NSGA-II optimization"""
    pareto_layouts: List[LayoutSpec]
    best_layout: LayoutSpec
    convergence_history: List[float]
    generation_count: int
    evaluation_count: int
    optimization_time: float
    config: OptimizationConfig


class HabitatLayoutProblem(Problem):
    """
    Pymoo Problem definition for habitat layout optimization.
    
    Decision variables represent module positions and rotations.
    Objectives include transit time, mass, power consumption, and safety metrics.
    """
    
    def __init__(
        self,
        envelope: EnvelopeSpec,
        mission_params: MissionParameters,
        required_modules: List[ModuleDefinition],
        config: OptimizationConfig
    ):
        self.envelope = envelope
        self.mission_params = mission_params
        self.required_modules = required_modules
        self.config = config
        
        # Initialize services
        self.collision_detector = CollisionDetector()
        self.connectivity_validator = ConnectivityValidator()
        self.scoring_engine = EnhancedScoringEngine()
        self.layout_grammar = create_layout_grammar()
        
        # Calculate decision variable bounds
        self.placement_bounds = self._calculate_placement_bounds()
        
        # Each module has 4 decision variables: x, y, z, rotation
        n_vars = len(required_modules) * 4
        n_obj = len(config.objectives)
        
        # Define variable bounds
        xl = []  # Lower bounds
        xu = []  # Upper bounds
        
        for _ in required_modules:
            # Position bounds (x, y, z)
            xl.extend([
                self.placement_bounds['min_x'],
                self.placement_bounds['min_y'], 
                self.placement_bounds['min_z']
            ])
            xu.extend([
                self.placement_bounds['max_x'],
                self.placement_bounds['max_y'],
                self.placement_bounds['max_z']
            ])
            
            # Rotation bounds (0-360 degrees)
            xl.append(0.0)
            xu.append(360.0)
        
        super().__init__(
            n_var=n_vars,
            n_obj=n_obj,
            n_constr=0,  # We'll handle constraints through penalty functions
            xl=np.array(xl),
            xu=np.array(xu)
        )
    
    def _calculate_placement_bounds(self) -> Dict[str, float]:
        """Calculate valid placement bounds within the envelope"""
        margin = 0.5  # Safety margin from envelope boundary
        
        envelope_type = self.envelope.type if isinstance(self.envelope.type, str) else self.envelope.type.value
        if envelope_type == "cylinder":
            radius = self.envelope.params['radius'] - margin
            length = self.envelope.params['length'] - 2 * margin
            return {
                'min_x': -radius,
                'max_x': radius,
                'min_y': -radius,
                'max_y': radius,
                'min_z': -length/2,
                'max_z': length/2
            }
        
        elif envelope_type == "box":
            return {
                'min_x': -self.envelope.params['width']/2 + margin,
                'max_x': self.envelope.params['width']/2 - margin,
                'min_y': -self.envelope.params['height']/2 + margin,
                'max_y': self.envelope.params['height']/2 - margin,
                'min_z': -self.envelope.params['depth']/2 + margin,
                'max_z': self.envelope.params['depth']/2 - margin
            }
        
        elif envelope_type == "torus":
            major_radius = self.envelope.params['major_radius'] - margin
            return {
                'min_x': -major_radius,
                'max_x': major_radius,
                'min_y': -major_radius,
                'max_y': major_radius,
                'min_z': -self.envelope.params['minor_radius'] + margin,
                'max_z': self.envelope.params['minor_radius'] - margin
            }
        
        else:
            # Default bounds for freeform
            return {
                'min_x': -5.0, 'max_x': 5.0,
                'min_y': -5.0, 'max_y': 5.0,
                'min_z': -5.0, 'max_z': 5.0
            }
    
    def _decode_solution(self, x: np.ndarray) -> List[ModulePlacement]:
        """Convert decision variables to module placements"""
        placements = []
        
        for i, module_def in enumerate(self.required_modules):
            # Extract variables for this module
            start_idx = i * 4
            pos_x = x[start_idx]
            pos_y = x[start_idx + 1]
            pos_z = x[start_idx + 2]
            rotation = x[start_idx + 3]
            
            # Create module placement
            module_type_str = module_def.spec.type if isinstance(module_def.spec.type, str) else module_def.spec.type.value
            module_id = f"{module_type_str}_{i+1:03d}_{uuid.uuid4().hex[:8]}"
            
            placement = ModulePlacement(
                module_id=module_id,
                type=module_def.spec.type,
                position=[pos_x, pos_y, pos_z],
                rotation_deg=rotation,
                connections=[]
            )
            
            placements.append(placement)
        
        return placements
    
    def _evaluate_objectives(self, placements: List[ModulePlacement]) -> Tuple[np.ndarray, float]:
        """
        Evaluate objectives for a given layout.
        
        Returns:
            objectives: Array of objective values (to be minimized)
            penalty: Constraint violation penalty
        """
        try:
            # Check constraints and calculate penalty
            penalty = self._calculate_constraint_penalty(placements)
            
            # If severe constraint violations, return high penalty objectives
            if penalty > 1000:
                return np.full(len(self.config.objectives), 1e6), penalty
            
            # Calculate performance metrics
            metrics = asyncio.run(
                self.scoring_engine.calculate_metrics(
                    placements, self.envelope, self.mission_params
                )
            )
            
            # Convert metrics to objectives (all objectives are minimized)
            objectives = []
            
            for obj_type in self.config.objectives:
                if obj_type == OptimizationObjective.TRANSIT_TIME:
                    # Minimize transit time
                    objectives.append(metrics.mean_transit_time)
                
                elif obj_type == OptimizationObjective.MASS:
                    # Minimize total mass
                    objectives.append(metrics.mass_total)
                
                elif obj_type == OptimizationObjective.POWER:
                    # Minimize power consumption
                    objectives.append(metrics.power_budget)
                
                elif obj_type == OptimizationObjective.SAFETY:
                    # Minimize safety risk (maximize safety score)
                    safety_score = metrics.safety_score or 0.5
                    objectives.append(1.0 - safety_score)  # Convert to minimization
                
                elif obj_type == OptimizationObjective.THERMAL:
                    # Minimize thermal risk (maximize thermal margin)
                    objectives.append(1.0 - max(0, metrics.thermal_margin))
                
                elif obj_type == OptimizationObjective.LSS_MARGIN:
                    # Minimize LSS risk (maximize LSS margin)
                    objectives.append(1.0 - max(0, metrics.lss_margin))
                
                elif obj_type == OptimizationObjective.VOLUME_EFFICIENCY:
                    # Minimize volume inefficiency
                    volume_util = metrics.volume_utilization or 0.5
                    objectives.append(1.0 - volume_util)
            
            # Add penalty to objectives
            objectives = np.array(objectives) + penalty
            
            return objectives, penalty
        
        except Exception as e:
            logger.warning(f"Error evaluating objectives: {str(e)}")
            # Return high penalty for failed evaluations
            return np.full(len(self.config.objectives), 1e6), 1e6
    
    def _calculate_constraint_penalty(self, placements: List[ModulePlacement]) -> float:
        """Calculate penalty for constraint violations"""
        penalty = 0.0
        
        try:
            # Check collision constraints
            collision_count = 0
            for i, placement in enumerate(placements):
                module_def = self.required_modules[i]
                other_placements = placements[:i] + placements[i+1:]
                
                if self.collision_detector.check_module_collisions(
                    placement, module_def, other_placements, min_clearance=0.6
                ):
                    collision_count += 1
            
            # Heavy penalty for collisions
            penalty += collision_count * 1000
            
            # Check connectivity constraints
            if not self.connectivity_validator.validate_layout_connectivity(placements):
                penalty += 500  # Moderate penalty for connectivity issues
            
            # Check envelope bounds
            bounds_violations = 0
            for i, placement in enumerate(placements):
                module_def = self.required_modules[i]
                if not self._is_within_envelope_bounds(placement, module_def):
                    bounds_violations += 1
            
            penalty += bounds_violations * 200
            
            # Add layout grammar penalty
            try:
                grammar_evaluation = self.layout_grammar.evaluate_layout(
                    placements, self.mission_params
                )
                penalty += grammar_evaluation.total_penalty
                
                # Extra penalty for critical violations
                penalty += grammar_evaluation.critical_violations * 2000
                
            except Exception as e:
                logger.warning(f"Error evaluating layout grammar: {str(e)}")
                penalty += 100  # Small penalty for grammar evaluation errors
            
            return penalty
        
        except Exception as e:
            logger.warning(f"Error calculating constraint penalty: {str(e)}")
            return 1000  # High penalty for evaluation errors
    
    def _is_within_envelope_bounds(
        self, 
        placement: ModulePlacement, 
        module_def: ModuleDefinition
    ) -> bool:
        """Check if module placement is within envelope bounds"""
        bbox = module_def.spec.bbox_m
        pos = placement.position
        
        envelope_type = self.envelope.type if isinstance(self.envelope.type, str) else self.envelope.type.value
        if envelope_type == "cylinder":
            radius = self.envelope.params['radius']
            length = self.envelope.params['length']
            
            # Check radial constraint
            module_radius = np.sqrt(pos[0]**2 + pos[1]**2) + max(bbox.x, bbox.y) / 2
            if module_radius > radius:
                return False
            
            # Check length constraint
            if abs(pos[2]) + bbox.z / 2 > length / 2:
                return False
            
            return True
        
        elif envelope_type == "box":
            width = self.envelope.params['width']
            height = self.envelope.params['height']
            depth = self.envelope.params['depth']
            
            if (abs(pos[0]) + bbox.x/2 > width/2 or
                abs(pos[1]) + bbox.y/2 > height/2 or
                abs(pos[2]) + bbox.z/2 > depth/2):
                return False
            
            return True
        
        # For other envelope types, assume valid for now
        return True
    
    def _evaluate(self, x, out, *args, **kwargs):
        """Pymoo evaluation function"""
        n_solutions = x.shape[0]
        objectives = np.zeros((n_solutions, len(self.config.objectives)))
        
        for i in range(n_solutions):
            placements = self._decode_solution(x[i])
            obj_values, penalty = self._evaluate_objectives(placements)
            objectives[i] = obj_values
        
        out["F"] = objectives


class NSGA2Optimizer:
    """
    NSGA-II Multi-Objective Optimization Engine for habitat layouts.
    
    This class implements the NSGA-II genetic algorithm to optimize habitat
    layouts across multiple objectives including transit time, mass, power,
    and safety considerations.
    """
    
    def __init__(self, config: OptimizationConfig = None):
        self.config = config or OptimizationConfig()
        self.module_library = get_module_library()
        
        # Thread pool for parallel evaluation
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def optimize_layout(
        self,
        envelope: EnvelopeSpec,
        mission_params: MissionParameters,
        required_modules: List[ModuleDefinition] = None
    ) -> OptimizationResult:
        """
        Optimize habitat layout using NSGA-II algorithm.
        
        Args:
            envelope: Habitat envelope specification
            mission_params: Mission parameters and constraints
            required_modules: List of required modules (auto-selected if None)
            
        Returns:
            OptimizationResult containing Pareto-optimal layouts
        """
        logger.info(f"Starting NSGA-II optimization for envelope {envelope.id}")
        
        # Select required modules if not provided
        if required_modules is None:
            required_modules = self._select_required_modules(mission_params)
        
        logger.info(f"Optimizing layout with {len(required_modules)} modules")
        
        # Create optimization problem
        problem = HabitatLayoutProblem(
            envelope, mission_params, required_modules, self.config
        )
        
        # Configure NSGA-II algorithm
        algorithm = NSGA2(
            pop_size=self.config.population_size,
            sampling=FloatRandomSampling(),
            crossover=SBX(prob=self.config.crossover_prob, eta=self.config.crossover_eta),
            mutation=PM(prob=self.config.mutation_prob, eta=self.config.mutation_eta),
            eliminate_duplicates=True
        )
        
        # Run optimization
        import time
        start_time = time.time()
        
        try:
            # Run optimization in thread pool to avoid blocking
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._run_optimization,
                problem,
                algorithm
            )
            
            optimization_time = time.time() - start_time
            
            # Convert results to layout specifications
            pareto_layouts = await self._convert_results_to_layouts(
                result, problem, envelope, mission_params
            )
            
            # Select best layout based on weighted objectives
            best_layout = self._select_best_layout(pareto_layouts, mission_params)
            
            # Extract convergence history
            convergence_history = self._extract_convergence_history(result)
            
            optimization_result = OptimizationResult(
                pareto_layouts=pareto_layouts,
                best_layout=best_layout,
                convergence_history=convergence_history,
                generation_count=self.config.generations,
                evaluation_count=result.algorithm.evaluator.n_eval,
                optimization_time=optimization_time,
                config=self.config
            )
            
            logger.info(
                f"Optimization completed in {optimization_time:.2f}s, "
                f"found {len(pareto_layouts)} Pareto-optimal solutions"
            )
            
            return optimization_result
        
        except Exception as e:
            logger.error(f"Optimization failed: {str(e)}")
            raise
    
    def _run_optimization(self, problem: HabitatLayoutProblem, algorithm: NSGA2) -> Result:
        """Run the optimization algorithm (blocking operation)"""
        termination = ('n_gen', self.config.generations)
        
        result = minimize(
            problem,
            algorithm,
            termination,
            verbose=False,
            save_history=True
        )
        
        return result
    
    async def _convert_results_to_layouts(
        self,
        result: Result,
        problem: HabitatLayoutProblem,
        envelope: EnvelopeSpec,
        mission_params: MissionParameters
    ) -> List[LayoutSpec]:
        """Convert optimization results to LayoutSpec objects"""
        layouts = []
        
        # Get Pareto-optimal solutions
        pareto_solutions = result.X
        pareto_objectives = result.F
        
        for i, (solution, objectives) in enumerate(zip(pareto_solutions, pareto_objectives)):
            try:
                # Decode solution to module placements
                placements = problem._decode_solution(solution)
                
                # Calculate detailed metrics
                scoring_engine = EnhancedScoringEngine()
                metrics = await scoring_engine.calculate_metrics(
                    placements, envelope, mission_params
                )
                
                # Generate explainability
                explainability = self._generate_explainability(
                    placements, metrics, objectives, mission_params
                )
                
                # Create layout specification
                layout_id = f"nsga2_layout_{i+1:03d}_{uuid.uuid4().hex[:8]}"
                
                layout = LayoutSpec(
                    layout_id=layout_id,
                    envelope_id=envelope.id,
                    modules=placements,
                    kpis=metrics,
                    explainability=explainability,
                    metadata=LayoutMetadata(
                        name=f"NSGA-II Optimized Layout {i+1}",
                        generation_params={
                            "algorithm": "nsga2",
                            "population_size": self.config.population_size,
                            "generations": self.config.generations,
                            "objectives": [obj.value for obj in self.config.objectives],
                            "pareto_rank": i + 1
                        }
                    )
                )
                
                layouts.append(layout)
            
            except Exception as e:
                logger.warning(f"Failed to convert solution {i} to layout: {str(e)}")
                continue
        
        return layouts
    
    def _select_best_layout(
        self, 
        layouts: List[LayoutSpec], 
        mission_params: MissionParameters
    ) -> LayoutSpec:
        """Select the best layout based on mission priority weights"""
        if not layouts:
            raise ValueError("No valid layouts to select from")
        
        best_layout = layouts[0]
        best_score = float('-inf')
        
        for layout in layouts:
            # Calculate weighted score based on mission priorities
            score = self._calculate_weighted_score(layout.kpis, mission_params)
            
            if score > best_score:
                best_score = score
                best_layout = layout
        
        return best_layout
    
    def _calculate_weighted_score(
        self, 
        metrics: PerformanceMetrics, 
        mission_params: MissionParameters
    ) -> float:
        """Calculate weighted performance score"""
        weights = mission_params.priority_weights
        
        # Normalize metrics to 0-1 scale (higher is better)
        transit_score = max(0, 1 - (metrics.mean_transit_time / 300))  # 5-minute baseline
        safety_score = metrics.safety_score or 0.5
        efficiency_score = metrics.efficiency_score or 0.5
        
        # Mass and power scores (lower is better, so invert)
        mass_score = max(0, 1 - (metrics.mass_total / 50000))  # 50-ton baseline
        power_score = max(0, 1 - (metrics.power_budget / 10000))  # 10kW baseline
        
        # Calculate weighted sum
        score = (
            weights.get("safety", 0.3) * safety_score +
            weights.get("efficiency", 0.25) * efficiency_score +
            weights.get("mass", 0.2) * mass_score +
            weights.get("power", 0.15) * power_score +
            weights.get("comfort", 0.1) * transit_score
        )
        
        return score
    
    def _extract_convergence_history(self, result: Result) -> List[float]:
        """Extract convergence history from optimization result"""
        if not hasattr(result, 'history') or not result.history:
            return []
        
        convergence = []
        for generation in result.history:
            if hasattr(generation, 'opt') and generation.opt is not None:
                # Use hypervolume or average objective as convergence metric
                objectives = generation.opt.get("F")
                if objectives is not None and len(objectives) > 0:
                    # Use average of first objective as convergence metric
                    avg_objective = np.mean(objectives[:, 0])
                    convergence.append(float(avg_objective))
        
        return convergence
    
    def _select_required_modules(self, mission_params: MissionParameters) -> List[ModuleDefinition]:
        """Select required modules based on mission parameters"""
        required_modules = []
        crew_size = mission_params.crew_size
        
        # Essential modules for any habitat
        # Sleep quarters (one per crew member)
        sleep_modules = self.module_library.get_modules_by_type(ModuleType.SLEEP_QUARTER)
        if sleep_modules:
            for i in range(crew_size):
                required_modules.append(sleep_modules[0])
        
        # Galley (one for up to 6 crew, two for larger crews)
        galley_modules = self.module_library.get_modules_by_type(ModuleType.GALLEY)
        if galley_modules:
            galley_count = 1 if crew_size <= 6 else 2
            for i in range(galley_count):
                required_modules.append(galley_modules[0])
        
        # Airlock (at least one, two for larger habitats)
        airlock_modules = self.module_library.get_modules_by_type(ModuleType.AIRLOCK)
        if airlock_modules:
            airlock_count = 1 if crew_size <= 4 else 2
            for i in range(airlock_count):
                required_modules.append(airlock_modules[0])
        
        # Mechanical/ECLSS (one per 4 crew members)
        mechanical_modules = self.module_library.get_modules_by_type(ModuleType.MECHANICAL)
        if mechanical_modules:
            mechanical_count = max(1, (crew_size + 3) // 4)
            for i in range(mechanical_count):
                required_modules.append(mechanical_modules[0])
        
        # Medical (one for any crew size)
        medical_modules = self.module_library.get_modules_by_type(ModuleType.MEDICAL)
        if medical_modules:
            required_modules.append(medical_modules[0])
        
        # Laboratory (for missions longer than 30 days)
        if mission_params.duration_days > 30:
            lab_modules = self.module_library.get_modules_by_type(ModuleType.LABORATORY)
            if lab_modules:
                required_modules.append(lab_modules[0])
        
        # Exercise (for missions longer than 14 days)
        if mission_params.duration_days > 14:
            exercise_modules = self.module_library.get_modules_by_type(ModuleType.EXERCISE)
            if exercise_modules:
                required_modules.append(exercise_modules[0])
        
        # Storage (scale with crew size and duration)
        storage_modules = self.module_library.get_modules_by_type(ModuleType.STORAGE)
        if storage_modules:
            storage_count = max(1, crew_size // 2)
            for i in range(storage_count):
                required_modules.append(storage_modules[0])
        
        logger.info(f"Selected {len(required_modules)} required modules for optimization")
        return required_modules
    
    def _generate_explainability(
        self,
        placements: List[ModulePlacement],
        metrics: PerformanceMetrics,
        objectives: np.ndarray,
        mission_params: MissionParameters
    ) -> str:
        """Generate natural language explanation for optimized layout"""
        explanations = []
        
        # Analyze optimization objectives
        obj_names = [obj.value for obj in self.config.objectives]
        
        if OptimizationObjective.TRANSIT_TIME in self.config.objectives:
            if metrics.mean_transit_time < 60:
                explanations.append("Layout optimized for minimal crew transit times")
            elif metrics.mean_transit_time > 120:
                explanations.append("Layout balances transit efficiency with other objectives")
        
        if OptimizationObjective.SAFETY in self.config.objectives:
            safety_score = metrics.safety_score or 0.5
            if safety_score > 0.8:
                explanations.append("High safety score achieved through optimal module placement")
            elif safety_score < 0.6:
                explanations.append("Safety considerations balanced against other mission priorities")
        
        if OptimizationObjective.MASS in self.config.objectives:
            explanations.append("Mass optimization considered in multi-objective tradeoff")
        
        if OptimizationObjective.POWER in self.config.objectives:
            explanations.append("Power efficiency integrated into layout optimization")
        
        # Mission-specific considerations
        priority_weights = mission_params.priority_weights
        max_priority = max(priority_weights.values())
        top_priority = [k for k, v in priority_weights.items() if v == max_priority][0]
        
        if top_priority == "safety":
            explanations.append("Layout prioritizes crew safety as primary mission objective")
        elif top_priority == "efficiency":
            explanations.append("Operational efficiency emphasized in layout optimization")
        elif top_priority == "mass":
            explanations.append("Mass minimization drives layout configuration")
        
        # Pareto optimality explanation
        explanations.append("Solution represents Pareto-optimal tradeoff among competing objectives")
        
        return ". ".join(explanations) + "."


# Factory function for easy instantiation
def create_nsga2_optimizer(
    population_size: int = 50,
    generations: int = 100,
    objectives: List[OptimizationObjective] = None
) -> NSGA2Optimizer:
    """Create NSGA-II optimizer with specified parameters"""
    config = OptimizationConfig(
        population_size=population_size,
        generations=generations,
        objectives=objectives
    )
    return NSGA2Optimizer(config)