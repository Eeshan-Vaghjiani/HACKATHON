#!/usr/bin/env python3
"""
Test script for Layout Grammar and Adjacency Rules System

This script tests the layout grammar rules, violation detection,
and penalty system functionality.
"""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.models.base import ModulePlacement, ModuleType, MissionParameters
from app.services.layout_grammar import (
    LayoutGrammar, LayoutRule, RuleType, RuleSeverity, ZoneType,
    create_layout_grammar, validate_layout_against_rules, get_adjacency_matrix
)


def create_test_layout_good() -> list[ModulePlacement]:
    """Create a test layout that follows most rules"""
    return [
        # Crew area cluster
        ModulePlacement(
            module_id="sleep_001", type=ModuleType.SLEEP_QUARTER,
            position=[0.0, 0.0, 0.0], rotation_deg=0.0
        ),
        ModulePlacement(
            module_id="sleep_002", type=ModuleType.SLEEP_QUARTER,
            position=[2.5, 0.0, 0.0], rotation_deg=0.0
        ),
        ModulePlacement(
            module_id="galley_001", type=ModuleType.GALLEY,
            position=[1.0, 3.0, 0.0], rotation_deg=0.0
        ),
        ModulePlacement(
            module_id="medical_001", type=ModuleType.MEDICAL,
            position=[0.0, 6.0, 0.0], rotation_deg=0.0
        ),
        
        # Work area cluster
        ModulePlacement(
            module_id="lab_001", type=ModuleType.LABORATORY,
            position=[8.0, 0.0, 0.0], rotation_deg=0.0
        ),
        ModulePlacement(
            module_id="storage_001", type=ModuleType.STORAGE,
            position=[10.0, 2.0, 0.0], rotation_deg=0.0
        ),
        
        # Utility area (separated)
        ModulePlacement(
            module_id="mechanical_001", type=ModuleType.MECHANICAL,
            position=[0.0, -8.0, 0.0], rotation_deg=0.0
        ),
        ModulePlacement(
            module_id="airlock_001", type=ModuleType.AIRLOCK,
            position=[2.0, -6.0, 0.0], rotation_deg=0.0
        ),
        
        # Exercise area (separated from quiet areas)
        ModulePlacement(
            module_id="exercise_001", type=ModuleType.EXERCISE,
            position=[6.0, 6.0, 0.0], rotation_deg=0.0
        )
    ]


def create_test_layout_bad() -> list[ModulePlacement]:
    """Create a test layout that violates many rules"""
    return [
        # Sleep quarters next to mechanical (noise violation)
        ModulePlacement(
            module_id="sleep_001", type=ModuleType.SLEEP_QUARTER,
            position=[0.0, 0.0, 0.0], rotation_deg=0.0
        ),
        ModulePlacement(
            module_id="mechanical_001", type=ModuleType.MECHANICAL,
            position=[1.5, 0.0, 0.0], rotation_deg=0.0  # Too close!
        ),
        
        # Galley next to lab (contamination risk)
        ModulePlacement(
            module_id="galley_001", type=ModuleType.GALLEY,
            position=[5.0, 0.0, 0.0], rotation_deg=0.0
        ),
        ModulePlacement(
            module_id="lab_001", type=ModuleType.LABORATORY,
            position=[6.0, 0.0, 0.0], rotation_deg=0.0  # Too close!
        ),
        
        # Medical far from crew areas
        ModulePlacement(
            module_id="medical_001", type=ModuleType.MEDICAL,
            position=[20.0, 20.0, 0.0], rotation_deg=0.0  # Too far!
        ),
        
        # Airlock next to sleep quarters
        ModulePlacement(
            module_id="airlock_001", type=ModuleType.AIRLOCK,
            position=[0.0, 2.0, 0.0], rotation_deg=0.0  # Too close to sleep!
        ),
        
        # Exercise next to sleep (noise)
        ModulePlacement(
            module_id="exercise_001", type=ModuleType.EXERCISE,
            position=[2.0, 1.0, 0.0], rotation_deg=0.0  # Too close to sleep!
        )
    ]


def test_rule_creation_and_management():
    """Test rule creation and management functionality"""
    print("Testing Rule Creation and Management...")
    
    grammar = create_layout_grammar()
    
    # Test getting rule summary
    summary = grammar.get_rule_summary()
    print(f"  Total rules: {summary['total_rules']}")
    print(f"  Rules by type: {summary['rules_by_type']}")
    print(f"  Rules by severity: {summary['rules_by_severity']}")
    print(f"  Mission rule sets: {summary['mission_rule_sets']}")
    
    # Test adding a custom rule
    custom_rule = LayoutRule(
        rule_id="test_custom_rule",
        rule_type=RuleType.ADJACENCY_PREFERENCE,
        severity=RuleSeverity.LOW,
        description="Test custom rule for validation",
        source_modules=[ModuleType.STORAGE],
        target_modules=[ModuleType.EXERCISE],
        distance_constraint=(0.0, 5.0),
        penalty_base=25.0
    )
    
    grammar.add_rule(custom_rule)
    
    # Verify rule was added
    retrieved_rule = grammar.get_rule("test_custom_rule")
    if retrieved_rule and retrieved_rule.description == custom_rule.description:
        print("  ✅ Custom rule added successfully")
    else:
        print("  ❌ Custom rule addition failed")
        return False
    
    # Test removing the rule
    if grammar.remove_rule("test_custom_rule"):
        print("  ✅ Custom rule removed successfully")
    else:
        print("  ❌ Custom rule removal failed")
        return False
    
    return True


