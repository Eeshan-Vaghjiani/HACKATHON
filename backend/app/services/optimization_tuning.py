"""
Optimization Parameter Tuning Interface for NSGA-II

This module provides tools for tuning NSGA-II optimization parameters
for different mission scenarios and performance requirements.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import json
from pathlib import Path

from app.models.base import MissionParameters, EnvelopeSpec
from app.services.nsga2_optimizer import (
    OptimizationConfig, OptimizationObjective, NSGA2Optimizer, OptimizationResult
)

logger = logging.getLogger(__name__)


class MissionScenario(str, Enum):
    """Predefined mission scenarios with different optimization requirements"""
    SHORT_TERM_RESEARCH = "short_term_research"  # < 30 days, research focus
    LONG_TERM_HABITATION = "long_term_habitation"  # > 180 days, comfort focus
    EMERGENCY_SHELTER = "emergency_shelter"  # Safety-critical, minimal resources
    DEEP_SPACE_MISSION = "deep_space_mission"  # Mass-critical, long duration
    LUNAR_SURFACE = "lunar_surface"  # Specific environmental constraints
    MARS_SURFACE = "mars_surface"  # Extended mission, resource constraints


@dataclass
class TuningParameters:
    """Parameters for optimization tuning"""
    population_size_range: Tuple[int, int] = (20, 100)
    generations_range: Tuple[int, int] = (50, 200)
    crossover_prob_range: Tuple[float, float] = (0.7, 0.95)
    mutation_prob_range: Tuple[float, float] = (0.05, 0.2)
    crossover_eta_range: Tuple[float, float] = (10.0, 30.0)
    mutation_eta_range: Tuple[float, float] = (15.0, 25.0)


@dataclass
class ScenarioConfig:
    """Configuration for a specific mission scenario"""
    name: str
    description: str
    objectives: List[OptimizationObjective]
    objective_weights: Dict[OptimizationObjective, float]
    optimization_config: OptimizationConfig
    mission_constraints: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'description': self.description,
            'objectives': [obj.value for obj in self.objectives],
            'objective_weights': {obj.value: weight for obj, weight in self.objective_weights.items()},
            'optimization_config': {
                'population_size': self.optimization_config.population_size,
                'generations': self.optimization_config.generations,
                'crossover_prob': self.optimization_config.crossover_prob,
                'mutation_prob': self.optimization_config.mutation_prob,
                'crossover_eta': self.optimization_config.crossover_eta,
                'mutation_eta': self.optimization_config.mutation_eta
            },
            'mission_constraints': self.mission_constraints
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScenarioConfig':
        """Create from dictionary"""
        objectives = [OptimizationObjective(obj) for obj in data['objectives']]
        objective_weights = {
            OptimizationObjective(obj): weight 
            for obj, weight in data['objective_weights'].items()
        }
        
        config_data = data['optimization_config']
        optimization_config = OptimizationConfig(
            population_size=config_data['population_size'],
            generations=config_data['generations'],
            crossover_prob=config_data['crossover_prob'],
            mutation_prob=config_data['mutation_prob'],
            crossover_eta=config_data['crossover_eta'],
            mutation_eta=config_data['mutation_eta'],
            objectives=objectives,
            objective_weights=objective_weights
        )
        
        return cls(
            name=data['name'],
            description=data['description'],
            objectives=objectives,
            objective_weights=objective_weights,
            optimization_config=optimization_config,
            mission_constraints=data.get('mission_constraints', {})
        )


class OptimizationTuner:
    """
    Parameter tuning interface for NSGA-II optimization.
    
    Provides predefined configurations for different mission scenarios
    and tools for custom parameter tuning.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("optimization_configs.json")
        self.scenario_configs: Dict[MissionScenario, ScenarioConfig] = {}
        
        # Initialize with default scenario configurations
        self._initialize_default_scenarios()
        
        # Load custom configurations if available
        if self.config_path.exists():
            self.load_configurations()
    
    def _initialize_default_scenarios(self):
        """Initialize default optimization configurations for different scenarios"""
        
        # Short-term research mission (< 30 days)
        short_term_config = ScenarioConfig(
            name="Short-term Research Mission",
            description="Optimized for research productivity and crew efficiency in short missions",
            objectives=[
                OptimizationObjective.TRANSIT_TIME,
                OptimizationObjective.POWER,
                OptimizationObjective.SAFETY
            ],
            objective_weights={
                OptimizationObjective.TRANSIT_TIME: 0.4,
                OptimizationObjective.POWER: 0.3,
                OptimizationObjective.SAFETY: 0.3
            },
            optimization_config=OptimizationConfig(
                population_size=40,
                generations=75,
                crossover_prob=0.85,
                mutation_prob=0.1,
                crossover_eta=20.0,
                mutation_eta=20.0
            ),
            mission_constraints={
                'max_duration_days': 30,
                'research_priority': True,
                'mass_constraint_relaxed': True
            }
        )
        
        # Long-term habitation (> 180 days)
        long_term_config = ScenarioConfig(
            name="Long-term Habitation Mission",
            description="Optimized for crew comfort and psychological well-being in extended missions",
            objectives=[
                OptimizationObjective.TRANSIT_TIME,
                OptimizationObjective.SAFETY,
                OptimizationObjective.VOLUME_EFFICIENCY,
                OptimizationObjective.MASS
            ],
            objective_weights={
                OptimizationObjective.TRANSIT_TIME: 0.3,
                OptimizationObjective.SAFETY: 0.35,
                OptimizationObjective.VOLUME_EFFICIENCY: 0.2,
                OptimizationObjective.MASS: 0.15
            },
            optimization_config=OptimizationConfig(
                population_size=60,
                generations=120,
                crossover_prob=0.9,
                mutation_prob=0.08,
                crossover_eta=15.0,
                mutation_eta=22.0
            ),
            mission_constraints={
                'min_duration_days': 180,
                'comfort_priority': True,
                'psychological_factors': True
            }
        )
        
        # Emergency shelter
        emergency_config = ScenarioConfig(
            name="Emergency Shelter",
            description="Safety-critical configuration for emergency scenarios with minimal resources",
            objectives=[
                OptimizationObjective.SAFETY,
                OptimizationObjective.LSS_MARGIN,
                OptimizationObjective.TRANSIT_TIME
            ],
            objective_weights={
                OptimizationObjective.SAFETY: 0.5,
                OptimizationObjective.LSS_MARGIN: 0.3,
                OptimizationObjective.TRANSIT_TIME: 0.2
            },
            optimization_config=OptimizationConfig(
                population_size=30,
                generations=60,
                crossover_prob=0.8,
                mutation_prob=0.15,
                crossover_eta=25.0,
                mutation_eta=18.0
            ),
            mission_constraints={
                'emergency_mode': True,
                'minimal_resources': True,
                'safety_critical': True
            }
        )
        
        # Deep space mission
        deep_space_config = ScenarioConfig(
            name="Deep Space Mission",
            description="Mass-critical optimization for deep space missions with strict launch constraints",
            objectives=[
                OptimizationObjective.MASS,
                OptimizationObjective.POWER,
                OptimizationObjective.SAFETY,
                OptimizationObjective.LSS_MARGIN
            ],
            objective_weights={
                OptimizationObjective.MASS: 0.4,
                OptimizationObjective.POWER: 0.25,
                OptimizationObjective.SAFETY: 0.25,
                OptimizationObjective.LSS_MARGIN: 0.1
            },
            optimization_config=OptimizationConfig(
                population_size=80,
                generations=150,
                crossover_prob=0.92,
                mutation_prob=0.06,
                crossover_eta=12.0,
                mutation_eta=25.0
            ),
            mission_constraints={
                'mass_critical': True,
                'launch_constraints': True,
                'deep_space': True
            }
        )
        
        # Lunar surface mission
        lunar_config = ScenarioConfig(
            name="Lunar Surface Mission",
            description="Optimized for lunar surface operations with specific environmental constraints",
            objectives=[
                OptimizationObjective.SAFETY,
                OptimizationObjective.POWER,
                OptimizationObjective.THERMAL,
                OptimizationObjective.TRANSIT_TIME
            ],
            objective_weights={
                OptimizationObjective.SAFETY: 0.3,
                OptimizationObjective.POWER: 0.25,
                OptimizationObjective.THERMAL: 0.25,
                OptimizationObjective.TRANSIT_TIME: 0.2
            },
            optimization_config=OptimizationConfig(
                population_size=50,
                generations=100,
                crossover_prob=0.88,
                mutation_prob=0.12,
                crossover_eta=18.0,
                mutation_eta=20.0
            ),
            mission_constraints={
                'lunar_environment': True,
                'thermal_extremes': True,
                'dust_mitigation': True
            }
        )
        
        # Mars surface mission
        mars_config = ScenarioConfig(
            name="Mars Surface Mission",
            description="Extended mission optimization for Mars surface operations with resource constraints",
            objectives=[
                OptimizationObjective.MASS,
                OptimizationObjective.SAFETY,
                OptimizationObjective.LSS_MARGIN,
                OptimizationObjective.VOLUME_EFFICIENCY,
                OptimizationObjective.POWER
            ],
            objective_weights={
                OptimizationObjective.MASS: 0.25,
                OptimizationObjective.SAFETY: 0.25,
                OptimizationObjective.LSS_MARGIN: 0.2,
                OptimizationObjective.VOLUME_EFFICIENCY: 0.15,
                OptimizationObjective.POWER: 0.15
            },
            optimization_config=OptimizationConfig(
                population_size=70,
                generations=140,
                crossover_prob=0.9,
                mutation_prob=0.1,
                crossover_eta=16.0,
                mutation_eta=22.0
            ),
            mission_constraints={
                'mars_environment': True,
                'extended_mission': True,
                'resource_constraints': True,
                'dust_storms': True
            }
        )
        
        # Store configurations
        self.scenario_configs = {
            MissionScenario.SHORT_TERM_RESEARCH: short_term_config,
            MissionScenario.LONG_TERM_HABITATION: long_term_config,
            MissionScenario.EMERGENCY_SHELTER: emergency_config,
            MissionScenario.DEEP_SPACE_MISSION: deep_space_config,
            MissionScenario.LUNAR_SURFACE: lunar_config,
            MissionScenario.MARS_SURFACE: mars_config
        }
    
    def get_scenario_config(self, scenario: MissionScenario) -> ScenarioConfig:
        """Get configuration for a specific mission scenario"""
        return self.scenario_configs[scenario]
    
    def get_all_scenarios(self) -> Dict[MissionScenario, ScenarioConfig]:
        """Get all available scenario configurations"""
        return self.scenario_configs.copy()
    
    def recommend_scenario(self, mission_params: MissionParameters) -> MissionScenario:
        """
        Recommend the best scenario configuration based on mission parameters.
        
        Args:
            mission_params: Mission parameters to analyze
            
        Returns:
            Recommended mission scenario
        """
        crew_size = mission_params.crew_size
        duration = mission_params.duration_days
        priorities = mission_params.priority_weights
        
        # Analyze mission characteristics
        is_short_term = duration <= 30
        is_long_term = duration >= 180
        is_safety_critical = priorities.get('safety', 0) > 0.4
        is_mass_critical = priorities.get('mass', 0) > 0.3
        is_research_focused = priorities.get('efficiency', 0) > 0.3
        
        # Decision logic
        if is_safety_critical and (crew_size <= 2 or duration <= 14):
            return MissionScenario.EMERGENCY_SHELTER
        
        elif is_mass_critical and duration >= 365:
            return MissionScenario.DEEP_SPACE_MISSION
        
        elif is_short_term and is_research_focused:
            return MissionScenario.SHORT_TERM_RESEARCH
        
        elif is_long_term:
            return MissionScenario.LONG_TERM_HABITATION
        
        elif duration >= 90 and duration <= 365:
            # Medium-term missions - could be lunar or Mars
            if is_mass_critical:
                return MissionScenario.MARS_SURFACE
            else:
                return MissionScenario.LUNAR_SURFACE
        
        else:
            # Default to short-term research
            return MissionScenario.SHORT_TERM_RESEARCH
    
    def create_custom_config(
        self,
        name: str,
        description: str,
        objectives: List[OptimizationObjective],
        objective_weights: Dict[OptimizationObjective, float],
        tuning_params: Optional[TuningParameters] = None,
        mission_constraints: Optional[Dict[str, Any]] = None
    ) -> ScenarioConfig:
        """
        Create a custom optimization configuration.
        
        Args:
            name: Configuration name
            description: Configuration description
            objectives: List of optimization objectives
            objective_weights: Weights for each objective
            tuning_params: Parameter ranges for tuning
            mission_constraints: Additional mission constraints
            
        Returns:
            Custom scenario configuration
        """
        if tuning_params is None:
            tuning_params = TuningParameters()
        
        if mission_constraints is None:
            mission_constraints = {}
        
        # Validate objective weights
        total_weight = sum(objective_weights.values())
        if abs(total_weight - 1.0) > 0.001:
            # Normalize weights
            objective_weights = {
                obj: weight / total_weight 
                for obj, weight in objective_weights.items()
            }
        
        # Select parameters from ranges (use middle values as defaults)
        optimization_config = OptimizationConfig(
            population_size=int(np.mean(tuning_params.population_size_range)),
            generations=int(np.mean(tuning_params.generations_range)),
            crossover_prob=np.mean(tuning_params.crossover_prob_range),
            mutation_prob=np.mean(tuning_params.mutation_prob_range),
            crossover_eta=np.mean(tuning_params.crossover_eta_range),
            mutation_eta=np.mean(tuning_params.mutation_eta_range),
            objectives=objectives,
            objective_weights=objective_weights
        )
        
        return ScenarioConfig(
            name=name,
            description=description,
            objectives=objectives,
            objective_weights=objective_weights,
            optimization_config=optimization_config,
            mission_constraints=mission_constraints
        )
    
    def tune_parameters(
        self,
        envelope: EnvelopeSpec,
        mission_params: MissionParameters,
        base_config: ScenarioConfig,
        tuning_params: TuningParameters,
        evaluation_budget: int = 5
    ) -> Tuple[ScenarioConfig, List[OptimizationResult]]:
        """
        Tune optimization parameters using grid search or random sampling.
        
        Args:
            envelope: Habitat envelope specification
            mission_params: Mission parameters
            base_config: Base configuration to tune
            tuning_params: Parameter ranges for tuning
            evaluation_budget: Number of parameter combinations to evaluate
            
        Returns:
            Tuple of (best_config, evaluation_results)
        """
        logger.info(f"Starting parameter tuning with budget of {evaluation_budget} evaluations")
        
        # Generate parameter combinations
        param_combinations = self._generate_parameter_combinations(
            tuning_params, evaluation_budget
        )
        
        evaluation_results = []
        best_config = base_config
        best_score = float('-inf')
        
        for i, params in enumerate(param_combinations):
            logger.info(f"Evaluating parameter combination {i+1}/{len(param_combinations)}")
            
            # Create configuration with these parameters
            config = OptimizationConfig(
                population_size=params['population_size'],
                generations=params['generations'],
                crossover_prob=params['crossover_prob'],
                mutation_prob=params['mutation_prob'],
                crossover_eta=params['crossover_eta'],
                mutation_eta=params['mutation_eta'],
                objectives=base_config.objectives,
                objective_weights=base_config.objective_weights
            )
            
            # Run optimization
            optimizer = NSGA2Optimizer(config)
            
            try:
                # Create a new event loop for this optimization
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        optimizer.optimize_layout(envelope, mission_params)
                    )
                finally:
                    loop.close()
                
                evaluation_results.append(result)
                
                # Evaluate configuration quality
                score = self._evaluate_configuration_quality(result)
                
                if score > best_score:
                    best_score = score
                    best_config = ScenarioConfig(
                        name=f"{base_config.name} (Tuned)",
                        description=f"{base_config.description} - Parameter tuned version",
                        objectives=base_config.objectives,
                        objective_weights=base_config.objective_weights,
                        optimization_config=config,
                        mission_constraints=base_config.mission_constraints
                    )
                
                logger.info(f"Configuration score: {score:.3f}")
                
            except Exception as e:
                logger.warning(f"Optimization failed for parameter combination {i+1}: {str(e)}")
                continue
        
        logger.info(f"Parameter tuning completed. Best score: {best_score:.3f}")
        
        return best_config, evaluation_results
    
    def _generate_parameter_combinations(
        self, 
        tuning_params: TuningParameters, 
        budget: int
    ) -> List[Dict[str, Any]]:
        """Generate parameter combinations for tuning"""
        combinations = []
        
        for _ in range(budget):
            combination = {
                'population_size': int(np.random.uniform(*tuning_params.population_size_range)),
                'generations': int(np.random.uniform(*tuning_params.generations_range)),
                'crossover_prob': np.random.uniform(*tuning_params.crossover_prob_range),
                'mutation_prob': np.random.uniform(*tuning_params.mutation_prob_range),
                'crossover_eta': np.random.uniform(*tuning_params.crossover_eta_range),
                'mutation_eta': np.random.uniform(*tuning_params.mutation_eta_range)
            }
            combinations.append(combination)
        
        return combinations
    
    def _evaluate_configuration_quality(self, result: OptimizationResult) -> float:
        """
        Evaluate the quality of an optimization configuration based on results.
        
        Args:
            result: Optimization result to evaluate
            
        Returns:
            Quality score (higher is better)
        """
        # Factors to consider:
        # 1. Number of Pareto-optimal solutions found
        # 2. Quality of best solution
        # 3. Convergence speed
        # 4. Diversity of solutions
        
        pareto_count_score = min(1.0, len(result.pareto_layouts) / 20.0)  # Normalize to 20 solutions
        
        best_solution_score = result.best_layout.kpis.overall_score
        
        # Convergence speed (faster is better, but with diminishing returns)
        convergence_score = 1.0 / (1.0 + result.optimization_time / 60.0)  # Normalize to 1 minute
        
        # Diversity score based on performance spread
        if len(result.pareto_layouts) > 1:
            scores = [layout.kpis.overall_score for layout in result.pareto_layouts]
            diversity_score = np.std(scores)  # Higher std = more diversity
        else:
            diversity_score = 0.0
        
        # Weighted combination
        quality_score = (
            0.3 * pareto_count_score +
            0.4 * best_solution_score +
            0.2 * convergence_score +
            0.1 * diversity_score
        )
        
        return quality_score
    
    def save_configurations(self):
        """Save all scenario configurations to file"""
        try:
            config_data = {
                scenario.value: config.to_dict()
                for scenario, config in self.scenario_configs.items()
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"Saved {len(config_data)} configurations to {self.config_path}")
        
        except Exception as e:
            logger.error(f"Failed to save configurations: {str(e)}")
    
    def load_configurations(self):
        """Load scenario configurations from file"""
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
            
            for scenario_name, config_dict in config_data.items():
                try:
                    scenario = MissionScenario(scenario_name)
                    config = ScenarioConfig.from_dict(config_dict)
                    self.scenario_configs[scenario] = config
                except Exception as e:
                    logger.warning(f"Failed to load configuration for {scenario_name}: {str(e)}")
            
            logger.info(f"Loaded {len(config_data)} configurations from {self.config_path}")
        
        except Exception as e:
            logger.error(f"Failed to load configurations: {str(e)}")
    
    def add_custom_scenario(self, scenario_name: str, config: ScenarioConfig):
        """Add a custom scenario configuration"""
        # Create a custom enum value (for storage purposes)
        custom_scenario = f"custom_{scenario_name.lower().replace(' ', '_')}"
        self.scenario_configs[custom_scenario] = config
        logger.info(f"Added custom scenario: {scenario_name}")
    
    def get_tuning_recommendations(
        self, 
        mission_params: MissionParameters
    ) -> Dict[str, Any]:
        """
        Get parameter tuning recommendations based on mission characteristics.
        
        Args:
            mission_params: Mission parameters to analyze
            
        Returns:
            Dictionary with tuning recommendations
        """
        crew_size = mission_params.crew_size
        duration = mission_params.duration_days
        priorities = mission_params.priority_weights
        
        recommendations = {
            'population_size': 50,  # Default
            'generations': 100,     # Default
            'reasoning': []
        }
        
        # Adjust based on mission complexity
        complexity_factor = 1.0
        
        if crew_size > 6:
            complexity_factor *= 1.2
            recommendations['reasoning'].append("Increased population size for larger crew")
        
        if duration > 365:
            complexity_factor *= 1.15
            recommendations['reasoning'].append("Extended generations for long-duration mission")
        
        # Adjust based on priorities
        if priorities.get('safety', 0) > 0.4:
            complexity_factor *= 1.1
            recommendations['reasoning'].append("Enhanced search for safety-critical mission")
        
        if priorities.get('mass', 0) > 0.3:
            complexity_factor *= 1.05
            recommendations['reasoning'].append("Thorough search for mass-critical mission")
        
        # Apply complexity factor
        recommendations['population_size'] = int(50 * complexity_factor)
        recommendations['generations'] = int(100 * complexity_factor)
        
        # Ensure reasonable bounds
        recommendations['population_size'] = max(20, min(100, recommendations['population_size']))
        recommendations['generations'] = max(50, min(200, recommendations['generations']))
        
        # Add specific parameter recommendations
        recommendations['crossover_prob'] = 0.9 if priorities.get('efficiency', 0) > 0.3 else 0.85
        recommendations['mutation_prob'] = 0.15 if crew_size <= 3 else 0.1
        
        return recommendations


# Factory function for easy instantiation
def create_optimization_tuner(config_path: Optional[Path] = None) -> OptimizationTuner:
    """Create a new optimization tuner instance"""
    return OptimizationTuner(config_path)


# Utility functions
def get_scenario_summary() -> Dict[str, str]:
    """Get a summary of all available mission scenarios"""
    tuner = create_optimization_tuner()
    scenarios = tuner.get_all_scenarios()
    
    return {
        scenario.value: config.description
        for scenario, config in scenarios.items()
    }


async def quick_optimize_for_scenario(
    envelope: EnvelopeSpec,
    mission_params: MissionParameters,
    scenario: MissionScenario
) -> OptimizationResult:
    """
    Quick optimization using a predefined scenario configuration.
    
    Args:
        envelope: Habitat envelope specification
        mission_params: Mission parameters
        scenario: Mission scenario to use
        
    Returns:
        Optimization result
    """
    tuner = create_optimization_tuner()
    config = tuner.get_scenario_config(scenario)
    
    optimizer = NSGA2Optimizer(config.optimization_config)
    
    return await optimizer.optimize_layout(envelope, mission_params)