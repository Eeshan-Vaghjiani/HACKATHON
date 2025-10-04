"""
Comprehensive tests for scoring engine accuracy and consistency.
"""

import pytest
import numpy as np
from typing import List, Dict, Any

from app.services.scoring_engine import ScoringEngine, ScoringError
from app.models.base import (
    LayoutSpec, ModulePlacement, PerformanceMetrics, EnvelopeSpec,
    MissionParameters, ModuleType, EnvelopeType, CoordinateFrame, EnvelopeMetadata
)


class TestScoringEngineAccuracy:
    """Test scoring engine calculation accuracy"""
    
    @pytest.fixture
    def scoring_engine(self):
        """Create scoring engine instance"""
        return ScoringEngine()
    
    @pytest.fixture
    def test_envelope(self):
        """Create test envelope"""
        return EnvelopeSpec(
            id="scoring_test_envelope",
            type=EnvelopeType.CYLINDER,
            params={"radius": 4.0, "length": 16.0},
            coordinate_frame=CoordinateFrame.LOCAL,
            metadata=EnvelopeMetadata(name="Scoring Test", creator="test")
        )
    
    @pytest.fixture
    def test_mission(self):
        """Create test mission parameters"""
        return MissionParameters(
            crew_size=4,
            duration_days=180,
            priority_weights={
                "safety": 0.3,
                "efficiency": 0.3,
                "mass": 0.2,
                "power": 0.2
            }
        )
    
    @pytest.fixture
    def simple_layout(self, test_envelope):
        """Create simple test layout"""
        modules = [
            ModulePlacement(
                module_id="sleep_001",
                type=ModuleType.SLEEP_QUARTER,
                position=[2.0, 0.0, -6.0],
                rotation_deg=0,
                connections=["galley_001"]
            ),
            ModulePlacement(
                module_id="sleep_002",
                type=ModuleType.SLEEP_QUARTER,
                position=[-2.0, 0.0, -6.0],
                rotation_deg=0,
                connections=["galley_001"]
            ),
            ModulePlacement(
                module_id="galley_001",
                type=ModuleType.GALLEY,
                position=[0.0, 0.0, 0.0],
                rotation_deg=0,
                connections=["sleep_001", "sleep_002", "lab_001", "airlock_001"]
            ),
            ModulePlacement(
                module_id="lab_001",
                type=ModuleType.LABORATORY,
                position=[0.0, 0.0, 6.0],
                rotation_deg=0,
                connections=["galley_001", "airlock_001"]
            ),
            ModulePlacement(
                module_id="airlock_001",
                type=ModuleType.AIRLOCK,
                position=[3.0, 0.0, 6.0],
                rotation_deg=90,
                connections=["galley_001", "lab_001"]
            )
        ]
        
        return LayoutSpec(
            layout_id="simple_test_layout",
            envelope_id=test_envelope.id,
            modules=modules,
            kpis=PerformanceMetrics(
                mean_transit_time=0.0,  # Will be calculated
                egress_time=0.0,
                mass_total=0.0,
                power_budget=0.0,
                thermal_margin=0.0,
                lss_margin=0.0,
                stowage_utilization=0.0
            ),
            explainability="Simple test layout for scoring validation"
        )
    
    @pytest.mark.asyncio
    async def test_transit_time_calculation_accuracy(self, scoring_engine, simple_layout, test_mission):
        """Test accuracy of transit time calculations"""
        
        metrics = await scoring_engine.calculate_metrics(simple_layout, test_mission)
        
        # Transit time should be positive and reasonable
        assert metrics.mean_transit_time > 0
        assert metrics.mean_transit_time < 300  # Less than 5 minutes for this simple layout
        
        # Manual verification for known distances
        # Distance from sleep_001 to galley_001 should be ~6m
        # Distance from galley_001 to lab_001 should be ~6m
        # Average walking speed ~1.5 m/s, so transit times should be ~4s and ~4s
        
        # The calculated mean should be reasonable for this layout
        expected_range = (10, 60)  # 10-60 seconds seems reasonable
        assert expected_range[0] <= metrics.mean_transit_time <= expected_range[1]
    
    @pytest.mark.asyncio
    async def test_egress_time_calculation_accuracy(self, scoring_engine, simple_layout, test_mission):
        """Test accuracy of emergency egress time calculations"""
        
        metrics = await scoring_engine.calculate_metrics(simple_layout, test_mission)
        
        # Egress time should be positive and reasonable
        assert metrics.egress_time > 0
        assert metrics.egress_time < 600  # Less than 10 minutes
        
        # For this layout, worst case is from sleep quarters to airlock
        # Distance from sleep_001 to airlock_001 via galley should be calculable
        # sqrt((2-3)^2 + (0-0)^2 + (-6-6)^2) = sqrt(1 + 144) = ~12m direct
        # Via galley: 6m + 6.7m = ~12.7m
        # At emergency speed (~2 m/s), should be ~6-7 seconds
        
        expected_range = (5, 120)  # 5-120 seconds for emergency egress
        assert expected_range[0] <= metrics.egress_time <= expected_range[1]
    
    @pytest.mark.asyncio
    async def test_mass_calculation_accuracy(self, scoring_engine, simple_layout, test_mission):
        """Test accuracy of total mass calculations"""
        
        metrics = await scoring_engine.calculate_metrics(simple_layout, test_mission)
        
        # Mass should be positive
        assert metrics.mass_total > 0
        
        # Manual calculation based on standard module masses
        # Sleep quarters: ~450kg each (2 modules = 900kg)
        # Galley: ~800kg
        # Laboratory: ~1200kg  
        # Airlock: ~600kg
        # Total expected: ~3500kg
        
        expected_range = (2000, 6000)  # 2-6 tons seems reasonable
        assert expected_range[0] <= metrics.mass_total <= expected_range[1]
        
        # Should be close to sum of individual module masses
        # Allow for some variation due to connections, structure, etc.
        base_mass = 450 * 2 + 800 + 1200 + 600  # 3500kg
        assert abs(metrics.mass_total - base_mass) / base_mass < 0.5  # Within 50%
    
    @pytest.mark.asyncio
    async def test_power_calculation_accuracy(self, scoring_engine, simple_layout, test_mission):
        """Test accuracy of power budget calculations"""
        
        metrics = await scoring_engine.calculate_metrics(simple_layout, test_mission)
        
        # Power should be positive
        assert metrics.power_budget > 0
        
        # Manual calculation based on standard module power consumption
        # Sleep quarters: ~75W each (2 modules = 150W)
        # Galley: ~500W
        # Laboratory: ~800W
        # Airlock: ~200W
        # Total expected: ~1650W
        
        expected_range = (1000, 3000)  # 1-3kW seems reasonable
        assert expected_range[0] <= metrics.power_budget <= expected_range[1]
    
    @pytest.mark.asyncio
    async def test_thermal_margin_calculation(self, scoring_engine, simple_layout, test_mission):
        """Test thermal margin calculation accuracy"""
        
        metrics = await scoring_engine.calculate_metrics(simple_layout, test_mission)
        
        # Thermal margin should be a reasonable percentage
        assert -1.0 <= metrics.thermal_margin <= 1.0
        
        # For a well-designed layout, thermal margin should be positive
        # (indicating adequate cooling capacity)
        assert metrics.thermal_margin > -0.5  # Not critically overheated
    
    @pytest.mark.asyncio
    async def test_lss_margin_calculation(self, scoring_engine, simple_layout, test_mission):
        """Test life support systems margin calculation accuracy"""
        
        metrics = await scoring_engine.calculate_metrics(simple_layout, test_mission)
        
        # LSS margin should be a reasonable percentage
        assert -1.0 <= metrics.lss_margin <= 1.0
        
        # For 4 crew members, LSS should be adequate with some margin
        assert metrics.lss_margin > -0.3  # Not critically undersized
    
    @pytest.mark.asyncio
    async def test_stowage_utilization_accuracy(self, scoring_engine, simple_layout, test_mission):
        """Test stowage utilization calculation accuracy"""
        
        metrics = await scoring_engine.calculate_metrics(simple_layout, test_mission)
        
        # Stowage utilization should be non-negative
        assert metrics.stowage_utilization >= 0
        
        # For 4 crew, 180 days, should have reasonable utilization
        # Not overcrowded (>1.0) but not empty (<0.1)
        assert 0.1 <= metrics.stowage_utilization <= 1.5


