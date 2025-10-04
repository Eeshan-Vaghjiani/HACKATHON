// Unit tests for validation functions

import { describe, it, expect } from 'vitest';
import {
  validateEnvelopeSpec,
  validateModuleSpec,
  validateModulePlacement,
  validateLayoutSpec,
  validatePerformanceMetrics,
  validateMissionParameters,
  validateRequired,
  validateRange,
  validateEnum
} from '../types/validation';
import {
  EnvelopeSpec,
  ModuleSpec,
  ModulePlacement,
  LayoutSpec,
  PerformanceMetrics,
  MissionParameters,
  EnvelopeType,
  ModuleType,
  CoordinateFrame
} from '../types/index';

// ============================================================================
// TEST HELPERS
// ============================================================================

function createValidEnvelope(): EnvelopeSpec {
  return {
    id: 'env-001',
    type: EnvelopeType.CYLINDER,
    params: { radius: 3.0, length: 12.0 },
    coordinateFrame: CoordinateFrame.LOCAL,
    metadata: {
      name: 'Test Cylinder',
      creator: 'Test User',
      created: new Date('2024-01-01')
    }
  };
}

function createValidModule(): ModuleSpec {
  return {
    module_id: 'mod-001',
    type: ModuleType.SLEEP_QUARTER,
    name: 'Sleep Quarter A',
    bbox_m: { x: 2.0, y: 2.0, z: 2.5 },
    mass_kg: 500,
    power_w: 100,
    stowage_m3: 5.0,
    connectivity_ports: ['port1', 'port2'],
    adjacency_preferences: [ModuleType.GALLEY],
    adjacency_restrictions: [ModuleType.MECHANICAL]
  };
}

function createValidModulePlacement(): ModulePlacement {
  return {
    module_id: 'mod-001',
    type: ModuleType.SLEEP_QUARTER,
    position: [1.0, 2.0, 3.0],
    rotation_deg: 45,
    connections: ['mod-002']
  };
}

function createValidPerformanceMetrics(): PerformanceMetrics {
  return {
    meanTransitTime: 30.5,
    egressTime: 120.0,
    massTotal: 15000,
    powerBudget: 5000,
    thermalMargin: 0.25,
    lssMargin: 0.30,
    stowageUtilization: 0.85
  };
}

function createValidMissionParameters(): MissionParameters {
  return {
    crew_size: 4,
    duration_days: 180,
    priority_weights: {
      safety: 0.4,
      efficiency: 0.3,
      mass: 0.2,
      power: 0.1
    },
    activity_schedule: {
      sleep: 8,
      work: 8,
      exercise: 2,
      meals: 3,
      personal: 3
    },
    emergency_scenarios: ['fire', 'depressurization']
  };
}

// ============================================================================
// ENVELOPE VALIDATION TESTS
// ============================================================================

describe('validateEnvelopeSpec', () => {
  it('should validate a correct envelope specification', () => {
    const envelope = createValidEnvelope();
    const result = validateEnvelopeSpec(envelope);
    
    expect(result.isValid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  it('should reject envelope with missing ID', () => {
    const envelope = createValidEnvelope();
    envelope.id = '';
    
    const result = validateEnvelopeSpec(envelope);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'id',
        code: 'REQUIRED_FIELD'
      })
    );
  });

  it('should reject envelope with invalid type', () => {
    const envelope = createValidEnvelope();
    (envelope as any).type = 'invalid_type';
    
    const result = validateEnvelopeSpec(envelope);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'type',
        code: 'INVALID_ENUM_VALUE'
      })
    );
  });

  it('should reject cylinder with negative radius', () => {
    const envelope = createValidEnvelope();
    envelope.params.radius = -1.0;
    
    const result = validateEnvelopeSpec(envelope);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'params.radius',
        code: 'INVALID_RANGE'
      })
    );
  });

  it('should reject cylinder with zero length', () => {
    const envelope = createValidEnvelope();
    envelope.params.length = 0;
    
    const result = validateEnvelopeSpec(envelope);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'params.length',
        code: 'INVALID_RANGE'
      })
    );
  });

  it('should validate box envelope parameters', () => {
    const envelope = createValidEnvelope();
    envelope.type = EnvelopeType.BOX;
    envelope.params = { width: 5.0, height: 3.0, depth: 8.0 };
    
    const result = validateEnvelopeSpec(envelope);
    
    expect(result.isValid).toBe(true);
  });

  it('should reject box with missing dimensions', () => {
    const envelope = createValidEnvelope();
    envelope.type = EnvelopeType.BOX;
    envelope.params = { width: 5.0, height: 3.0 }; // missing depth
    
    const result = validateEnvelopeSpec(envelope);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'params.depth',
        code: 'INVALID_RANGE'
      })
    );
  });

  it('should validate torus envelope parameters', () => {
    const envelope = createValidEnvelope();
    envelope.type = EnvelopeType.TORUS;
    envelope.params = { majorRadius: 5.0, minorRadius: 2.0 };
    
    const result = validateEnvelopeSpec(envelope);
    
    expect(result.isValid).toBe(true);
  });

  it('should reject torus with minor radius >= major radius', () => {
    const envelope = createValidEnvelope();
    envelope.type = EnvelopeType.TORUS;
    envelope.params = { majorRadius: 2.0, minorRadius: 3.0 };
    
    const result = validateEnvelopeSpec(envelope);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'params.minorRadius',
        code: 'INVALID_RELATIONSHIP'
      })
    );
  });
});

