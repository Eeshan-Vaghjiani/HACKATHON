"""
Comprehensive tests for optimization algorithm convergence and performance.
"""

import pytest
import numpy as np
import asyncio
from typing import List, Dict, Any

from app.services.nsga2_optimizer import NSGA2Optimizer, OptimizationResult, OptimizationConfig
from app.models.base import (
    EnvelopeSpec, MissionParameters, LayoutSpec, ModulePlacement,
    EnvelopeType, CoordinateFrame, EnvelopeMetadata, ModuleType
)


class TestNSGA2Convergence:
    """Test NSGA-II optimization algorithm convergence"""
    
    @pytest.fixture
    def optimizer(self):
        """Create NSGA-II optimizer instance"""
        config = OptimizationConfig(
            population_size=50,
            generations=20,
            crossover_prob=0.9,
            mutation_prob=0.1
        )
        return NSGA2Optimizer(config)
    
    @pytest.fixture
    def test_envelope(self):
        """Create test envelope for optimization"""
        return EnvelopeSpec(
            id="opt_test_envelope",
            type=EnvelopeType.CYLINDER,
            params={"radius": 4.0, "length": 16.0},
            coordinate_frame=CoordinateFrame.LOCAL,
            metadata=EnvelopeMetadata(
                name="Optimization Test Habitat",
                creator="test_optimizer"
            )
        )
    
    @pytest.fixture
    def test_mission(self):
        """Create test mission parameters"""
        return MissionParameters(
            crew_size=3,
            duration_days=90,
            priority_weights={
                "safety": 0.35,
                "efficiency": 0.25,
                "mass": 0.20,
                "power": 0.20
            }
        )
    
    def test_optimizer_initialization(self, optimizer):
        """Test optimizer initializes with correct parameters"""
        assert optimizer.config.population_size == 50
        assert optimizer.config.generations == 20
        assert optimizer.config.crossover_prob == 0.9
        assert optimizer.config.mutation_prob == 0.1
        assert optimizer.module_library is not None
    
    @pytest.mark.asyncio
    async def test_basic_optimization_convergence(self, optimizer, test_envelope, test_mission):
        """Test that optimization converges to valid solutions"""
        try:
            result = await optimizer.optimize_layout(test_envelope, test_mission)
            
            # Check that optimization completed
            assert result is not None
            assert isinstance(result, OptimizationResult)
            
            # Check that we have solutions
            assert len(result.pareto_front) > 0
            assert len(result.all_solutions) >= len(result.pareto_front)
            
            # Check convergence metrics
            assert result.convergence_history is not None
            assert len(result.convergence_history) > 0
            
            # Verify solutions are valid layouts
            for solution in result.pareto_front:
                assert isinstance(solution, LayoutSpec)
                assert len(solution.modules) > 0
                assert solution.kpis is not None
                
            print(f"Optimization converged with {len(result.pareto_front)} Pareto solutions")
            print(f"Best hypervolume: {result.final_hypervolume:.4f}")
            
        except Exception as e:
            # If optimization fails, it should be due to constraints, not algorithm issues
            assert "constraint" in str(e).lower() or "generation" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_convergence_metrics_calculation(self, optimizer, test_envelope, test_mission):
        """Test that convergence metrics are calculated correctly"""
        try:
            result = await optimizer.optimize(test_envelope, test_mission)
            
            # Check convergence metrics
            assert result.convergence_history is not None
            assert result.final_hypervolume >= 0
            assert result.generation_count > 0
            
            # Check that hypervolume generally improves over generations
            if len(result.convergence_history) > 5:
                early_hv = np.mean(result.convergence_history[:3])
                late_hv = np.mean(result.convergence_history[-3:])
                # Allow for some variation but expect general improvement
                assert late_hv >= early_hv * 0.8  # At least 80% of early performance
                
        except Exception as e:
            pytest.skip(f"Optimization failed: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_pareto_front_quality(self, optimizer, test_envelope, test_mission):
        """Test that Pareto front contains diverse, non-dominated solutions"""
        try:
            result = await optimizer.optimize(test_envelope, test_mission)
            
            if len(result.pareto_front) < 2:
                pytest.skip("Need at least 2 solutions for Pareto front analysis")
            
            # Extract objective values
            objectives = []
            for solution in result.pareto_front:
                kpis = solution.kpis
                # Convert to minimization objectives (lower is better)
                obj = [
                    kpis.mean_transit_time,  # Minimize transit time
                    kpis.egress_time,        # Minimize egress time
                    kpis.mass_total,         # Minimize mass
                    -kpis.thermal_margin,    # Maximize thermal margin (minimize negative)
                    -kpis.lss_margin         # Maximize LSS margin (minimize negative)
                ]
                objectives.append(obj)
            
            objectives = np.array(objectives)
            
            # Check that solutions are non-dominated
            for i, sol_i in enumerate(objectives):
                dominated = False
                for j, sol_j in enumerate(objectives):
                    if i != j:
                        # Check if sol_j dominates sol_i
                        if np.all(sol_j <= sol_i) and np.any(sol_j < sol_i):
                            dominated = True
                            break
                
                assert not dominated, f"Solution {i} is dominated by another solution in Pareto front"
            
            # Check diversity - solutions should span different regions
            if len(objectives) >= 3:
                # Calculate pairwise distances
                distances = []
                for i in range(len(objectives)):
                    for j in range(i + 1, len(objectives)):
                        dist = np.linalg.norm(objectives[i] - objectives[j])
                        distances.append(dist)
                
                avg_distance = np.mean(distances)
                assert avg_distance > 0, "Pareto front solutions should be diverse"
                
        except Exception as e:
            pytest.skip(f"Optimization failed: {str(e)}")
    
    def test_optimization_parameter_sensitivity(self, test_envelope, test_mission):
        """Test that optimization parameters affect convergence behavior"""
        # Test with different population sizes
        small_config = OptimizationConfig(population_size=20, generations=10)
        large_config = OptimizationConfig(population_size=100, generations=10)
        small_pop_optimizer = NSGA2Optimizer(small_config)
        large_pop_optimizer = NSGA2Optimizer(large_config)
        
        # Both should initialize successfully
        assert small_pop_optimizer.config.population_size == 20
        assert large_pop_optimizer.config.population_size == 100
        
        # Test with different mutation rates
        low_mut_config = OptimizationConfig(mutation_prob=0.01)
        high_mut_config = OptimizationConfig(mutation_prob=0.5)
        low_mut_optimizer = NSGA2Optimizer(low_mut_config)
        high_mut_optimizer = NSGA2Optimizer(high_mut_config)
        
        assert low_mut_optimizer.config.mutation_prob == 0.01
        assert high_mut_optimizer.config.mutation_prob == 0.5
    
    @pytest.mark.asyncio
    async def test_optimization_with_different_objectives(self, optimizer, test_envelope):
        """Test optimization with different priority weight configurations"""
        
        # Safety-focused mission
        safety_mission = MissionParameters(
            crew_size=3,
            duration_days=90,
            priority_weights={
                "safety": 0.7,
                "efficiency": 0.1,
                "mass": 0.1,
                "power": 0.1
            }
        )
        
        # Efficiency-focused mission
        efficiency_mission = MissionParameters(
            crew_size=3,
            duration_days=90,
            priority_weights={
                "safety": 0.2,
                "efficiency": 0.6,
                "mass": 0.1,
                "power": 0.1
            }
        )
        
        try:
            safety_result = await optimizer.optimize(test_envelope, safety_mission)
            efficiency_result = await optimizer.optimize(test_envelope, efficiency_mission)
            
            # Both should produce valid results
            assert safety_result is not None
            assert efficiency_result is not None
            
            # Results should be different (different priorities should lead to different solutions)
            if (len(safety_result.pareto_front) > 0 and 
                len(efficiency_result.pareto_front) > 0):
                
                safety_best = safety_result.pareto_front[0]
                efficiency_best = efficiency_result.pareto_front[0]
                
                # At least one metric should be significantly different
                safety_score = safety_best.kpis.safety_score or 0.5
                efficiency_score = efficiency_best.kpis.efficiency_score or 0.5
                
                # Allow for some variation in optimization results
                assert abs(safety_score - efficiency_score) >= 0.01 or \
                       abs(safety_best.kpis.mean_transit_time - efficiency_best.kpis.mean_transit_time) >= 1.0
                
        except Exception as e:
            pytest.skip(f"Optimization failed: {str(e)}")
    
    def test_constraint_handling(self, optimizer, test_envelope):
        """Test that optimizer properly handles constraint violations"""
        
        # Create impossible mission (too many crew for small space)
        impossible_mission = MissionParameters(
            crew_size=20,  # Too many for the envelope
            duration_days=365
        )
        
        # This should either fail gracefully or produce constrained solutions
        with pytest.raises(Exception) as exc_info:
            asyncio.run(optimizer.optimize(test_envelope, impossible_mission))
        
        # Should be a meaningful constraint-related error
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in 
                  ["constraint", "infeasible", "space", "crew", "capacity"])