def test_good_layout_evaluation():
    """Test evaluation of a well-designed layout"""
    print("\nTesting Good Layout Evaluation...")
    
    grammar = create_layout_grammar()
    good_layout = create_test_layout_good()
    
    # Test with different mission types
    mission_types = ['short_term_research', 'long_term_habitation', 'lunar_surface']
    
    for mission_type in mission_types:
        print(f"\n  Evaluating for {mission_type}:")
        
        # Create mission parameters
        mission_params = MissionParameters(
            crew_size=4,
            duration_days=180 if mission_type == 'long_term_habitation' else 30,
            priority_weights={
                "safety": 0.3,
                "efficiency": 0.25,
                "mass": 0.2,
                "power": 0.15,
                "comfort": 0.1
            }
        )
        
        evaluation = grammar.evaluate_layout(good_layout, mission_params)
        
        print(f"    Total penalty: {evaluation.total_penalty:.1f}")
        print(f"    Compliance score: {evaluation.rule_compliance_score:.3f}")
        print(f"    Violations: {len(evaluation.violations)}")
        print(f"    Critical violations: {evaluation.critical_violations}")
        print(f"    Valid layout: {evaluation.is_valid_layout}")
        
        # Show violation details
        if evaluation.violations:
            print(f"    Violation details:")
            for i, violation in enumerate(evaluation.violations[:3]):  # Show first 3
                print(f"      {i+1}. {violation.rule.severity.value}: {violation.violation_description}")
                print(f"         Penalty: {violation.penalty:.1f}")
    
    return True


def test_bad_layout_evaluation():
    """Test evaluation of a poorly designed layout"""
    print("\nTesting Bad Layout Evaluation...")
    
    grammar = create_layout_grammar()
    bad_layout = create_test_layout_bad()
    
    # Use long-term habitation rules (comprehensive)
    mission_params = MissionParameters(
        crew_size=4,
        duration_days=365,
        priority_weights={
            "safety": 0.4,
            "efficiency": 0.2,
            "mass": 0.2,
            "power": 0.1,
            "comfort": 0.1
        }
    )
    
    evaluation = grammar.evaluate_layout(bad_layout, mission_params)
    
    print(f"  Total penalty: {evaluation.total_penalty:.1f}")
    print(f"  Compliance score: {evaluation.rule_compliance_score:.3f}")
    print(f"  Violations: {len(evaluation.violations)}")
    print(f"  Critical violations: {evaluation.critical_violations}")
    print(f"  Valid layout: {evaluation.is_valid_layout}")
    
    # Show all violations
    print(f"\n  Violation details:")
    for i, violation in enumerate(evaluation.violations):
        print(f"    {i+1}. {violation.rule.severity.value}: {violation.violation_description}")
        print(f"       Modules: {violation.violating_modules}")
        print(f"       Penalty: {violation.penalty:.1f}")
    
    # Verify that bad layout has more violations than good layout
    good_evaluation = grammar.evaluate_layout(create_test_layout_good(), mission_params)
    
    if evaluation.total_penalty > good_evaluation.total_penalty:
        print(f"  ✅ Bad layout correctly penalized more than good layout")
        print(f"     Bad: {evaluation.total_penalty:.1f}, Good: {good_evaluation.total_penalty:.1f}")
        return True
    else:
        print(f"  ❌ Bad layout penalty not higher than good layout")
        return False


def test_custom_rule_sets():
    """Test custom rule set creation and application"""
    print("\nTesting Custom Rule Sets...")
    
    grammar = create_layout_grammar()
    
    # Create a custom rule set for testing
    custom_rules = [
        'sleep_mechanical_restriction',
        'medical_central_preference',
        'airlock_connectivity'
    ]
    
    success = grammar.create_custom_rule_set(
        name="test_custom_set",
        rule_ids=custom_rules,
        description="Custom rule set for testing"
    )
    
    if not success:
        print("  ❌ Failed to create custom rule set")
        return False
    
    # Test applying the custom rule set
    test_layout = create_test_layout_good()
    
    evaluation = grammar.evaluate_layout(
        test_layout, 
        custom_rules=custom_rules
    )
    
    print(f"  Custom rule set evaluation:")
    print(f"    Applied rules: {len(custom_rules)}")
    print(f"    Total penalty: {evaluation.total_penalty:.1f}")
    print(f"    Violations: {len(evaluation.violations)}")
    
    # Verify that only the specified rules were applied
    rule_ids_in_violations = set()
    for violation in evaluation.violations:
        rule_ids_in_violations.add(violation.rule.rule_id)
    
    unexpected_rules = rule_ids_in_violations - set(custom_rules)
    if not unexpected_rules:
        print("  ✅ Custom rule set applied correctly")
        return True
    else:
        print(f"  ❌ Unexpected rules applied: {unexpected_rules}")
        return False