// ============================================================================
// MODULE VALIDATION TESTS
// ============================================================================

describe('validateModuleSpec', () => {
  it('should validate a correct module specification', () => {
    const module = createValidModule();
    const result = validateModuleSpec(module);
    
    expect(result.isValid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  it('should reject module with missing ID', () => {
    const module = createValidModule();
    module.module_id = '';
    
    const result = validateModuleSpec(module);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'module_id',
        code: 'REQUIRED_FIELD'
      })
    );
  });

  it('should reject module with invalid type', () => {
    const module = createValidModule();
    (module as any).type = 'invalid_type';
    
    const result = validateModuleSpec(module);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'type',
        code: 'INVALID_ENUM_VALUE'
      })
    );
  });

  it('should reject module with negative mass', () => {
    const module = createValidModule();
    module.mass_kg = -100;
    
    const result = validateModuleSpec(module);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'mass_kg',
        code: 'BELOW_MINIMUM'
      })
    );
  });

  it('should reject module with negative power consumption', () => {
    const module = createValidModule();
    module.power_w = -50;
    
    const result = validateModuleSpec(module);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'power_w',
        code: 'BELOW_MINIMUM'
      })
    );
  });

  it('should reject module with zero dimensions', () => {
    const module = createValidModule();
    module.bbox_m.x = 0;
    
    const result = validateModuleSpec(module);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'bbox_m.x',
        code: 'INVALID_RANGE'
      })
    );
  });

  it('should reject module with conflicting adjacency rules', () => {
    const module = createValidModule();
    module.adjacency_preferences = [ModuleType.GALLEY, ModuleType.LABORATORY];
    module.adjacency_restrictions = [ModuleType.GALLEY, ModuleType.MECHANICAL];
    
    const result = validateModuleSpec(module);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'adjacency_preferences',
        code: 'CONFLICTING_CONSTRAINTS'
      })
    );
  });

  it('should warn about very high mass', () => {
    const module = createValidModule();
    module.mass_kg = 60000; // Above recommended maximum
    
    const result = validateModuleSpec(module);
    
    expect(result.isValid).toBe(true);
    expect(result.warnings).toContainEqual(
      expect.objectContaining({
        field: 'mass_kg',
        code: 'ABOVE_RECOMMENDED'
      })
    );
  });
});

// ============================================================================
// MODULE PLACEMENT VALIDATION TESTS
// ============================================================================

