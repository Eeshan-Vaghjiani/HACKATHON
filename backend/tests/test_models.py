# Unit tests for Pydantic models

import pytest
from datetime import datetime
from pydantic import ValidationError
import math

from app.models.base import (
    EnvelopeSpec,
    EnvelopeType,
    CoordinateFrame,
    EnvelopeMetadata,
    EnvelopeConstraints,
    ModuleSpec,
    ModuleType,
    ModuleMetadata,
    BoundingBox,
    ModulePlacement,
    MissionParameters,
    MissionConstraints,
    PerformanceMetrics,
    LayoutSpec,
    LayoutMetadata,
    LayoutConstraints
)


# ============================================================================
# TEST HELPERS
# ============================================================================

def create_valid_envelope_metadata():
    return EnvelopeMetadata(
        name="Test Envelope",
        creator="test_user",
        created=datetime(2024, 1, 1),
        version="1.0",
        description="Test envelope for unit testing"
    )


def create_valid_envelope_spec():
    return EnvelopeSpec(
        id="env_001",
        type=EnvelopeType.CYLINDER,
        params={"radius": 3.0, "length": 12.0},
        coordinate_frame=CoordinateFrame.LOCAL,
        metadata=create_valid_envelope_metadata()
    )


def create_valid_bounding_box():
    return BoundingBox(x=2.0, y=2.0, z=2.5)


def create_valid_module_spec():
    return ModuleSpec(
        module_id="mod_001",
        type=ModuleType.SLEEP_QUARTER,
        name="Sleep Quarter A",
        bbox_m=create_valid_bounding_box(),
        mass_kg=500.0,
        power_w=100.0,
        stowage_m3=5.0,
        connectivity_ports=["port1", "port2"],
        adjacency_preferences=[ModuleType.GALLEY],
        adjacency_restrictions=[ModuleType.MECHANICAL]
    )


def create_valid_module_placement():
    return ModulePlacement(
        module_id="mod_001",
        type=ModuleType.SLEEP_QUARTER,
        position=[1.0, 2.0, 3.0],
        rotation_deg=45.0,
        connections=["mod_002"]
    )


def create_valid_performance_metrics():
    return PerformanceMetrics(
        mean_transit_time=30.5,
        egress_time=120.0,
        mass_total=15000.0,
        power_budget=5000.0,
        thermal_margin=0.25,
        lss_margin=0.30,
        stowage_utilization=0.85
    )


def create_valid_mission_parameters():
    return MissionParameters(
        crew_size=4,
        duration_days=180,
        priority_weights={
            "safety": 0.4,
            "efficiency": 0.3,
            "mass": 0.2,
            "power": 0.1
        },
        activity_schedule={
            "sleep": 8.0,
            "work": 8.0,
            "exercise": 2.0,
            "meals": 3.0,
            "personal": 3.0
        },
        emergency_scenarios=["fire", "depressurization"]
    )


def create_valid_layout_spec():
    return LayoutSpec(
        layout_id="layout_001",
        envelope_id="env_001",
        modules=[create_valid_module_placement()],
        kpis=create_valid_performance_metrics(),
        explainability="This layout prioritizes safety by placing modules strategically."
    )


# ============================================================================
# ENVELOPE TESTS
# ============================================================================

