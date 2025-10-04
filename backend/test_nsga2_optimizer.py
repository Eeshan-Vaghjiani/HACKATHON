#!/usr/bin/env python3
"""
Test script for NSGA-II Multi-Objective Optimization Engine

This script tests the basic functionality of the NSGA-II optimizer
with a simple habitat layout optimization problem.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.models.base import (
    EnvelopeSpec, EnvelopeType, EnvelopeMetadata, MissionParameters,
    ModuleType
)
from app.services.nsga2_optimizer import (
    NSGA2Optimizer, OptimizationConfig, OptimizationObjective,
    create_nsga2_optimizer
)
from app.models.module_library import get_module_library


async def test_basic_optimization():
    """Test basic NSGA-II optimization functionality"""
    print("Testing NSGA-II Multi-Objective Optimization Engine...")
    
    # Create a simple cylindrical habitat envelope
    envelope = EnvelopeSpec(
        id="test_envelope_001",
        type=EnvelopeType.CYLINDER,
        params={"radius": 3.0, "length": 12.0},
        metadata=EnvelopeMetadata(
            name="Test Cylinder Habitat",
            creator="test_system"
        )
    )
    
    # Create mission parameters
    mission_params = MissionParameters(
        crew_size=4,
        duration_days=180,
        priority_weights={
            "safety": 0.3,
            "efficiency": 0.25,
            "mass": 0.2,
            "power": 0.15,
            "comfort": 0.1
        }
    )
    
    # Create optimizer with small population for testing
    config = OptimizationConfig(
        population_size=20,
        generations=10,
        objectives=[
            OptimizationObjective.TRANSIT_TIME,
            OptimizationObjective.MASS,
            OptimizationObjective.POWER,
            OptimizationObjective.SAFETY
        ]
    )
    
    optimizer = NSGA2Optimizer(config)
    
    envelope_type = envelope.type if isinstance(envelope.type, str) else envelope.type.value
    print(f"Envelope: {envelope_type} (radius={envelope.params['radius']}m, length={envelope.params['length']}m)")
    print(f"Mission: {mission_params.crew_size} crew, {mission_params.duration_days} days")
    print(f"Optimization: {config.population_size} population, {config.generations} generations")
    print(f"Objectives: {[obj.value for obj in config.objectives]}")
    
    try:
        # Run optimization
        print("\nStarting optimization...")
        result = await optimizer.optimize_layout(envelope, mission_params)
        
        print(f"\nOptimization completed successfully!")
        print(f"- Found {len(result.pareto_layouts)} Pareto-optimal solutions")
        print(f"- Best layout: {result.best_layout.layout_id}")
        print(f"- Optimization time: {result.optimization_time:.2f} seconds")
        print(f"- Evaluations: {result.evaluation_count}")
        
        # Display best layout metrics
        best_kpis = result.best_layout.kpis
        print(f"\nBest Layout Performance:")
        print(f"- Transit time: {best_kpis.mean_transit_time:.1f}s")
        print(f"- Egress time: {best_kpis.egress_time:.1f}s")
        print(f"- Total mass: {best_kpis.mass_total:.0f}kg")
        print(f"- Power budget: {best_kpis.power_budget:.0f}W")
        print(f"- Safety score: {best_kpis.safety_score:.3f}")
        print(f"- Overall score: {best_kpis.overall_score:.3f}")
        
        # Display module layout
        print(f"\nModule Layout ({len(result.best_layout.modules)} modules):")
        for i, module in enumerate(result.best_layout.modules):
            pos = module.position
            module_type = module.type if isinstance(module.type, str) else module.type.value
            print(f"  {i+1}. {module_type}: [{pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}] @ {module.rotation_deg:.0f}°")
        
        # Display explainability
        print(f"\nExplanation: {result.best_layout.explainability}")
        
        # Display Pareto front summary
        print(f"\nPareto Front Analysis:")
        for i, layout in enumerate(result.pareto_layouts[:5]):  # Show first 5
            kpis = layout.kpis
            print(f"  Solution {i+1}: Transit={kpis.mean_transit_time:.1f}s, "
                  f"Mass={kpis.mass_total:.0f}kg, Power={kpis.power_budget:.0f}W, "
                  f"Safety={kpis.safety_score:.3f}")
        
        if len(result.pareto_layouts) > 5:
            print(f"  ... and {len(result.pareto_layouts) - 5} more solutions")
        
        return True
        
    except Exception as e:
        print(f"\nOptimization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_pareto_analysis():
    """Test Pareto analysis functionality"""
    print("\n" + "="*60)
    print("Testing Pareto Analysis...")
    
    from app.services.pareto_analysis import create_pareto_analyzer
    
    # Create some mock layouts for testing
    from app.models.base import LayoutSpec, ModulePlacement, PerformanceMetrics, LayoutMetadata
    
    # Create test layouts with different performance characteristics
    test_layouts = []
    
    for i in range(5):
        # Create mock module placements
        modules = [
            ModulePlacement(
                module_id=f"test_module_{j}",
                type=ModuleType.SLEEP_QUARTER,
                position=[j * 2.0, 0.0, 0.0],
                rotation_deg=0.0
            ) for j in range(3)
        ]
        
        # Create performance metrics with different tradeoffs
        metrics = PerformanceMetrics(
            mean_transit_time=30.0 + i * 10.0,  # Increasing transit time
            egress_time=60.0 + i * 5.0,
            mass_total=10000.0 - i * 500.0,  # Decreasing mass (tradeoff)
            power_budget=2000.0 + i * 200.0,
            thermal_margin=0.2 - i * 0.02,
            lss_margin=0.3 - i * 0.01,
            stowage_utilization=0.7 + i * 0.05,
            safety_score=0.9 - i * 0.05
        )
        
        layout = LayoutSpec(
            layout_id=f"test_layout_{i+1:03d}",
            envelope_id="test_envelope_001",
            modules=modules,
            kpis=metrics,
            explainability=f"Test layout {i+1} with specific performance characteristics",
            metadata=LayoutMetadata(name=f"Test Layout {i+1}")
        )
        
        test_layouts.append(layout)
    
    # Analyze with Pareto analyzer
    analyzer = create_pareto_analyzer()
    pareto_fronts = analyzer.analyze_solutions(test_layouts)
    
    print(f"Found {len(pareto_fronts)} Pareto fronts")
    
    for i, front in enumerate(pareto_fronts):
        print(f"  Front {i+1}: {front.size} solutions, hypervolume={front.hypervolume:.3f}")
    
    # Get best compromise solution
    best_compromise = analyzer.get_best_compromise_solution(pareto_fronts)
    if best_compromise:
        print(f"Best compromise solution: {best_compromise.layout_id}")
    
    # Generate tradeoff analysis
    analysis = analyzer.generate_tradeoff_analysis(pareto_fronts)
    print(f"Tradeoff analysis generated with {len(analysis.get('recommendations', []))} recommendations")
    
    return True


async def main():
    """Main test function"""
    print("NSGA-II Multi-Objective Optimization Engine Test Suite")
    print("="*60)
    
    # Test basic optimization
    success1 = await test_basic_optimization()
    
    # Test Pareto analysis
    success2 = await test_pareto_analysis()
    
    print("\n" + "="*60)
    if success1 and success2:
        print("✅ All tests passed successfully!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)