describe('validateModulePlacement', () => {
  it('should validate a correct module placement', () => {
    const placement = createValidModulePlacement();
    const result = validateModulePlacement(placement);
    
    expect(result.isValid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  it('should reject placement with invalid position array', () => {
    const placement = createValidModulePlacement();
    (placement as any).position = [1.0, 2.0]; // Missing Z coordinate
    
    const result = validateModulePlacement(placement);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'position',
        code: 'INVALID_FORMAT'
      })
    );
  });

  it('should reject placement with non-finite coordinates', () => {
    const placement = createValidModulePlacement();
    placement.position = [1.0, Infinity, 3.0];
    
    const result = validateModulePlacement(placement);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'position[1]',
        code: 'INVALID_TYPE'
      })
    );
  });

  it('should reject placement with non-finite rotation', () => {
    const placement = createValidModulePlacement();
    placement.rotation_deg = NaN;
    
    const result = validateModulePlacement(placement);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'rotation_deg',
        code: 'INVALID_TYPE'
      })
    );
  });

  it('should warn about rotation outside 0-360 range', () => {
    const placement = createValidModulePlacement();
    placement.rotation_deg = 450;
    
    const result = validateModulePlacement(placement);
    
    expect(result.isValid).toBe(true);
    expect(result.warnings).toContainEqual(
      expect.objectContaining({
        field: 'rotation_deg',
        code: 'NORMALIZATION_RECOMMENDED'
      })
    );
  });

  it('should reject placement with non-array connections', () => {
    const placement = createValidModulePlacement();
    (placement as any).connections = 'not-an-array';
    
    const result = validateModulePlacement(placement);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'connections',
        code: 'INVALID_TYPE'
      })
    );
  });
});

// ============================================================================
// PERFORMANCE METRICS VALIDATION TESTS
// ============================================================================

describe('validatePerformanceMetrics', () => {
  it('should validate correct performance metrics', () => {
    const metrics = createValidPerformanceMetrics();
    const result = validatePerformanceMetrics(metrics);
    
    expect(result.isValid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  it('should reject metrics with negative values', () => {
    const metrics = createValidPerformanceMetrics();
    metrics.meanTransitTime = -10;
    
    const result = validatePerformanceMetrics(metrics);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'meanTransitTime',
        code: 'BELOW_MINIMUM'
      })
    );
  });

  it('should reject metrics with non-finite values', () => {
    const metrics = createValidPerformanceMetrics();
    metrics.powerBudget = Infinity;
    
    const result = validatePerformanceMetrics(metrics);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'powerBudget',
        code: 'INVALID_TYPE'
      })
    );
  });

  it('should warn about high stowage utilization', () => {
    const metrics = createValidPerformanceMetrics();
    metrics.stowageUtilization = 1.2; // 120%
    
    const result = validatePerformanceMetrics(metrics);
    
    expect(result.isValid).toBe(true);
    expect(result.warnings).toContainEqual(
      expect.objectContaining({
        field: 'stowageUtilization',
        code: 'ABOVE_RECOMMENDED'
      })
    );
  });

  it('should warn about low thermal margin', () => {
    const metrics = createValidPerformanceMetrics();
    metrics.thermalMargin = 0.05; // 5%
    
    const result = validatePerformanceMetrics(metrics);
    
    expect(result.isValid).toBe(true);
    expect(result.warnings).toContainEqual(
      expect.objectContaining({
        field: 'thermalMargin',
        code: 'BELOW_RECOMMENDED'
      })
    );
  });

  it('should warn about low LSS margin', () => {
    const metrics = createValidPerformanceMetrics();
    metrics.lssMargin = 0.15; // 15%
    
    const result = validatePerformanceMetrics(metrics);
    
    expect(result.isValid).toBe(true);
    expect(result.warnings).toContainEqual(
      expect.objectContaining({
        field: 'lssMargin',
        code: 'BELOW_RECOMMENDED'
      })
    );
  });
});

// ============================================================================
// MISSION PARAMETERS VALIDATION TESTS
// ============================================================================