class TestEnvelopeSpec:
    def test_valid_cylinder_envelope(self):
        envelope = create_valid_envelope_spec()
        assert envelope.id == "env_001"
        assert envelope.type == EnvelopeType.CYLINDER
        assert envelope.params["radius"] == 3.0
        assert envelope.params["length"] == 12.0
        
        # Test computed volume
        expected_volume = math.pi * 3.0 * 3.0 * 12.0
        assert abs(envelope.volume - expected_volume) < 1e-6

    def test_valid_box_envelope(self):
        envelope = create_valid_envelope_spec()
        envelope.type = EnvelopeType.BOX
        envelope.params = {"width": 5.0, "height": 3.0, "depth": 8.0}
        
        assert envelope.volume == 120.0  # 5 * 3 * 8

    def test_valid_torus_envelope(self):
        envelope = create_valid_envelope_spec()
        envelope.type = EnvelopeType.TORUS
        envelope.params = {"major_radius": 5.0, "minor_radius": 2.0}
        
        expected_volume = 2 * math.pi * math.pi * 5.0 * 2.0 * 2.0
        assert abs(envelope.volume - expected_volume) < 1e-6

    def test_invalid_cylinder_params(self):
        with pytest.raises(ValidationError) as exc_info:
            EnvelopeSpec(
                id="env_001",
                type=EnvelopeType.CYLINDER,
                params={"radius": -1.0, "length": 12.0},  # Negative radius
                coordinate_frame=CoordinateFrame.LOCAL,
                metadata=create_valid_envelope_metadata()
            )
        assert "radius must be positive" in str(exc_info.value)

    def test_missing_cylinder_params(self):
        with pytest.raises(ValidationError) as exc_info:
            EnvelopeSpec(
                id="env_001",
                type=EnvelopeType.CYLINDER,
                params={"radius": 3.0},  # Missing length
                coordinate_frame=CoordinateFrame.LOCAL,
                metadata=create_valid_envelope_metadata()
            )
        assert "requires parameters" in str(exc_info.value)

    def test_invalid_torus_params(self):
        with pytest.raises(ValidationError) as exc_info:
            EnvelopeSpec(
                id="env_001",
                type=EnvelopeType.TORUS,
                params={"major_radius": 2.0, "minor_radius": 3.0},  # minor >= major
                coordinate_frame=CoordinateFrame.LOCAL,
                metadata=create_valid_envelope_metadata()
            )
        assert "minor_radius must be less than major_radius" in str(exc_info.value)

    def test_envelope_constraints_validation(self):
        with pytest.raises(ValidationError) as exc_info:
            EnvelopeConstraints(
                min_volume=100.0,
                max_volume=50.0  # max < min
            )
        assert "min_volume must be less than max_volume" in str(exc_info.value)


# ============================================================================
# MODULE TESTS
# ============================================================================

class TestBoundingBox:
    def test_valid_bounding_box(self):
        bbox = create_valid_bounding_box()
        assert bbox.x == 2.0
        assert bbox.y == 2.0
        assert bbox.z == 2.5
        assert bbox.volume == 10.0  # 2 * 2 * 2.5
        assert bbox.surface_area == 28.0  # 2 * (2*2 + 2*2.5 + 2*2.5) = 2 * (4 + 5 + 5) = 28

    def test_invalid_bounding_box_dimensions(self):
        with pytest.raises(ValidationError):
            BoundingBox(x=0, y=2.0, z=2.5)  # Zero dimension
        
        with pytest.raises(ValidationError):
            BoundingBox(x=-1.0, y=2.0, z=2.5)  # Negative dimension


class TestModuleSpec:
    def test_valid_module_spec(self):
        module = create_valid_module_spec()
        assert module.module_id == "mod_001"
        assert module.type == ModuleType.SLEEP_QUARTER
        assert module.mass_kg == 500.0
        assert module.power_w == 100.0
        
        # Test computed fields
        assert module.density_kg_m3 == 50.0  # 500 / 10
        assert module.power_density_w_m3 == 10.0  # 100 / 10

    def test_invalid_mass(self):
        with pytest.raises(ValidationError):
            ModuleSpec(
                module_id="mod_001",
                type=ModuleType.SLEEP_QUARTER,
                name="Test Module",
                bbox_m=create_valid_bounding_box(),
                mass_kg=0.05,  # Below minimum
                power_w=100.0,
                stowage_m3=5.0
            )

    def test_excessive_stowage_volume(self):
        with pytest.raises(ValidationError) as exc_info:
            ModuleSpec(
                module_id="mod_001",
                type=ModuleType.SLEEP_QUARTER,
                name="Test Module",
                bbox_m=create_valid_bounding_box(),
                mass_kg=500.0,
                power_w=100.0,
                stowage_m3=15.0  # Greater than bbox volume (10.0)
            )
        assert "cannot exceed module bounding box volume" in str(exc_info.value)

    def test_conflicting_adjacency_rules(self):
        with pytest.raises(ValidationError) as exc_info:
            ModuleSpec(
                module_id="mod_001",
                type=ModuleType.SLEEP_QUARTER,
                name="Test Module",
                bbox_m=create_valid_bounding_box(),
                mass_kg=500.0,
                power_w=100.0,
                stowage_m3=5.0,
                adjacency_preferences=[ModuleType.GALLEY, ModuleType.LABORATORY],
                adjacency_restrictions=[ModuleType.GALLEY, ModuleType.MECHANICAL]  # Conflict with GALLEY
            )
        assert "cannot be both preferred and restricted" in str(exc_info.value)