class TestScoringEngineConsistency:
    """Test scoring engine consistency and repeatability"""
    
    @pytest.fixture
    def scoring_engine(self):
        return ScoringEngine()
    
    @pytest.mark.asyncio
    async def test_calculation_repeatability(self, scoring_engine):
        """Test that identical inputs produce identical outputs"""
        
        # Create identical layouts
        layout1 = self._create_test_layout("layout1")
        layout2 = self._create_test_layout("layout2")  # Same content, different ID
        
        mission = MissionParameters(crew_size=3, duration_days=90)
        
        # Calculate metrics for both
        metrics1 = await scoring_engine.calculate_metrics(layout1, mission)
        metrics2 = await scoring_engine.calculate_metrics(layout2, mission)
        
        # Results should be identical (within floating-point precision)
        assert abs(metrics1.mean_transit_time - metrics2.mean_transit_time) < 1e-6
        assert abs(metrics1.egress_time - metrics2.egress_time) < 1e-6
        assert abs(metrics1.mass_total - metrics2.mass_total) < 1e-6
        assert abs(metrics1.power_budget - metrics2.power_budget) < 1e-6
        assert abs(metrics1.thermal_margin - metrics2.thermal_margin) < 1e-6
        assert abs(metrics1.lss_margin - metrics2.lss_margin) < 1e-6
        assert abs(metrics1.stowage_utilization - metrics2.stowage_utilization) < 1e-6
    
    @pytest.mark.asyncio
    async def test_metric_scaling_consistency(self, scoring_engine):
        """Test that metrics scale consistently with layout changes"""
        
        # Create layouts with different crew sizes
        small_layout = self._create_test_layout("small", crew_modules=2)
        large_layout = self._create_test_layout("large", crew_modules=6)
        
        small_mission = MissionParameters(crew_size=2, duration_days=90)
        large_mission = MissionParameters(crew_size=6, duration_days=90)
        
        small_metrics = await scoring_engine.calculate_metrics(small_layout, small_mission)
        large_metrics = await scoring_engine.calculate_metrics(large_layout, large_mission)
        
        # Mass should scale with number of modules
        assert large_metrics.mass_total > small_metrics.mass_total
        
        # Power should scale with number of modules
        assert large_metrics.power_budget > small_metrics.power_budget
        
        # Stowage utilization should be higher for more crew
        # (assuming same module count per crew ratio)
        if small_layout.module_count / 2 == large_layout.module_count / 6:
            assert large_metrics.stowage_utilization >= small_metrics.stowage_utilization
    
    @pytest.mark.asyncio
    async def test_mission_parameter_sensitivity(self, scoring_engine):
        """Test that metrics respond appropriately to mission parameter changes"""
        
        layout = self._create_test_layout("sensitivity_test")
        
        # Short vs long mission
        short_mission = MissionParameters(crew_size=4, duration_days=30)
        long_mission = MissionParameters(crew_size=4, duration_days=365)
        
        short_metrics = await scoring_engine.calculate_metrics(layout, short_mission)
        long_metrics = await scoring_engine.calculate_metrics(layout, long_mission)
        
        # Stowage utilization should be higher for longer missions
        assert long_metrics.stowage_utilization > short_metrics.stowage_utilization
        
        # LSS margin might be different due to longer operation requirements
        # (Could be lower due to more consumables needed)
    
    def _create_test_layout(self, layout_id: str, crew_modules: int = 4) -> LayoutSpec:
        """Helper to create test layouts with specified number of crew modules"""
        
        modules = []
        
        # Add crew quarters
        for i in range(crew_modules):
            angle = (i / crew_modules) * 2 * np.pi
            x = 2.5 * np.cos(angle)
            y = 2.5 * np.sin(angle)
            
            modules.append(ModulePlacement(
                module_id=f"sleep_{i:03d}",
                type=ModuleType.SLEEP_QUARTER,
                position=[x, y, -4.0],
                rotation_deg=0,
                connections=["galley_001"]
            ))
        
        # Add common modules
        modules.extend([
            ModulePlacement(
                module_id="galley_001",
                type=ModuleType.GALLEY,
                position=[0.0, 0.0, 0.0],
                rotation_deg=0,
                connections=[f"sleep_{i:03d}" for i in range(crew_modules)] + ["lab_001", "airlock_001"]
            ),
            ModulePlacement(
                module_id="lab_001",
                type=ModuleType.LABORATORY,
                position=[0.0, 0.0, 4.0],
                rotation_deg=0,
                connections=["galley_001", "airlock_001"]
            ),
            ModulePlacement(
                module_id="airlock_001",
                type=ModuleType.AIRLOCK,
                position=[3.0, 0.0, 4.0],
                rotation_deg=90,
                connections=["galley_001", "lab_001"]
            )
        ])
        
        return LayoutSpec(
            layout_id=layout_id,
            envelope_id="test_envelope",
            modules=modules,
            kpis=PerformanceMetrics(
                mean_transit_time=0.0,
                egress_time=0.0,
                mass_total=0.0,
                power_budget=0.0,
                thermal_margin=0.0,
                lss_margin=0.0,
                stowage_utilization=0.0
            ),
            explainability=f"Test layout {layout_id} with {crew_modules} crew modules"
        )