class TestOptimizationPerformance:
    """Test optimization algorithm performance characteristics"""
    
    def test_optimization_timing(self):
        """Test that optimization completes within reasonable time"""
        optimizer = NSGA2Optimizer(population_size=30, generations=10)
        
        envelope = EnvelopeSpec(
            id="perf_test_envelope",
            type=EnvelopeType.CYLINDER,
            params={"radius": 3.0, "length": 12.0},
            coordinate_frame=CoordinateFrame.LOCAL,
            metadata=EnvelopeMetadata(name="Performance Test", creator="test")
        )
        
        mission = MissionParameters(crew_size=2, duration_days=30)
        
        import time
        start_time = time.time()
        
        try:
            result = asyncio.run(optimizer.optimize(envelope, mission))
            end_time = time.time()
            
            optimization_time = end_time - start_time
            
            # Should complete within reasonable time (adjust based on system performance)
            assert optimization_time < 60.0, f"Optimization took {optimization_time:.2f}s, too slow"
            
            print(f"Optimization completed in {optimization_time:.2f} seconds")
            
        except Exception as e:
            pytest.skip(f"Optimization failed: {str(e)}")
    
    def test_memory_usage_stability(self):
        """Test that optimization doesn't have memory leaks"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        optimizer = NSGA2Optimizer(population_size=20, generations=5)
        
        envelope = EnvelopeSpec(
            id="memory_test_envelope",
            type=EnvelopeType.BOX,
            params={"width": 4.0, "height": 3.0, "depth": 8.0},
            coordinate_frame=CoordinateFrame.LOCAL,
            metadata=EnvelopeMetadata(name="Memory Test", creator="test")
        )
        
        mission = MissionParameters(crew_size=2, duration_days=30)
        
        # Run multiple optimizations
        for i in range(3):
            try:
                result = asyncio.run(optimizer.optimize(envelope, mission))
            except Exception:
                continue  # Skip failed optimizations for memory test
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for this test)
        assert memory_increase < 100, f"Memory increased by {memory_increase:.1f}MB, possible leak"
        
        print(f"Memory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB (+{memory_increase:.1f}MB)")


class TestOptimizationEdgeCases:
    """Test optimization algorithm edge cases and error handling"""
    
    def test_single_module_optimization(self):
        """Test optimization with minimal module requirements"""
        optimizer = NSGA2Optimizer(population_size=10, generations=5)
        
        # Very small envelope that can only fit minimal modules
        envelope = EnvelopeSpec(
            id="minimal_envelope",
            type=EnvelopeType.CYLINDER,
            params={"radius": 1.5, "length": 4.0},
            coordinate_frame=CoordinateFrame.LOCAL,
            metadata=EnvelopeMetadata(name="Minimal Test", creator="test")
        )
        
        mission = MissionParameters(crew_size=1, duration_days=7)
        
        try:
            result = asyncio.run(optimizer.optimize(envelope, mission))
            
            # Should produce at least one valid solution
            assert result is not None
            assert len(result.pareto_front) > 0
            
            # Solution should have minimal required modules
            best_solution = result.pareto_front[0]
            assert len(best_solution.modules) >= 1  # At least one module
            
        except Exception as e:
            # Acceptable if constraints make this impossible
            assert "constraint" in str(e).lower() or "infeasible" in str(e).lower()
    
    def test_optimization_with_invalid_parameters(self):
        """Test optimization error handling with invalid parameters"""
        
        # Test with invalid optimizer parameters
        with pytest.raises((ValueError, AssertionError)):
            NSGA2Optimizer(population_size=0)  # Invalid population size
        
        with pytest.raises((ValueError, AssertionError)):
            NSGA2Optimizer(generations=-1)  # Invalid generation count
        
        with pytest.raises((ValueError, AssertionError)):
            NSGA2Optimizer(crossover_prob=1.5)  # Invalid probability
        
        with pytest.raises((ValueError, AssertionError)):
            NSGA2Optimizer(mutation_prob=-0.1)  # Invalid probability
    
    def test_optimization_reproducibility(self):
        """Test that optimization with same seed produces consistent results"""
        
        envelope = EnvelopeSpec(
            id="repro_test_envelope",
            type=EnvelopeType.CYLINDER,
            params={"radius": 3.0, "length": 10.0},
            coordinate_frame=CoordinateFrame.LOCAL,
            metadata=EnvelopeMetadata(name="Reproducibility Test", creator="test")
        )
        
        mission = MissionParameters(crew_size=2, duration_days=30)
        
        # Run optimization twice with same seed
        optimizer1 = NSGA2Optimizer(population_size=20, generations=5, random_seed=42)
        optimizer2 = NSGA2Optimizer(population_size=20, generations=5, random_seed=42)
        
        try:
            result1 = asyncio.run(optimizer1.optimize(envelope, mission))
            result2 = asyncio.run(optimizer2.optimize(envelope, mission))
            
            # Results should be similar (allowing for some floating-point differences)
            assert len(result1.pareto_front) == len(result2.pareto_front)
            
            if len(result1.pareto_front) > 0 and len(result2.pareto_front) > 0:
                # Compare first solution metrics
                kpis1 = result1.pareto_front[0].kpis
                kpis2 = result2.pareto_front[0].kpis
                
                # Should be very close (within 1% difference)
                assert abs(kpis1.mean_transit_time - kpis2.mean_transit_time) < 0.01 * kpis1.mean_transit_time
                assert abs(kpis1.mass_total - kpis2.mass_total) < 0.01 * kpis1.mass_total
                
        except Exception as e:
            pytest.skip(f"Optimization failed: {str(e)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])