class TestModulePlacement:
    def test_valid_module_placement(self):
        placement = create_valid_module_placement()
        assert placement.module_id == "mod_001"
        assert placement.position == [1.0, 2.0, 3.0]
        assert placement.rotation_deg == 45.0
        
        # Test computed field
        expected_magnitude = math.sqrt(1.0**2 + 2.0**2 + 3.0**2)
        assert abs(placement.position_magnitude - expected_magnitude) < 1e-6

    def test_invalid_position_format(self):
        with pytest.raises(ValidationError):
            ModulePlacement(
                module_id="mod_001",
                type=ModuleType.SLEEP_QUARTER,
                position=[1.0, 2.0],  # Missing Z coordinate
                rotation_deg=45.0
            )

    def test_invalid_position_values(self):
        with pytest.raises(ValidationError) as exc_info:
            ModulePlacement(
                module_id="mod_001",
                type=ModuleType.SLEEP_QUARTER,
                position=[1.0, float('inf'), 3.0],  # Infinite coordinate
                rotation_deg=45.0
            )
        assert "must be a finite number" in str(exc_info.value)

    def test_rotation_normalization(self):
        placement = ModulePlacement(
            module_id="mod_001",
            type=ModuleType.SLEEP_QUARTER,
            position=[1.0, 2.0, 3.0],
            rotation_deg=450.0  # Should normalize to 90.0
        )
        assert placement.rotation_deg == 90.0


# ============================================================================
# MISSION PARAMETERS TESTS
# ============================================================================

class TestMissionParameters:
    def test_valid_mission_parameters(self):
        mission = create_valid_mission_parameters()
        assert mission.crew_size == 4
        assert mission.duration_days == 180
        
        # Test computed fields
        assert mission.total_crew_hours == 4 * 180 * 24
        assert mission.daily_activity_total == 24.0

    def test_invalid_priority_weights_sum(self):
        with pytest.raises(ValidationError) as exc_info:
            MissionParameters(
                crew_size=4,
                duration_days=180,
                priority_weights={
                    "safety": 0.5,
                    "efficiency": 0.3,
                    "mass": 0.1,
                    "power": 0.05  # Sum = 0.95, not 1.0
                }
            )
        assert "must sum to 1.0" in str(exc_info.value)

    def test_negative_priority_weight(self):
        with pytest.raises(ValidationError) as exc_info:
            MissionParameters(
                crew_size=4,
                duration_days=180,
                priority_weights={
                    "safety": -0.1,  # Negative weight
                    "efficiency": 0.6,
                    "mass": 0.3,
                    "power": 0.2
                }
            )
        assert "cannot be negative" in str(exc_info.value)

    def test_negative_activity_time(self):
        with pytest.raises(ValidationError) as exc_info:
            MissionParameters(
                crew_size=4,
                duration_days=180,
                activity_schedule={
                    "sleep": 8.0,
                    "work": -2.0,  # Negative time
                    "exercise": 2.0,
                    "meals": 3.0,
                    "personal": 3.0
                }
            )
        assert "cannot be negative" in str(exc_info.value)

    def test_crew_size_constraint_validation(self):
        with pytest.raises(ValidationError) as exc_info:
            MissionParameters(
                crew_size=8,  # Exceeds constraint
                duration_days=180,
                constraints=MissionConstraints(max_crew_size=6)
            )
        assert "exceeds maximum allowed" in str(exc_info.value)


