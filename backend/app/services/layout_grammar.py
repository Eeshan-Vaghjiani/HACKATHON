"""
Layout Grammar and Adjacency Rules System for HabitatCanvas

This module implements layout grammar rules and adjacency constraints
for habitat module placement, including rule violation detection and
penalty systems for different mission types.
"""

import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from collections import defaultdict

from app.models.base import ModulePlacement, ModuleType, MissionParameters
from app.models.module_library import get_module_library, ModuleDefinition

logger = logging.getLogger(__name__)


class RuleType(str, Enum):
    """Types of layout grammar rules"""
    ADJACENCY_PREFERENCE = "adjacency_preference"
    ADJACENCY_RESTRICTION = "adjacency_restriction"
    FUNCTIONAL_GROUPING = "functional_grouping"
    SEPARATION_REQUIREMENT = "separation_requirement"
    CONNECTIVITY_REQUIREMENT = "connectivity_requirement"
    ORIENTATION_CONSTRAINT = "orientation_constraint"
    ZONE_ASSIGNMENT = "zone_assignment"


class RuleSeverity(str, Enum):
    """Severity levels for rule violations"""
    CRITICAL = "critical"      # Must be enforced (hard constraint)
    HIGH = "high"             # Strong preference (high penalty)
    MEDIUM = "medium"         # Moderate preference (medium penalty)
    LOW = "low"              # Weak preference (low penalty)
    ADVISORY = "advisory"     # Suggestion only (minimal penalty)


class ZoneType(str, Enum):
    """Habitat zones for module organization"""
    CREW_QUARTERS = "crew_quarters"
    WORK_AREA = "work_area"
    COMMON_AREA = "common_area"
    UTILITY_AREA = "utility_area"
    STORAGE_AREA = "storage_area"
    EXTERNAL_ACCESS = "external_access"
    EMERGENCY_ZONE = "emergency_zone"


@dataclass
class LayoutRule:
    """Represents a single layout grammar rule"""
    rule_id: str
    rule_type: RuleType
    severity: RuleSeverity
    description: str
    
    # Rule parameters (varies by rule type)
    source_modules: List[ModuleType] = field(default_factory=list)
    target_modules: List[ModuleType] = field(default_factory=list)
    distance_constraint: Optional[Tuple[float, float]] = None  # (min_distance, max_distance)
    zone_constraint: Optional[ZoneType] = None
    orientation_constraint: Optional[float] = None  # degrees
    
    # Rule conditions
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Penalty configuration
    penalty_base: float = 100.0
    penalty_multiplier: float = 1.0
    
    def calculate_penalty(self, violation_count: int = 1, violation_severity: float = 1.0) -> float:
        """Calculate penalty for rule violation"""
        severity_multipliers = {
            RuleSeverity.CRITICAL: 10.0,
            RuleSeverity.HIGH: 5.0,
            RuleSeverity.MEDIUM: 2.0,
            RuleSeverity.LOW: 1.0,
            RuleSeverity.ADVISORY: 0.1
        }
        
        multiplier = severity_multipliers.get(self.severity, 1.0)
        return self.penalty_base * multiplier * self.penalty_multiplier * violation_count * violation_severity


@dataclass
class RuleViolation:
    """Represents a detected rule violation"""
    rule: LayoutRule
    violating_modules: List[str]  # Module IDs
    violation_description: str
    penalty: float
    severity_factor: float = 1.0
    
    @property
    def is_critical(self) -> bool:
        return self.rule.severity == RuleSeverity.CRITICAL


@dataclass
class GrammarEvaluation:
    """Results of layout grammar evaluation"""
    total_penalty: float
    violations: List[RuleViolation]
    rule_compliance_score: float  # 0.0 to 1.0
    critical_violations: int
    
    @property
    def is_valid_layout(self) -> bool:
        """Check if layout has no critical violations"""
        return self.critical_violations == 0