class TestScoringEngineEdgeCases:
    """Test scoring engine edge cases and error handling"""
    
    @pytest.fixture
    def scoring_engine(self):
        return ScoringEngine()
    
    @pytest.mark.asyncio
    async def test_empty_layout_handling(self, scoring_engine):
        """Test handling of empty or minimal layouts"""
        
        # Layout with no modules
        empty_layout = LayoutSpec(
            layout_id="empty_layout",
            envelope_id="test_envelope",
            modules=[],
            kpis=PerformanceMetrics(
                mean_transit_time=0.0,
                egress_time=0.0,
                mass_total=0.0,
                power_budget=0.0,
                thermal_margin=0.0,
                lss_margin=0.0,
                stowage_utilization=0.0
            ),
            explainability="Empty layout for testing"
        )
        
        mission = MissionParameters(crew_size=1, duration_days=30)
        
        # Should handle gracefully (either return zeros or raise appropriate error)
        try:
            metrics = await scoring_engine.calculate_metrics(empty_layout, mission)
            
            # If it succeeds, metrics should be zero or indicate no modules
            assert metrics.mass_total == 0
            assert metrics.power_budget == 0
            
        except ScoringError as e:
            # Acceptable to raise error for empty layout
            assert "empty" in str(e).lower() or "no modules" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_disconnected_layout_handling(self, scoring_engine):
        """Test handling of layouts with disconnected modules"""
        
        # Layout with disconnected modules
        disconnected_layout = LayoutSpec(
            layout_id="disconnected_layout",
            envelope_id="test_envelope",
            modules=[
                ModulePlacement(
                    module_id="module1",
                    type=ModuleType.SLEEP_QUARTER,
                    position=[0.0, 0.0, 0.0],
                    rotation_deg=0,
                    connections=[]  # No connections
                ),
                ModulePlacement(
                    module_id="module2",
                    type=ModuleType.GALLEY,
                    position=[10.0, 0.0, 0.0],  # Far away
                    rotation_deg=0,
                    connections=[]  # No connections
                )
            ],
            kpis=PerformanceMetrics(
                mean_transit_time=0.0,
                egress_time=0.0,
                mass_total=0.0,
                power_budget=0.0,
                thermal_margin=0.0,
                lss_margin=0.0,
                stowage_utilization=0.0
            ),
            explainability="Disconnected layout for testing"
        )
        
        mission = MissionParameters(crew_size=2, duration_days=30)
        
        try:
            metrics = await scoring_engine.calculate_metrics(disconnected_layout, mission)
            
            # Transit time should be very high or infinite for disconnected modules
            assert metrics.mean_transit_time > 1000 or metrics.mean_transit_time == float('inf')
            
        except ScoringError as e:
            # Acceptable to raise error for disconnected layout
            assert "disconnect" in str(e).lower() or "path" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_extreme_parameter_handling(self, scoring_engine):
        """Test handling of extreme mission parameters"""
        
        layout = LayoutSpec(
            layout_id="extreme_test_layout",
            envelope_id="test_envelope",
            modules=[
                ModulePlacement(
                    module_id="airlock_001",
                    type=ModuleType.AIRLOCK,
                    position=[0.0, 0.0, 0.0],
                    rotation_deg=0,
                    connections=[]
                )
            ],
            kpis=PerformanceMetrics(
                mean_transit_time=0.0,
                egress_time=0.0,
                mass_total=0.0,
                power_budget=0.0,
                thermal_margin=0.0,
                lss_margin=0.0,
                stowage_utilization=0.0
            ),
            explainability="Extreme parameter test layout"
        )
        
        # Extreme mission: many crew, very long duration
        extreme_mission = MissionParameters(
            crew_size=100,
            duration_days=3650  # 10 years
        )
        
        try:
            metrics = await scoring_engine.calculate_metrics(layout, extreme_mission)
            
            # Should handle extreme values gracefully
            assert not np.isnan(metrics.stowage_utilization)
            assert not np.isinf(metrics.lss_margin) or metrics.lss_margin == float('-inf')
            
        except ScoringError as e:
            # Acceptable to raise error for impossible scenarios
            assert any(keyword in str(e).lower() for keyword in 
                      ["extreme", "impossible", "capacity", "overflow"])
    
    @pytest.mark.asyncio
    async def test_numerical_stability(self, scoring_engine):
        """Test numerical stability with very small or large values"""
        
        # Layout with modules at very small distances
        close_layout = LayoutSpec(
            layout_id="close_layout",
            envelope_id="test_envelope",
            modules=[
                ModulePlacement(
                    module_id="module1",
                    type=ModuleType.SLEEP_QUARTER,
                    position=[0.0, 0.0, 0.0],
                    rotation_deg=0,
                    connections=["module2"]
                ),
                ModulePlacement(
                    module_id="module2",
                    type=ModuleType.GALLEY,
                    position=[0.001, 0.0, 0.0],  # 1mm away
                    rotation_deg=0,
                    connections=["module1"]
                )
            ],
            kpis=PerformanceMetrics(
                mean_transit_time=0.0,
                egress_time=0.0,
                mass_total=0.0,
                power_budget=0.0,
                thermal_margin=0.0,
                lss_margin=0.0,
                stowage_utilization=0.0
            ),
            explainability="Close modules for numerical stability testing"
        )
        
        mission = MissionParameters(crew_size=1, duration_days=1)
        
        metrics = await scoring_engine.calculate_metrics(close_layout, mission)
        
        # Should handle very small distances without numerical issues
        assert not np.isnan(metrics.mean_transit_time)
        assert not np.isinf(metrics.mean_transit_time)
        assert metrics.mean_transit_time >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])