# ============================================================================
# PERFORMANCE METRICS TESTS
# ============================================================================

class TestPerformanceMetrics:
    def test_valid_performance_metrics(self):
        metrics = create_valid_performance_metrics()
        assert metrics.mean_transit_time == 30.5
        assert metrics.egress_time == 120.0
        
        # Test computed overall score
        assert 0 <= metrics.overall_score <= 1
        
        # Test critical issues (should be empty for valid metrics)
        assert len(metrics.critical_issues) == 0

    def test_negative_values_validation(self):
        with pytest.raises(ValidationError):
            PerformanceMetrics(
                mean_transit_time=-10.0,  # Negative value
                egress_time=120.0,
                mass_total=15000.0,
                power_budget=5000.0,
                thermal_margin=0.25,
                lss_margin=0.30,
                stowage_utilization=0.85
            )

    def test_critical_thermal_margin(self):
        with pytest.raises(ValidationError) as exc_info:
            PerformanceMetrics(
                mean_transit_time=30.5,
                egress_time=120.0,
                mass_total=15000.0,
                power_budget=5000.0,
                thermal_margin=-0.6,  # Below -50%
                lss_margin=0.30,
                stowage_utilization=0.85
            )
        assert "critical thermal overload" in str(exc_info.value)

    def test_critical_lss_margin(self):
        with pytest.raises(ValidationError) as exc_info:
            PerformanceMetrics(
                mean_transit_time=30.5,
                egress_time=120.0,
                mass_total=15000.0,
                power_budget=5000.0,
                thermal_margin=0.25,
                lss_margin=-0.3,  # Below -20%
                stowage_utilization=0.85
            )
        assert "life support failure risk" in str(exc_info.value)

    def test_critical_issues_detection(self):
        metrics = PerformanceMetrics(
            mean_transit_time=200.0,  # High transit time
            egress_time=400.0,  # High egress time
            mass_total=15000.0,
            power_budget=5000.0,
            thermal_margin=0.05,  # Low thermal margin
            lss_margin=0.15,  # Low LSS margin
            stowage_utilization=1.2  # Overcrowded
        )
        
        issues = metrics.critical_issues
        assert len(issues) == 5  # All critical issues should be detected
        assert any("thermal margin" in issue for issue in issues)
        assert any("LSS margin" in issue for issue in issues)
        assert any("overcrowding" in issue for issue in issues)
        assert any("egress time" in issue for issue in issues)
        assert any("transit times" in issue for issue in issues)


# ============================================================================
# LAYOUT SPEC TESTS
# ============================================================================