describe('validateMissionParameters', () => {
  it('should validate correct mission parameters', () => {
    const mission = createValidMissionParameters();
    const result = validateMissionParameters(mission);
    
    expect(result.isValid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  it('should reject mission with zero crew size', () => {
    const mission = createValidMissionParameters();
    mission.crew_size = 0;
    
    const result = validateMissionParameters(mission);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'crew_size',
        code: 'BELOW_MINIMUM'
      })
    );
  });

  it('should reject mission with non-integer crew size', () => {
    const mission = createValidMissionParameters();
    mission.crew_size = 3.5;
    
    const result = validateMissionParameters(mission);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'crew_size',
        code: 'BELOW_MINIMUM'
      })
    );
  });

  it('should reject mission with zero duration', () => {
    const mission = createValidMissionParameters();
    mission.duration_days = 0;
    
    const result = validateMissionParameters(mission);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'duration_days',
        code: 'BELOW_MINIMUM'
      })
    );
  });

  it('should reject mission with priority weights not summing to 1.0', () => {
    const mission = createValidMissionParameters();
    mission.priority_weights = {
      safety: 0.5,
      efficiency: 0.3,
      mass: 0.1,
      power: 0.05 // Sum = 0.95
    };
    
    const result = validateMissionParameters(mission);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'priority_weights',
        code: 'INVALID_SUM'
      })
    );
  });

  it('should reject mission with negative priority weights', () => {
    const mission = createValidMissionParameters();
    mission.priority_weights.safety = -0.1;
    mission.priority_weights.efficiency = 0.5; // Adjust to maintain sum
    
    const result = validateMissionParameters(mission);
    
    expect(result.isValid).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({
        field: 'priority_weights.safety',
        code: 'BELOW_MINIMUM'
      })
    );
  });

  it('should warn about very large crew size', () => {
    const mission = createValidMissionParameters();
    mission.crew_size = 25;
    
    const result = validateMissionParameters(mission);
    
    expect(result.isValid).toBe(true);
    expect(result.warnings).toContainEqual(
      expect.objectContaining({
        field: 'crew_size',
        code: 'ABOVE_RECOMMENDED'
      })
    );
  });

  it('should warn about activity schedule exceeding 24 hours', () => {
    const mission = createValidMissionParameters();
    mission.activity_schedule = {
      sleep: 8,
      work: 10,
      exercise: 3,
      meals: 4,
      personal: 2 // Total = 27 hours
    };
    
    const result = validateMissionParameters(mission);
    
    expect(result.isValid).toBe(true);
    expect(result.warnings).toContainEqual(
      expect.objectContaining({
        field: 'activity_schedule',
        code: 'ABOVE_MAXIMUM'
      })
    );
  });
});

// ============================================================================
// UTILITY VALIDATION FUNCTION TESTS
// ============================================================================

describe('validateRequired', () => {
  it('should return null for valid values', () => {
    expect(validateRequired('valid string', 'testField')).toBeNull();
    expect(validateRequired(123, 'testField')).toBeNull();
    expect(validateRequired(true, 'testField')).toBeNull();
  });

  it('should return error for null/undefined values', () => {
    expect(validateRequired(null, 'testField')).toEqual(
      expect.objectContaining({
        field: 'testField',
        code: 'REQUIRED_FIELD'
      })
    );
    expect(validateRequired(undefined, 'testField')).toEqual(
      expect.objectContaining({
        field: 'testField',
        code: 'REQUIRED_FIELD'
      })
    );
  });

  it('should return error for empty strings', () => {
    expect(validateRequired('', 'testField')).toEqual(
      expect.objectContaining({
        field: 'testField',
        code: 'REQUIRED_FIELD'
      })
    );
    expect(validateRequired('   ', 'testField')).toEqual(
      expect.objectContaining({
        field: 'testField',
        code: 'REQUIRED_FIELD'
      })
    );
  });
});

describe('validateRange', () => {
  it('should return null for values within range', () => {
    expect(validateRange(5, 0, 10, 'testField')).toBeNull();
    expect(validateRange(0, 0, 10, 'testField')).toBeNull();
    expect(validateRange(10, 0, 10, 'testField')).toBeNull();
  });

  it('should return error for values below minimum', () => {
    expect(validateRange(-1, 0, 10, 'testField')).toEqual(
      expect.objectContaining({
        field: 'testField',
        code: 'BELOW_MINIMUM'
      })
    );
  });

  it('should return error for values above maximum', () => {
    expect(validateRange(11, 0, 10, 'testField')).toEqual(
      expect.objectContaining({
        field: 'testField',
        code: 'ABOVE_MAXIMUM'
      })
    );
  });
});

describe('validateEnum', () => {
  const TestEnum = {
    VALUE1: 'value1',
    VALUE2: 'value2',
    VALUE3: 'value3'
  } as const;

  it('should return null for valid enum values', () => {
    expect(validateEnum('value1', TestEnum, 'testField')).toBeNull();
    expect(validateEnum('value2', TestEnum, 'testField')).toBeNull();
    expect(validateEnum('value3', TestEnum, 'testField')).toBeNull();
  });

  it('should return error for invalid enum values', () => {
    expect(validateEnum('invalid', TestEnum, 'testField')).toEqual(
      expect.objectContaining({
        field: 'testField',
        code: 'INVALID_ENUM_VALUE'
      })
    );
  });
});