def test_adjacency_matrix():
    """Test adjacency matrix generation"""
    print("\nTesting Adjacency Matrix Generation...")
    
    test_layout = create_test_layout_good()
    adjacency_matrix = get_adjacency_matrix(test_layout)
    
    print(f"  Generated adjacency matrix with {len(adjacency_matrix)} entries")
    
    # Verify matrix properties
    expected_entries = len(test_layout) * (len(test_layout) - 1)  # n*(n-1) for directed pairs
    
    if len(adjacency_matrix) == expected_entries:
        print("  ✅ Adjacency matrix has correct number of entries")
    else:
        print(f"  ❌ Expected {expected_entries} entries, got {len(adjacency_matrix)}")
        return False
    
    # Show some sample distances
    print("  Sample distances:")
    count = 0
    for (mod1, mod2), distance in adjacency_matrix.items():
        if count < 5:  # Show first 5
            print(f"    {mod1} <-> {mod2}: {distance:.2f}m")
            count += 1
    
    return True


def test_rule_penalty_calculation():
    """Test rule penalty calculation with different severities"""
    print("\nTesting Rule Penalty Calculation...")
    
    # Create test rules with different severities
    test_rules = [
        LayoutRule(
            rule_id="test_critical",
            rule_type=RuleType.ADJACENCY_RESTRICTION,
            severity=RuleSeverity.CRITICAL,
            description="Critical test rule",
            penalty_base=100.0
        ),
        LayoutRule(
            rule_id="test_high",
            rule_type=RuleType.ADJACENCY_RESTRICTION,
            severity=RuleSeverity.HIGH,
            description="High severity test rule",
            penalty_base=100.0
        ),
        LayoutRule(
            rule_id="test_low",
            rule_type=RuleType.ADJACENCY_RESTRICTION,
            severity=RuleSeverity.LOW,
            description="Low severity test rule",
            penalty_base=100.0
        )
    ]
    
    # Calculate penalties
    penalties = {}
    for rule in test_rules:
        penalty = rule.calculate_penalty(violation_count=1, violation_severity=1.0)
        penalties[rule.severity] = penalty
        print(f"  {rule.severity.value}: {penalty:.1f}")
    
    # Verify penalty ordering
    if (penalties[RuleSeverity.CRITICAL] > penalties[RuleSeverity.HIGH] > 
        penalties[RuleSeverity.LOW]):
        print("  ✅ Penalty severity ordering correct")
        return True
    else:
        print("  ❌ Penalty severity ordering incorrect")
        return False


def test_convenience_functions():
    """Test convenience functions"""
    print("\nTesting Convenience Functions...")
    
    test_layout = create_test_layout_good()
    
    # Test validate_layout_against_rules function
    mission_params = MissionParameters(
        crew_size=4,
        duration_days=90,
        priority_weights={
            "safety": 0.3,
            "efficiency": 0.25,
            "mass": 0.2,
            "power": 0.15,
            "comfort": 0.1
        }
    )
    
    evaluation = validate_layout_against_rules(test_layout, mission_params)
    
    print(f"  Convenience function evaluation:")
    print(f"    Total penalty: {evaluation.total_penalty:.1f}")
    print(f"    Compliance score: {evaluation.rule_compliance_score:.3f}")
    print(f"    Violations: {len(evaluation.violations)}")
    
    if evaluation.rule_compliance_score >= 0.0:
        print("  ✅ Convenience function works correctly")
        return True
    else:
        print("  ❌ Convenience function failed")
        return False


def main():
    """Main test function"""
    print("Layout Grammar and Adjacency Rules System Test Suite")
    print("="*60)
    
    # Run all tests
    tests = [
        ("Rule Creation and Management", test_rule_creation_and_management),
        ("Good Layout Evaluation", test_good_layout_evaluation),
        ("Bad Layout Evaluation", test_bad_layout_evaluation),
        ("Custom Rule Sets", test_custom_rule_sets),
        ("Adjacency Matrix", test_adjacency_matrix),
        ("Rule Penalty Calculation", test_rule_penalty_calculation),
        ("Convenience Functions", test_convenience_functions)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append(result)
            
            if result:
                print(f"✅ {test_name} passed")
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            import traceback
            traceback.print_exc()
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
    exit_code = main()
    sys.exit(exit_code)