class TestLayoutSpec:
    def test_valid_layout_spec(self):
        layout = create_valid_layout_spec()
        assert layout.layout_id == "layout_001"
        assert layout.envelope_id == "env_001"
        assert len(layout.modules) == 1
        
        # Test computed fields
        assert layout.module_count == 1
        assert layout.module_types_count["sleep_quarter"] == 1
        assert not layout.has_airlock  # No airlock in test layout

    def test_empty_modules_validation(self):
        with pytest.raises(ValidationError) as exc_info:
            LayoutSpec(
                layout_id="layout_001",
                envelope_id="env_001",
                modules=[],  # Empty modules list
                kpis=create_valid_performance_metrics(),
                explainability="Test explanation"
            )
        assert "at least 1 item" in str(exc_info.value)

    def test_duplicate_module_ids(self):
        placement1 = create_valid_module_placement()
        placement2 = create_valid_module_placement()
        # Both have the same module_id
        
        with pytest.raises(ValidationError) as exc_info:
            LayoutSpec(
                layout_id="layout_001",
                envelope_id="env_001",
                modules=[placement1, placement2],
                kpis=create_valid_performance_metrics(),
                explainability="Test explanation"
            )
        assert "duplicate module IDs" in str(exc_info.value)

    def test_short_explainability(self):
        with pytest.raises(ValidationError) as exc_info:
            LayoutSpec(
                layout_id="layout_001",
                envelope_id="env_001",
                modules=[create_valid_module_placement()],
                kpis=create_valid_performance_metrics(),
                explainability="Short"  # Too short
            )
        assert "at least 10 characters" in str(exc_info.value)

    def test_layout_bounds_calculation(self):
        placement1 = ModulePlacement(
            module_id="mod_001",
            type=ModuleType.SLEEP_QUARTER,
            position=[1.0, 2.0, 3.0],
            rotation_deg=0.0
        )
        placement2 = ModulePlacement(
            module_id="mod_002",
            type=ModuleType.GALLEY,
            position=[4.0, 1.0, 2.0],
            rotation_deg=0.0
        )
        
        layout = LayoutSpec(
            layout_id="layout_001",
            envelope_id="env_001",
            modules=[placement1, placement2],
            kpis=create_valid_performance_metrics(),
            explainability="Test layout with multiple modules"
        )
        
        bounds = layout.layout_bounds
        assert bounds["min_x"] == 1.0
        assert bounds["max_x"] == 4.0
        assert bounds["min_y"] == 1.0
        assert bounds["max_y"] == 2.0
        assert bounds["min_z"] == 2.0
        assert bounds["max_z"] == 3.0

    def test_has_airlock_detection(self):
        airlock_placement = ModulePlacement(
            module_id="airlock_001",
            type=ModuleType.AIRLOCK,
            position=[0.0, 0.0, 0.0],
            rotation_deg=0.0
        )
        
        layout = LayoutSpec(
            layout_id="layout_001",
            envelope_id="env_001",
            modules=[create_valid_module_placement(), airlock_placement],
            kpis=create_valid_performance_metrics(),
            explainability="Layout with airlock module"
        )
        
        assert layout.has_airlock is True
        assert layout.module_types_count["airlock"] == 1


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestModelIntegration:
    def test_complete_habitat_specification(self):
        """Test creating a complete habitat specification with all models"""
        
        # Create envelope
        envelope = create_valid_envelope_spec()
        
        # Create modules
        sleep_module = create_valid_module_spec()
        galley_module = ModuleSpec(
            module_id="galley_001",
            type=ModuleType.GALLEY,
            name="Main Galley",
            bbox_m=BoundingBox(x=3.0, y=2.0, z=2.5),
            mass_kg=800.0,
            power_w=500.0,
            stowage_m3=8.0
        )
        
        # Create placements
        sleep_placement = create_valid_module_placement()
        galley_placement = ModulePlacement(
            module_id="galley_001",
            type=ModuleType.GALLEY,
            position=[5.0, 0.0, 0.0],
            rotation_deg=90.0,
            connections=["mod_001"]
        )
        
        # Create mission parameters
        mission = create_valid_mission_parameters()
        
        # Create performance metrics
        metrics = create_valid_performance_metrics()
        
        # Create layout
        layout = LayoutSpec(
            layout_id="complete_layout_001",
            envelope_id=envelope.id,
            modules=[sleep_placement, galley_placement],
            kpis=metrics,
            explainability="Complete habitat layout with sleep quarters and galley, optimized for crew efficiency and safety."
        )
        
        # Verify all components are valid
        assert envelope.volume > 0
        assert sleep_module.density_kg_m3 > 0
        assert galley_module.power_density_w_m3 > 0
        assert mission.total_crew_hours > 0
        assert 0 <= metrics.overall_score <= 1
        assert layout.module_count == 2
        assert layout.has_airlock is False  # No airlock in this test layout

    def test_model_serialization_deserialization(self):
        """Test that models can be serialized to JSON and back"""
        
        # Test envelope serialization
        envelope = create_valid_envelope_spec()
        envelope_dict = envelope.model_dump()
        envelope_restored = EnvelopeSpec(**envelope_dict)
        assert envelope_restored.id == envelope.id
        assert envelope_restored.volume == envelope.volume
        
        # Test layout serialization
        layout = create_valid_layout_spec()
        layout_dict = layout.model_dump()
        layout_restored = LayoutSpec(**layout_dict)
        assert layout_restored.layout_id == layout.layout_id
        assert layout_restored.module_count == layout.module_count