class LayoutGrammar:
    """
    Layout grammar system for enforcing habitat design rules.
    
    Manages adjacency preferences, functional groupings, and spatial
    constraints for different mission types and habitat configurations.
    """
    
    def __init__(self):
        self.module_library = get_module_library()
        self.rules: Dict[str, LayoutRule] = {}
        self.mission_rule_sets: Dict[str, List[str]] = {}
        
        # Initialize with standard rules
        self._initialize_standard_rules()
        self._initialize_mission_rule_sets()
    
    def _initialize_standard_rules(self):
        """Initialize standard layout grammar rules"""
        
        # Adjacency preference rules
        self.add_rule(LayoutRule(
            rule_id="sleep_galley_preference",
            rule_type=RuleType.ADJACENCY_PREFERENCE,
            severity=RuleSeverity.MEDIUM,
            description="Sleep quarters should be near galley for meal access",
            source_modules=[ModuleType.SLEEP_QUARTER],
            target_modules=[ModuleType.GALLEY],
            distance_constraint=(0.0, 8.0),
            penalty_base=50.0
        ))
        
        self.add_rule(LayoutRule(
            rule_id="medical_central_preference",
            rule_type=RuleType.ADJACENCY_PREFERENCE,
            severity=RuleSeverity.HIGH,
            description="Medical bay should be centrally accessible from all crew areas",
            source_modules=[ModuleType.MEDICAL],
            target_modules=[ModuleType.SLEEP_QUARTER, ModuleType.GALLEY, ModuleType.LABORATORY],
            distance_constraint=(0.0, 10.0),
            penalty_base=75.0
        ))
        
        self.add_rule(LayoutRule(
            rule_id="lab_storage_preference",
            rule_type=RuleType.ADJACENCY_PREFERENCE,
            severity=RuleSeverity.MEDIUM,
            description="Laboratory should be adjacent to storage for equipment access",
            source_modules=[ModuleType.LABORATORY],
            target_modules=[ModuleType.STORAGE],
            distance_constraint=(0.0, 5.0),
            penalty_base=40.0
        ))
        
        # Adjacency restriction rules
        self.add_rule(LayoutRule(
            rule_id="sleep_mechanical_restriction",
            rule_type=RuleType.ADJACENCY_RESTRICTION,
            severity=RuleSeverity.HIGH,
            description="Sleep quarters should not be adjacent to mechanical systems (noise)",
            source_modules=[ModuleType.SLEEP_QUARTER],
            target_modules=[ModuleType.MECHANICAL],
            distance_constraint=(3.0, float('inf')),
            penalty_base=100.0
        ))
        
        self.add_rule(LayoutRule(
            rule_id="galley_lab_restriction",
            rule_type=RuleType.ADJACENCY_RESTRICTION,
            severity=RuleSeverity.MEDIUM,
            description="Galley should be separated from laboratory (contamination risk)",
            source_modules=[ModuleType.GALLEY],
            target_modules=[ModuleType.LABORATORY],
            distance_constraint=(2.0, float('inf')),
            penalty_base=60.0
        ))
        
        self.add_rule(LayoutRule(
            rule_id="airlock_sleep_restriction",
            rule_type=RuleType.ADJACENCY_RESTRICTION,
            severity=RuleSeverity.MEDIUM,
            description="Airlocks should not be directly adjacent to sleep quarters (noise, contamination)",
            source_modules=[ModuleType.AIRLOCK],
            target_modules=[ModuleType.SLEEP_QUARTER],
            distance_constraint=(2.5, float('inf')),
            penalty_base=50.0
        ))
        
        # Functional grouping rules
        self.add_rule(LayoutRule(
            rule_id="crew_area_grouping",
            rule_type=RuleType.FUNCTIONAL_GROUPING,
            severity=RuleSeverity.MEDIUM,
            description="Crew living areas should be grouped together",
            source_modules=[ModuleType.SLEEP_QUARTER, ModuleType.GALLEY, ModuleType.MEDICAL],
            target_modules=[ModuleType.SLEEP_QUARTER, ModuleType.GALLEY, ModuleType.MEDICAL],
            distance_constraint=(0.0, 12.0),
            penalty_base=30.0,
            zone_constraint=ZoneType.CREW_QUARTERS
        ))
        
        self.add_rule(LayoutRule(
            rule_id="work_area_grouping",
            rule_type=RuleType.FUNCTIONAL_GROUPING,
            severity=RuleSeverity.LOW,
            description="Work areas should be grouped for operational efficiency",
            source_modules=[ModuleType.LABORATORY, ModuleType.STORAGE],
            target_modules=[ModuleType.LABORATORY, ModuleType.STORAGE],
            distance_constraint=(0.0, 8.0),
            penalty_base=25.0,
            zone_constraint=ZoneType.WORK_AREA
        ))
        
        self.add_rule(LayoutRule(
            rule_id="utility_grouping",
            rule_type=RuleType.FUNCTIONAL_GROUPING,
            severity=RuleSeverity.LOW,
            description="Utility systems should be grouped for maintenance efficiency",
            source_modules=[ModuleType.MECHANICAL, ModuleType.AIRLOCK],
            target_modules=[ModuleType.MECHANICAL, ModuleType.AIRLOCK],
            distance_constraint=(0.0, 6.0),
            penalty_base=20.0,
            zone_constraint=ZoneType.UTILITY_AREA
        ))
        
        # Separation requirements
        self.add_rule(LayoutRule(
            rule_id="mechanical_separation",
            rule_type=RuleType.SEPARATION_REQUIREMENT,
            severity=RuleSeverity.HIGH,
            description="Mechanical systems should be separated from crew areas",
            source_modules=[ModuleType.MECHANICAL],
            target_modules=[ModuleType.SLEEP_QUARTER, ModuleType.GALLEY],
            distance_constraint=(4.0, float('inf')),
            penalty_base=80.0
        ))
        
        self.add_rule(LayoutRule(
            rule_id="exercise_noise_separation",
            rule_type=RuleType.SEPARATION_REQUIREMENT,
            severity=RuleSeverity.MEDIUM,
            description="Exercise area should be separated from quiet areas",
            source_modules=[ModuleType.EXERCISE],
            target_modules=[ModuleType.SLEEP_QUARTER, ModuleType.LABORATORY],
            distance_constraint=(3.0, float('inf')),
            penalty_base=40.0
        ))
        
        # Connectivity requirements
        self.add_rule(LayoutRule(
            rule_id="airlock_connectivity",
            rule_type=RuleType.CONNECTIVITY_REQUIREMENT,
            severity=RuleSeverity.CRITICAL,
            description="All modules must have path to at least one airlock",
            source_modules=[ModuleType.AIRLOCK],
            target_modules=[m for m in ModuleType if m != ModuleType.AIRLOCK],
            distance_constraint=(0.0, 50.0),  # Path distance, not direct
            penalty_base=500.0
        ))
        
        self.add_rule(LayoutRule(
            rule_id="medical_emergency_access",
            rule_type=RuleType.CONNECTIVITY_REQUIREMENT,
            severity=RuleSeverity.HIGH,
            description="Medical bay must be accessible from all crew areas within 30 seconds",
            source_modules=[ModuleType.MEDICAL],
            target_modules=[ModuleType.SLEEP_QUARTER, ModuleType.GALLEY, ModuleType.LABORATORY, ModuleType.EXERCISE],
            distance_constraint=(0.0, 25.0),  # Path distance for 30-second access
            penalty_base=150.0
        ))
        
        # Zone assignment rules
        self.add_rule(LayoutRule(
            rule_id="airlock_external_zone",
            rule_type=RuleType.ZONE_ASSIGNMENT,
            severity=RuleSeverity.HIGH,
            description="Airlocks should be positioned for external access",
            source_modules=[ModuleType.AIRLOCK],
            zone_constraint=ZoneType.EXTERNAL_ACCESS,
            penalty_base=100.0,
            conditions={'envelope_boundary_distance': 2.0}
        ))
    
    def _initialize_mission_rule_sets(self):
        """Initialize rule sets for different mission types"""
        
        # Short-term research missions
        self.mission_rule_sets['short_term_research'] = [
            'lab_storage_preference',
            'galley_lab_restriction',
            'work_area_grouping',
            'airlock_connectivity',
            'medical_emergency_access'
        ]
        
        # Long-term habitation missions
        self.mission_rule_sets['long_term_habitation'] = [
            'sleep_galley_preference',
            'medical_central_preference',
            'sleep_mechanical_restriction',
            'crew_area_grouping',
            'exercise_noise_separation',
            'airlock_connectivity',
            'medical_emergency_access'
        ]
        
        # Emergency shelter
        self.mission_rule_sets['emergency_shelter'] = [
            'medical_central_preference',
            'airlock_connectivity',
            'medical_emergency_access',
            'mechanical_separation'
        ]
        
        # Deep space missions
        self.mission_rule_sets['deep_space_mission'] = [
            'sleep_galley_preference',
            'medical_central_preference',
            'sleep_mechanical_restriction',
            'galley_lab_restriction',
            'crew_area_grouping',
            'utility_grouping',
            'mechanical_separation',
            'airlock_connectivity',
            'medical_emergency_access'
        ]
        
        # Lunar surface missions
        self.mission_rule_sets['lunar_surface'] = [
            'sleep_galley_preference',
            'lab_storage_preference',
            'sleep_mechanical_restriction',
            'airlock_sleep_restriction',
            'work_area_grouping',
            'airlock_connectivity',
            'airlock_external_zone',
            'medical_emergency_access'
        ]
        
        # Mars surface missions
        self.mission_rule_sets['mars_surface'] = [
            'sleep_galley_preference',
            'medical_central_preference',
            'lab_storage_preference',
            'sleep_mechanical_restriction',
            'galley_lab_restriction',
            'crew_area_grouping',
            'work_area_grouping',
            'mechanical_separation',
            'airlock_connectivity',
            'airlock_external_zone',
            'medical_emergency_access'
        ]
    
    def add_rule(self, rule: LayoutRule):
        """Add a new rule to the grammar"""
        self.rules[rule.rule_id] = rule
        logger.debug(f"Added layout rule: {rule.rule_id}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from the grammar"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.debug(f"Removed layout rule: {rule_id}")
            return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[LayoutRule]:
        """Get a specific rule by ID"""
        return self.rules.get(rule_id)
    
    def get_rules_for_mission(self, mission_type: str) -> List[LayoutRule]:
        """Get applicable rules for a specific mission type"""
        rule_ids = self.mission_rule_sets.get(mission_type, [])
        return [self.rules[rule_id] for rule_id in rule_ids if rule_id in self.rules]
    
    def evaluate_layout(
        self, 
        modules: List[ModulePlacement], 
        mission_params: Optional[MissionParameters] = None,
        custom_rules: Optional[List[str]] = None
    ) -> GrammarEvaluation:
        """
        Evaluate a layout against grammar rules.
        
        Args:
            modules: List of module placements to evaluate
            mission_params: Mission parameters for rule selection
            custom_rules: Custom list of rule IDs to apply
            
        Returns:
            Grammar evaluation results
        """
        logger.info(f"Evaluating layout with {len(modules)} modules against grammar rules")
        
        # Determine which rules to apply
        if custom_rules:
            applicable_rules = [self.rules[rule_id] for rule_id in custom_rules if rule_id in self.rules]
        elif mission_params:
            # Try to infer mission type from parameters
            mission_type = self._infer_mission_type(mission_params)
            applicable_rules = self.get_rules_for_mission(mission_type)
        else:
            # Use all rules
            applicable_rules = list(self.rules.values())
        
        logger.debug(f"Applying {len(applicable_rules)} rules")
        
        violations = []
        total_penalty = 0.0
        critical_violations = 0
        
        # Evaluate each rule
        for rule in applicable_rules:
            rule_violations = self._evaluate_rule(rule, modules)
            violations.extend(rule_violations)
            
            for violation in rule_violations:
                total_penalty += violation.penalty
                if violation.is_critical:
                    critical_violations += 1
        
        # Calculate compliance score
        max_possible_penalty = sum(rule.penalty_base * 10 for rule in applicable_rules)  # Assume worst case
        compliance_score = max(0.0, 1.0 - (total_penalty / max_possible_penalty)) if max_possible_penalty > 0 else 1.0
        
        evaluation = GrammarEvaluation(
            total_penalty=total_penalty,
            violations=violations,
            rule_compliance_score=compliance_score,
            critical_violations=critical_violations
        )
        
        logger.info(f"Grammar evaluation complete: {len(violations)} violations, "
                   f"penalty={total_penalty:.1f}, compliance={compliance_score:.3f}")
        
        return evaluation
    
    def _evaluate_rule(self, rule: LayoutRule, modules: List[ModulePlacement]) -> List[RuleViolation]:
        """Evaluate a specific rule against the layout"""
        violations = []
        
        try:
            if rule.rule_type == RuleType.ADJACENCY_PREFERENCE:
                violations.extend(self._evaluate_adjacency_preference(rule, modules))
            
            elif rule.rule_type == RuleType.ADJACENCY_RESTRICTION:
                violations.extend(self._evaluate_adjacency_restriction(rule, modules))
            
            elif rule.rule_type == RuleType.FUNCTIONAL_GROUPING:
                violations.extend(self._evaluate_functional_grouping(rule, modules))
            
            elif rule.rule_type == RuleType.SEPARATION_REQUIREMENT:
                violations.extend(self._evaluate_separation_requirement(rule, modules))
            
            elif rule.rule_type == RuleType.CONNECTIVITY_REQUIREMENT:
                violations.extend(self._evaluate_connectivity_requirement(rule, modules))
            
            elif rule.rule_type == RuleType.ZONE_ASSIGNMENT:
                violations.extend(self._evaluate_zone_assignment(rule, modules))
            
            else:
                logger.warning(f"Unknown rule type: {rule.rule_type}")
        
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {str(e)}")
        
        return violations
    
    def _evaluate_adjacency_preference(self, rule: LayoutRule, modules: List[ModulePlacement]) -> List[RuleViolation]:
        """Evaluate adjacency preference rules"""
        violations = []
        
        source_modules = [m for m in modules if m.type in rule.source_modules]
        target_modules = [m for m in modules if m.type in rule.target_modules]
        
        for source in source_modules:
            min_distance = float('inf')
            closest_target = None
            
            for target in target_modules:
                if source.module_id == target.module_id:
                    continue
                
                distance = self._calculate_distance(source, target)
                if distance < min_distance:
                    min_distance = distance
                    closest_target = target
            
            # Check if preference is violated
            if rule.distance_constraint and closest_target:
                min_dist, max_dist = rule.distance_constraint
                
                if min_distance > max_dist:
                    # Violation: preferred modules are too far apart
                    severity_factor = min(2.0, min_distance / max_dist)
                    penalty = rule.calculate_penalty(1, severity_factor)
                    
                    violations.append(RuleViolation(
                        rule=rule,
                        violating_modules=[source.module_id, closest_target.module_id],
                        violation_description=f"{self._get_module_type_str(source.type)} is {min_distance:.1f}m from nearest {self._get_module_type_str(closest_target.type)} (preferred: <{max_dist:.1f}m)",
                        penalty=penalty,
                        severity_factor=severity_factor
                    ))
        
        return violations
    
    def _evaluate_adjacency_restriction(self, rule: LayoutRule, modules: List[ModulePlacement]) -> List[RuleViolation]:
        """Evaluate adjacency restriction rules"""
        violations = []
        
        source_modules = [m for m in modules if m.type in rule.source_modules]
        target_modules = [m for m in modules if m.type in rule.target_modules]
        
        for source in source_modules:
            for target in target_modules:
                if source.module_id == target.module_id:
                    continue
                
                distance = self._calculate_distance(source, target)
                
                # Check if restriction is violated
                if rule.distance_constraint:
                    min_dist, max_dist = rule.distance_constraint
                    
                    if distance < min_dist:
                        # Violation: restricted modules are too close
                        severity_factor = min(3.0, min_dist / max(0.1, distance))
                        penalty = rule.calculate_penalty(1, severity_factor)
                        
                        violations.append(RuleViolation(
                            rule=rule,
                            violating_modules=[source.module_id, target.module_id],
                            violation_description=f"{self._get_module_type_str(source.type)} is {distance:.1f}m from {self._get_module_type_str(target.type)} (minimum: {min_dist:.1f}m)",
                            penalty=penalty,
                            severity_factor=severity_factor
                        ))
        
        return violations
    
    def _evaluate_functional_grouping(self, rule: LayoutRule, modules: List[ModulePlacement]) -> List[RuleViolation]:
        """Evaluate functional grouping rules"""
        violations = []
        
        # Get all modules in the functional group
        group_modules = [m for m in modules if m.type in rule.source_modules or m.type in rule.target_modules]
        
        if len(group_modules) < 2:
            return violations  # No grouping possible with less than 2 modules
        
        # Calculate centroid of the group
        centroid = self._calculate_centroid(group_modules)
        
        # Check if any module is too far from the group centroid
        if rule.distance_constraint:
            min_dist, max_dist = rule.distance_constraint
            
            for module in group_modules:
                distance_to_centroid = np.linalg.norm(np.array(module.position) - centroid)
                
                if distance_to_centroid > max_dist:
                    severity_factor = min(2.0, distance_to_centroid / max_dist)
                    penalty = rule.calculate_penalty(1, severity_factor)
                    
                    violations.append(RuleViolation(
                        rule=rule,
                        violating_modules=[module.module_id],
                        violation_description=f"{self._get_module_type_str(module.type)} is {distance_to_centroid:.1f}m from functional group centroid (max: {max_dist:.1f}m)",
                        penalty=penalty,
                        severity_factor=severity_factor
                    ))
        
        return violations
    
    def _evaluate_separation_requirement(self, rule: LayoutRule, modules: List[ModulePlacement]) -> List[RuleViolation]:
        """Evaluate separation requirement rules"""
        # This is similar to adjacency restriction but may have different logic
        return self._evaluate_adjacency_restriction(rule, modules)
    
    def _evaluate_connectivity_requirement(self, rule: LayoutRule, modules: List[ModulePlacement]) -> List[RuleViolation]:
        """Evaluate connectivity requirement rules"""
        violations = []
        
        source_modules = [m for m in modules if m.type in rule.source_modules]
        target_modules = [m for m in modules if m.type in rule.target_modules]
        
        if not source_modules:
            # Critical violation: required source modules are missing
            penalty = rule.calculate_penalty(1, 5.0)  # High severity for missing critical modules
            violations.append(RuleViolation(
                rule=rule,
                violating_modules=[],
                violation_description=f"Missing required modules: {[self._get_module_type_str(t) for t in rule.source_modules]}",
                penalty=penalty,
                severity_factor=5.0
            ))
            return violations
        
        # For each target module, check if it's connected to at least one source module
        for target in target_modules:
            min_path_distance = float('inf')
            
            for source in source_modules:
                if source.module_id == target.module_id:
                    continue
                
                # For now, use direct distance as approximation of path distance
                # In a full implementation, this would use actual pathfinding
                distance = self._calculate_distance(source, target)
                min_path_distance = min(min_path_distance, distance)
            
            # Check connectivity constraint
            if rule.distance_constraint and min_path_distance != float('inf'):
                min_dist, max_dist = rule.distance_constraint
                
                if min_path_distance > max_dist:
                    severity_factor = min(3.0, min_path_distance / max_dist)
                    penalty = rule.calculate_penalty(1, severity_factor)
                    
                    violations.append(RuleViolation(
                        rule=rule,
                        violating_modules=[target.module_id],
                        violation_description=f"{self._get_module_type_str(target.type)} is {min_path_distance:.1f}m from nearest {self._get_module_type_str(rule.source_modules[0])} (max path: {max_dist:.1f}m)",
                        penalty=penalty,
                        severity_factor=severity_factor
                    ))
        
        return violations
    
    def _evaluate_zone_assignment(self, rule: LayoutRule, modules: List[ModulePlacement]) -> List[RuleViolation]:
        """Evaluate zone assignment rules"""
        violations = []
        
        # This is a simplified implementation
        # In a full system, this would check actual zone boundaries
        source_modules = [m for m in modules if m.type in rule.source_modules]
        
        for module in source_modules:
            # Check if module meets zone-specific conditions
            if 'envelope_boundary_distance' in rule.conditions:
                required_distance = rule.conditions['envelope_boundary_distance']
                
                # Calculate distance to envelope boundary (simplified)
                position = np.array(module.position)
                distance_to_boundary = min(
                    abs(position[0]) + 2.0,  # Simplified boundary calculation
                    abs(position[1]) + 2.0,
                    abs(position[2]) + 2.0
                )
                
                if distance_to_boundary > required_distance:
                    severity_factor = distance_to_boundary / required_distance
                    penalty = rule.calculate_penalty(1, severity_factor)
                    
                    violations.append(RuleViolation(
                        rule=rule,
                        violating_modules=[module.module_id],
                        violation_description=f"{self._get_module_type_str(module.type)} is {distance_to_boundary:.1f}m from boundary (required: <{required_distance:.1f}m for {rule.zone_constraint.value if rule.zone_constraint else 'unknown'})",
                        penalty=penalty,
                        severity_factor=severity_factor
                    ))
        
        return violations
    
    def _get_module_type_str(self, module_type) -> str:
        """Safely get string representation of module type"""
        if isinstance(module_type, str):
            return module_type
        elif hasattr(module_type, 'value'):
            return module_type.value
        else:
            return str(module_type)
    
    def _calculate_distance(self, module1: ModulePlacement, module2: ModulePlacement) -> float:
        """Calculate Euclidean distance between two modules"""
        pos1 = np.array(module1.position)
        pos2 = np.array(module2.position)
        return float(np.linalg.norm(pos1 - pos2))
    
    def _calculate_centroid(self, modules: List[ModulePlacement]) -> np.ndarray:
        """Calculate centroid position of a group of modules"""
        if not modules:
            return np.zeros(3)
        
        positions = np.array([module.position for module in modules])
        return np.mean(positions, axis=0)
    
    def _infer_mission_type(self, mission_params: MissionParameters) -> str:
        """Infer mission type from mission parameters"""
        duration = mission_params.duration_days
        crew_size = mission_params.crew_size
        priorities = mission_params.priority_weights
        
        # Simple heuristics for mission type inference
        if duration <= 30:
            return 'short_term_research'
        elif duration >= 365:
            if priorities.get('mass', 0) > 0.3:
                return 'deep_space_mission'
            else:
                return 'mars_surface'
        elif duration >= 180:
            return 'long_term_habitation'
        elif priorities.get('safety', 0) > 0.4:
            return 'emergency_shelter'
        else:
            return 'lunar_surface'
    
    def create_custom_rule_set(
        self, 
        name: str, 
        rule_ids: List[str],
        description: Optional[str] = None
    ) -> bool:
        """Create a custom rule set for specific scenarios"""
        # Validate that all rule IDs exist
        invalid_rules = [rule_id for rule_id in rule_ids if rule_id not in self.rules]
        if invalid_rules:
            logger.error(f"Invalid rule IDs: {invalid_rules}")
            return False
        
        self.mission_rule_sets[name] = rule_ids
        logger.info(f"Created custom rule set '{name}' with {len(rule_ids)} rules")
        
        if description:
            logger.info(f"Rule set description: {description}")
        
        return True
    
    def get_rule_summary(self) -> Dict[str, Any]:
        """Get a summary of all rules and rule sets"""
        return {
            'total_rules': len(self.rules),
            'rules_by_type': {
                rule_type.value: len([r for r in self.rules.values() if r.rule_type == rule_type])
                for rule_type in RuleType
            },
            'rules_by_severity': {
                severity.value: len([r for r in self.rules.values() if r.severity == severity])
                for severity in RuleSeverity
            },
            'mission_rule_sets': {
                name: len(rule_ids) for name, rule_ids in self.mission_rule_sets.items()
            }
        }
    
    def export_rules(self) -> Dict[str, Any]:
        """Export all rules for serialization"""
        return {
            'rules': {
                rule_id: {
                    'rule_type': rule.rule_type.value,
                    'severity': rule.severity.value,
                    'description': rule.description,
                    'source_modules': [m.value for m in rule.source_modules],
                    'target_modules': [m.value for m in rule.target_modules],
                    'distance_constraint': rule.distance_constraint,
                    'zone_constraint': rule.zone_constraint.value if rule.zone_constraint else None,
                    'conditions': rule.conditions,
                    'penalty_base': rule.penalty_base,
                    'penalty_multiplier': rule.penalty_multiplier
                }
                for rule_id, rule in self.rules.items()
            },
            'mission_rule_sets': self.mission_rule_sets
        }


# Factory function for easy instantiation
def create_layout_grammar() -> LayoutGrammar:
    """Create a new layout grammar instance"""
    return LayoutGrammar()


# Utility functions
def validate_layout_against_rules(
    modules: List[ModulePlacement],
    mission_params: Optional[MissionParameters] = None,
    rule_ids: Optional[List[str]] = None
) -> GrammarEvaluation:
    """
    Convenience function to validate a layout against grammar rules.
    
    Args:
        modules: Module placements to validate
        mission_params: Mission parameters for rule selection
        rule_ids: Specific rule IDs to apply
        
    Returns:
        Grammar evaluation results
    """
    grammar = create_layout_grammar()
    return grammar.evaluate_layout(modules, mission_params, rule_ids)


def get_adjacency_matrix(modules: List[ModulePlacement]) -> Dict[Tuple[str, str], float]:
    """
    Generate adjacency matrix for modules showing distances.
    
    Args:
        modules: List of module placements
        
    Returns:
        Dictionary mapping module pairs to distances
    """
    adjacency = {}
    
    for i, module1 in enumerate(modules):
        for module2 in modules[i+1:]:
            distance = np.linalg.norm(
                np.array(module1.position) - np.array(module2.position)
            )
            adjacency[(module1.module_id, module2.module_id)] = distance
            adjacency[(module2.module_id, module1.module_id)] = distance
    
    return adjacency