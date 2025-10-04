#!/usr/bin/env python3
"""
Test script for Optimization Parameter Tuning Interface

This script tests the parameter tuning functionality and scenario configurations.
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.models.base import (
    EnvelopeSpec, EnvelopeType, EnvelopeMetadata, MissionParameters
)
from app.services.optimization_tuning import (
    OptimizationTuner, MissionScenario, TuningParameters,
    create_optimization_tuner, get_scenario_summary, quick_optimize_for_scenario
)
from app.services.nsga2_optimizer import OptimizationObjective


def test_scenario_configurations():
    """Test predefined scenario configurations"""
    print("Testing Scenario Configurations...")
    
    tuner = create_optimization_tuner()
    scenarios = tuner.get_all_scenarios()
    
    print(f"Found {len(scenarios)} predefined scenarios:")
    
    for scenario, config in scenarios.items():
        print(f"\n  {scenario.value}:")
        print(f"    Name: {config.name}")
        print(f"    Description: {config.description}")
        print(f"    Objectives: {[obj.value for obj in config.objectives]}")
        print(f"    Population: {config.optimization_config.population_size}")
        print(f"    Generations: {config.optimization_config.generations}")
        
        # Validate objective weights sum to 1.0
        total_weight = sum(config.objective_weights.values())
        print(f"    Weight sum: {total_weight:.3f}")
        
        if abs(total_weight - 1.0) > 0.001:
            print(f"    ⚠️  Warning: Weights don't sum to 1.0")
        else:
            print(f"    ✅ Weights validated")
    
    return True


def test_scenario_recommendation():
    """Test scenario recommendation logic"""
    print("\n" + "="*60)
    print("Testing Scenario Recommendation...")
    
    tuner = create_optimization_tuner()
    
    # Test different mission profiles
    test_missions = [
        # Short-term research mission
        MissionParameters(
            crew_size=3,
            duration_days=21,
            priority_weights={
                "safety": 0.2,
                "efficiency": 0.4,
                "mass": 0.2,
                "power": 0.1,
                "comfort": 0.1
            }
        ),
        
        # Long-term habitation
        MissionParameters(
            crew_size=6,
            duration_days=365,
            priority_weights={
                "safety": 0.3,
                "efficiency": 0.2,
                "mass": 0.15,
                "power": 0.15,
                "comfort": 0.2
            }
        ),
        
        # Emergency shelter
        MissionParameters(
            crew_size=2,
            duration_days=7,
            priority_weights={
                "safety": 0.6,
                "efficiency": 0.1,
                "mass": 0.1,
                "power": 0.1,
                "comfort": 0.1
            }
        ),
        
        # Deep space mission
        MissionParameters(
            crew_size=4,
            duration_days=730,
            priority_weights={
                "safety": 0.25,
                "efficiency": 0.15,
                "mass": 0.4,
                "power": 0.15,
                "comfort": 0.05
            }
        )
    ]
    
    mission_names = [
        "Short-term Research",
        "Long-term Habitation", 
        "Emergency Shelter",
        "Deep Space Mission"
    ]
    
    for i, (mission, name) in enumerate(zip(test_missions, mission_names)):
        recommended_scenario = tuner.recommend_scenario(mission)
        config = tuner.get_scenario_config(recommended_scenario)
        
        print(f"\n  Mission {i+1}: {name}")
        print(f"    Crew: {mission.crew_size}, Duration: {mission.duration_days} days")
        print(f"    Top priority: {max(mission.priority_weights, key=mission.priority_weights.get)}")
        print(f"    Recommended: {recommended_scenario.value}")
        print(f"    Config: {config.name}")
    
    return True


def test_custom_configuration():
    """Test custom configuration creation"""
    print("\n" + "="*60)
    print("Testing Custom Configuration Creation...")
    
    tuner = create_optimization_tuner()
    
    # Create a custom configuration for a Mars mission
    custom_config = tuner.create_custom_config(
        name="Custom Mars Mission",
        description="Custom optimization for Mars surface operations",
        objectives=[
            OptimizationObjective.MASS,
            OptimizationObjective.SAFETY,
            OptimizationObjective.POWER,
            OptimizationObjective.LSS_MARGIN
        ],
        objective_weights={
            OptimizationObjective.MASS: 0.3,
            OptimizationObjective.SAFETY: 0.3,
            OptimizationObjective.POWER: 0.2,
            OptimizationObjective.LSS_MARGIN: 0.2
        },
        tuning_params=TuningParameters(
            population_size_range=(40, 80),
            generations_range=(80, 150)
        ),
        mission_constraints={
            'mars_environment': True,
            'dust_mitigation': True,
            'resource_scarcity': True
        }
    )
    
    print(f"Created custom configuration:")
    print(f"  Name: {custom_config.name}")
    print(f"  Objectives: {[obj.value for obj in custom_config.objectives]}")
    print(f"  Population: {custom_config.optimization_config.population_size}")
    print(f"  Generations: {custom_config.optimization_config.generations}")
    print(f"  Constraints: {list(custom_config.mission_constraints.keys())}")
    
    # Validate weights
    total_weight = sum(custom_config.objective_weights.values())
    print(f"  Weight sum: {total_weight:.3f}")
    
    if abs(total_weight - 1.0) < 0.001:
        print("  ✅ Custom configuration created successfully")
        return True
    else:
        print("  ❌ Weight validation failed")
        return False


async def test_quick_optimization():
    """Test quick optimization with scenario"""
    print("\n" + "="*60)
    print("Testing Quick Optimization with Scenario...")
    
    # Create a simple test envelope
    envelope = EnvelopeSpec(
        id="test_envelope_tuning",
        type=EnvelopeType.CYLINDER,
        params={"radius": 2.5, "length": 8.0},
        metadata=EnvelopeMetadata(
            name="Small Test Habitat",
            creator="tuning_test"
        )
    )
    
    # Create mission parameters
    mission_params = MissionParameters(
        crew_size=3,
        duration_days=90,
        priority_weights={
            "safety": 0.4,
            "efficiency": 0.3,
            "mass": 0.2,
            "power": 0.1
        }
    )
    
    print(f"Test envelope: {envelope.type} (r={envelope.params['radius']}m, l={envelope.params['length']}m)")
    print(f"Mission: {mission_params.crew_size} crew, {mission_params.duration_days} days")
    
    try:
        # Use lunar surface scenario for testing
        result = await quick_optimize_for_scenario(
            envelope, mission_params, MissionScenario.LUNAR_SURFACE
        )
        
        print(f"\nOptimization completed:")
        print(f"  Scenario: {MissionScenario.LUNAR_SURFACE.value}")
        print(f"  Solutions found: {len(result.pareto_layouts)}")
        print(f"  Best layout: {result.best_layout.layout_id}")
        print(f"  Optimization time: {result.optimization_time:.2f}s")
        print(f"  Best overall score: {result.best_layout.kpis.overall_score:.3f}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Quick optimization failed: {str(e)}")
        return False


def test_tuning_recommendations():
    """Test parameter tuning recommendations"""
    print("\n" + "="*60)
    print("Testing Tuning Recommendations...")
    
    tuner = create_optimization_tuner()
    
    # Test different mission types
    test_cases = [
        ("Small crew, short mission", MissionParameters(
            crew_size=2, duration_days=14,
            priority_weights={"safety": 0.5, "efficiency": 0.3, "mass": 0.1, "power": 0.1}
        )),
        ("Large crew, long mission", MissionParameters(
            crew_size=8, duration_days=500,
            priority_weights={"safety": 0.3, "efficiency": 0.2, "mass": 0.3, "power": 0.2}
        )),
        ("Mass-critical mission", MissionParameters(
            crew_size=4, duration_days=180,
            priority_weights={"safety": 0.2, "efficiency": 0.2, "mass": 0.5, "power": 0.1}
        ))
    ]
    
    for case_name, mission in test_cases:
        recommendations = tuner.get_tuning_recommendations(mission)
        
        print(f"\n  {case_name}:")
        print(f"    Crew: {mission.crew_size}, Duration: {mission.duration_days} days")
        print(f"    Recommended population: {recommendations['population_size']}")
        print(f"    Recommended generations: {recommendations['generations']}")
        print(f"    Crossover prob: {recommendations['crossover_prob']}")
        print(f"    Mutation prob: {recommendations['mutation_prob']}")
        
        if recommendations['reasoning']:
            print(f"    Reasoning: {', '.join(recommendations['reasoning'])}")
    
    return True


def test_scenario_summary():
    """Test scenario summary functionality"""
    print("\n" + "="*60)
    print("Testing Scenario Summary...")
    
    summary = get_scenario_summary()
    
    print(f"Available scenarios ({len(summary)}):")
    for scenario_name, description in summary.items():
        print(f"  {scenario_name}: {description[:80]}...")
    
    return True


async def main():
    """Main test function"""
    print("Optimization Parameter Tuning Interface Test Suite")
    print("="*60)
    
    # Run all tests
    tests = [
        ("Scenario Configurations", test_scenario_configurations),
        ("Scenario Recommendation", test_scenario_recommendation),
        ("Custom Configuration", test_custom_configuration),
        ("Quick Optimization", test_quick_optimization),
        ("Tuning Recommendations", test_tuning_recommendations),
        ("Scenario Summary", test_scenario_summary)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append(result)
            
            if result:
                print(f"✅ {test_name} passed")
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            results.append(False)
    
    # Summary
    print("\n" + "="*60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All {total} tests passed successfully!")
        return 0
    else:
        print(f"❌ {passed}/{total} tests passed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)