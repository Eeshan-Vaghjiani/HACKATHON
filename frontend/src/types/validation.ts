// Validation functions for HabitatCanvas data models

import {
  EnvelopeSpec,
  LayoutSpec,
  ModuleSpec,
  ModulePlacement,
  PerformanceMetrics,
  MissionParameters,
  ValidationResult,
  ValidationError,
  ValidationWarning,
  EnvelopeType,
  ModuleType,
  CoordinateFrame
} from './index';

// ============================================================================
// VALIDATION CONSTANTS
// ============================================================================

const VALIDATION_CONSTANTS = {
  ENVELOPE: {
    MIN_DIMENSION: 0.1, // meters
    MAX_DIMENSION: 100, // meters
    MIN_VOLUME: 0.001, // cubic meters
    MAX_VOLUME: 10000, // cubic meters
  },
  MODULE: {
    MIN_MASS: 0.1, // kg
    MAX_MASS: 50000, // kg
    MIN_POWER: 0, // watts
    MAX_POWER: 100000, // watts
    MIN_STOWAGE: 0, // cubic meters
    MAX_STOWAGE: 1000, // cubic meters
  },
  MISSION: {
    MIN_CREW_SIZE: 1,
    MAX_CREW_SIZE: 20,
    MIN_DURATION: 1, // days
    MAX_DURATION: 1000, // days
  },
  GEOMETRY: {
    MIN_CLEARANCE: 0.6, // meters (minimum walkway width)
    EMERGENCY_CLEARANCE: 1.2, // meters (emergency egress width)
    MAX_REACH: 2.0, // meters (maximum reach distance)
  }
} as const;

// ============================================================================
// ENVELOPE VALIDATION
// ============================================================================

export function validateEnvelopeSpec(envelope: EnvelopeSpec): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationWarning[] = [];

  // Validate ID
  if (!envelope.id || envelope.id.trim().length === 0) {
    errors.push({
      field: 'id',
      message: 'Envelope ID is required',
      code: 'REQUIRED_FIELD',
      value: envelope.id
    });
  }

  // Validate type
  if (!Object.values(EnvelopeType).includes(envelope.type)) {
    errors.push({
      field: 'type',
      message: `Invalid envelope type: ${envelope.type}`,
      code: 'INVALID_ENUM_VALUE',
      value: envelope.type
    });
  }

  // Validate coordinate frame
  if (!Object.values(CoordinateFrame).includes(envelope.coordinateFrame)) {
    errors.push({
      field: 'coordinateFrame',
      message: `Invalid coordinate frame: ${envelope.coordinateFrame}`,
      code: 'INVALID_ENUM_VALUE',
      value: envelope.coordinateFrame
    });
  }

  // Validate parameters based on type
  const paramValidation = validateEnvelopeParameters(envelope.type, envelope.params);
  errors.push(...paramValidation.errors);
  warnings.push(...paramValidation.warnings);

  // Validate metadata
  if (!envelope.metadata.name || envelope.metadata.name.trim().length === 0) {
    errors.push({
      field: 'metadata.name',
      message: 'Envelope name is required',
      code: 'REQUIRED_FIELD',
      value: envelope.metadata.name
    });
  }

  if (!envelope.metadata.creator || envelope.metadata.creator.trim().length === 0) {
    warnings.push({
      field: 'metadata.creator',
      message: 'Creator information is recommended',
      code: 'RECOMMENDED_FIELD',
      value: envelope.metadata.creator
    });
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
}

function validateEnvelopeParameters(type: EnvelopeType, params: Record<string, number>): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationWarning[] = [];

  switch (type) {
    case EnvelopeType.CYLINDER:
      if (!params.radius || params.radius <= 0) {
        errors.push({
          field: 'params.radius',
          message: 'Cylinder radius must be positive',
          code: 'INVALID_RANGE',
          value: params.radius
        });
      } else if (params.radius < VALIDATION_CONSTANTS.ENVELOPE.MIN_DIMENSION) {
        errors.push({
          field: 'params.radius',
          message: `Cylinder radius must be at least ${VALIDATION_CONSTANTS.ENVELOPE.MIN_DIMENSION}m`,
          code: 'BELOW_MINIMUM',
          value: params.radius
        });
      } else if (params.radius > VALIDATION_CONSTANTS.ENVELOPE.MAX_DIMENSION) {
        warnings.push({
          field: 'params.radius',
          message: `Cylinder radius ${params.radius}m is very large`,
          code: 'ABOVE_RECOMMENDED',
          value: params.radius
        });
      }

      if (!params.length || params.length <= 0) {
        errors.push({
          field: 'params.length',
          message: 'Cylinder length must be positive',
          code: 'INVALID_RANGE',
          value: params.length
        });
      } else if (params.length < VALIDATION_CONSTANTS.ENVELOPE.MIN_DIMENSION) {
        errors.push({
          field: 'params.length',
          message: `Cylinder length must be at least ${VALIDATION_CONSTANTS.ENVELOPE.MIN_DIMENSION}m`,
          code: 'BELOW_MINIMUM',
          value: params.length
        });
      }
      break;

    case EnvelopeType.BOX:
      ['width', 'height', 'depth'].forEach(dim => {
        if (!params[dim] || params[dim] <= 0) {
          errors.push({
            field: `params.${dim}`,
            message: `Box ${dim} must be positive`,
            code: 'INVALID_RANGE',
            value: params[dim]
          });
        } else if (params[dim] < VALIDATION_CONSTANTS.ENVELOPE.MIN_DIMENSION) {
          errors.push({
            field: `params.${dim}`,
            message: `Box ${dim} must be at least ${VALIDATION_CONSTANTS.ENVELOPE.MIN_DIMENSION}m`,
            code: 'BELOW_MINIMUM',
            value: params[dim]
          });
        }
      });
      break;

    case EnvelopeType.TORUS:
      if (!params.majorRadius || params.majorRadius <= 0) {
        errors.push({
          field: 'params.majorRadius',
          message: 'Torus major radius must be positive',
          code: 'INVALID_RANGE',
          value: params.majorRadius
        });
      }

      if (!params.minorRadius || params.minorRadius <= 0) {
        errors.push({
          field: 'params.minorRadius',
          message: 'Torus minor radius must be positive',
          code: 'INVALID_RANGE',
          value: params.minorRadius
        });
      }

      if (params.majorRadius && params.minorRadius && params.minorRadius >= params.majorRadius) {
        errors.push({
          field: 'params.minorRadius',
          message: 'Minor radius must be less than major radius',
          code: 'INVALID_RELATIONSHIP',
          value: params.minorRadius
        });
      }
      break;

    case EnvelopeType.FREEFORM:
      // Freeform validation would require more complex geometry checks
      if (!params.volume || params.volume <= 0) {
        warnings.push({
          field: 'params.volume',
          message: 'Freeform envelope should specify volume',
          code: 'RECOMMENDED_FIELD',
          value: params.volume
        });
      }
      break;
  }

  return { isValid: errors.length === 0, errors, warnings };
}

// ============================================================================
// MODULE VALIDATION
// ============================================================================

export function validateModuleSpec(module: ModuleSpec): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationWarning[] = [];

  // Validate ID
  if (!module.module_id || module.module_id.trim().length === 0) {
    errors.push({
      field: 'module_id',
      message: 'Module ID is required',
      code: 'REQUIRED_FIELD',
      value: module.module_id
    });
  }

  // Validate type
  if (!Object.values(ModuleType).includes(module.type)) {
    errors.push({
      field: 'type',
      message: `Invalid module type: ${module.type}`,
      code: 'INVALID_ENUM_VALUE',
      value: module.type
    });
  }

  // Validate name
  if (!module.name || module.name.trim().length === 0) {
    errors.push({
      field: 'name',
      message: 'Module name is required',
      code: 'REQUIRED_FIELD',
      value: module.name
    });
  }

  // Validate bounding box
  if (!module.bbox_m || typeof module.bbox_m !== 'object') {
    errors.push({
      field: 'bbox_m',
      message: 'Module bounding box is required',
      code: 'REQUIRED_FIELD',
      value: module.bbox_m
    });
  } else {
    ['x', 'y', 'z'].forEach(axis => {
      if (!module.bbox_m[axis] || module.bbox_m[axis] <= 0) {
        errors.push({
          field: `bbox_m.${axis}`,
          message: `Module ${axis} dimension must be positive`,
          code: 'INVALID_RANGE',
          value: module.bbox_m[axis]
        });
      }
    });
  }

  // Validate mass
  if (module.mass_kg < VALIDATION_CONSTANTS.MODULE.MIN_MASS) {
    errors.push({
      field: 'mass_kg',
      message: `Module mass must be at least ${VALIDATION_CONSTANTS.MODULE.MIN_MASS}kg`,
      code: 'BELOW_MINIMUM',
      value: module.mass_kg
    });
  } else if (module.mass_kg > VALIDATION_CONSTANTS.MODULE.MAX_MASS) {
    warnings.push({
      field: 'mass_kg',
      message: `Module mass ${module.mass_kg}kg is very high`,
      code: 'ABOVE_RECOMMENDED',
      value: module.mass_kg
    });
  }

  // Validate power
  if (module.power_w < VALIDATION_CONSTANTS.MODULE.MIN_POWER) {
    errors.push({
      field: 'power_w',
      message: 'Module power consumption cannot be negative',
      code: 'BELOW_MINIMUM',
      value: module.power_w
    });
  } else if (module.power_w > VALIDATION_CONSTANTS.MODULE.MAX_POWER) {
    warnings.push({
      field: 'power_w',
      message: `Module power consumption ${module.power_w}W is very high`,
      code: 'ABOVE_RECOMMENDED',
      value: module.power_w
    });
  }

  // Validate stowage
  if (module.stowage_m3 < VALIDATION_CONSTANTS.MODULE.MIN_STOWAGE) {
    errors.push({
      field: 'stowage_m3',
      message: 'Module stowage volume cannot be negative',
      code: 'BELOW_MINIMUM',
      value: module.stowage_m3
    });
  }

  // Validate adjacency preferences and restrictions don't conflict
  const conflictingTypes = module.adjacency_preferences.filter(pref => 
    module.adjacency_restrictions.includes(pref)
  );
  if (conflictingTypes.length > 0) {
    errors.push({
      field: 'adjacency_preferences',
      message: `Module types cannot be both preferred and restricted: ${conflictingTypes.join(', ')}`,
      code: 'CONFLICTING_CONSTRAINTS',
      value: conflictingTypes
    });
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
}

export function validateModulePlacement(placement: ModulePlacement): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationWarning[] = [];

  // Validate module ID
  if (!placement.module_id || placement.module_id.trim().length === 0) {
    errors.push({
      field: 'module_id',
      message: 'Module ID is required',
      code: 'REQUIRED_FIELD',
      value: placement.module_id
    });
  }

  // Validate type
  if (!Object.values(ModuleType).includes(placement.type)) {
    errors.push({
      field: 'type',
      message: `Invalid module type: ${placement.type}`,
      code: 'INVALID_ENUM_VALUE',
      value: placement.type
    });
  }

  // Validate position
  if (!Array.isArray(placement.position) || placement.position.length !== 3) {
    errors.push({
      field: 'position',
      message: 'Position must be a 3D coordinate array [x, y, z]',
      code: 'INVALID_FORMAT',
      value: placement.position
    });
  } else {
    placement.position.forEach((coord, index) => {
      if (typeof coord !== 'number' || !isFinite(coord)) {
        errors.push({
          field: `position[${index}]`,
          message: 'Position coordinates must be finite numbers',
          code: 'INVALID_TYPE',
          value: coord
        });
      }
    });
  }

  // Validate rotation
  if (typeof placement.rotation_deg !== 'number' || !isFinite(placement.rotation_deg)) {
    errors.push({
      field: 'rotation_deg',
      message: 'Rotation must be a finite number',
      code: 'INVALID_TYPE',
      value: placement.rotation_deg
    });
  } else if (placement.rotation_deg < 0 || placement.rotation_deg >= 360) {
    warnings.push({
      field: 'rotation_deg',
      message: 'Rotation should be normalized to 0-360 degrees',
      code: 'NORMALIZATION_RECOMMENDED',
      value: placement.rotation_deg
    });
  }

  // Validate connections
  if (!Array.isArray(placement.connections)) {
    errors.push({
      field: 'connections',
      message: 'Connections must be an array of module IDs',
      code: 'INVALID_TYPE',
      value: placement.connections
    });
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
}

// ============================================================================
// LAYOUT VALIDATION
// ============================================================================

export function validateLayoutSpec(layout: LayoutSpec): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationWarning[] = [];

  // Validate IDs
  if (!layout.layoutId || layout.layoutId.trim().length === 0) {
    errors.push({
      field: 'layoutId',
      message: 'Layout ID is required',
      code: 'REQUIRED_FIELD',
      value: layout.layoutId
    });
  }

  if (!layout.envelopeId || layout.envelopeId.trim().length === 0) {
    errors.push({
      field: 'envelopeId',
      message: 'Envelope ID is required',
      code: 'REQUIRED_FIELD',
      value: layout.envelopeId
    });
  }

  // Validate modules
  if (!Array.isArray(layout.modules)) {
    errors.push({
      field: 'modules',
      message: 'Modules must be an array',
      code: 'INVALID_TYPE',
      value: layout.modules
    });
  } else {
    // Validate each module placement
    layout.modules.forEach((module, index) => {
      const moduleValidation = validateModulePlacement(module);
      moduleValidation.errors.forEach(error => {
        errors.push({
          ...error,
          field: `modules[${index}].${error.field}`
        });
      });
      moduleValidation.warnings.forEach(warning => {
        warnings.push({
          ...warning,
          field: `modules[${index}].${warning.field}`
        });
      });
    });

    // Check for duplicate module IDs
    const moduleIds = layout.modules.map(m => m.module_id);
    const duplicateIds = moduleIds.filter((id, index) => moduleIds.indexOf(id) !== index);
    if (duplicateIds.length > 0) {
      errors.push({
        field: 'modules',
        message: `Duplicate module IDs found: ${duplicateIds.join(', ')}`,
        code: 'DUPLICATE_VALUES',
        value: duplicateIds
      });
    }
  }

  // Validate performance metrics
  const metricsValidation = validatePerformanceMetrics(layout.kpis);
  errors.push(...metricsValidation.errors);
  warnings.push(...metricsValidation.warnings);

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
}

// ============================================================================
// PERFORMANCE METRICS VALIDATION
// ============================================================================

export function validatePerformanceMetrics(metrics: PerformanceMetrics): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationWarning[] = [];

  // Validate required numeric fields
  const requiredFields = [
    'meanTransitTime', 'egressTime', 'massTotal', 'powerBudget',
    'thermalMargin', 'lssMargin', 'stowageUtilization'
  ];

  requiredFields.forEach(field => {
    const value = metrics[field as keyof PerformanceMetrics];
    if (typeof value !== 'number' || !isFinite(value)) {
      errors.push({
        field,
        message: `${field} must be a finite number`,
        code: 'INVALID_TYPE',
        value
      });
    } else if (value < 0) {
      errors.push({
        field,
        message: `${field} cannot be negative`,
        code: 'BELOW_MINIMUM',
        value
      });
    }
  });

  // Validate utilization percentages
  if (metrics.stowageUtilization > 1.0) {
    warnings.push({
      field: 'stowageUtilization',
      message: 'Stowage utilization above 100% indicates overcrowding',
      code: 'ABOVE_RECOMMENDED',
      value: metrics.stowageUtilization
    });
  }

  // Validate safety margins
  if (metrics.thermalMargin < 0.1) {
    warnings.push({
      field: 'thermalMargin',
      message: 'Thermal margin below 10% may indicate insufficient cooling',
      code: 'BELOW_RECOMMENDED',
      value: metrics.thermalMargin
    });
  }

  if (metrics.lssMargin < 0.2) {
    warnings.push({
      field: 'lssMargin',
      message: 'LSS margin below 20% may indicate insufficient life support capacity',
      code: 'BELOW_RECOMMENDED',
      value: metrics.lssMargin
    });
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
}

// ============================================================================
// MISSION PARAMETERS VALIDATION
// ============================================================================

export function validateMissionParameters(mission: MissionParameters): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationWarning[] = [];

  // Validate crew size
  if (!Number.isInteger(mission.crew_size) || mission.crew_size < VALIDATION_CONSTANTS.MISSION.MIN_CREW_SIZE) {
    errors.push({
      field: 'crew_size',
      message: `Crew size must be at least ${VALIDATION_CONSTANTS.MISSION.MIN_CREW_SIZE}`,
      code: 'BELOW_MINIMUM',
      value: mission.crew_size
    });
  } else if (mission.crew_size > VALIDATION_CONSTANTS.MISSION.MAX_CREW_SIZE) {
    warnings.push({
      field: 'crew_size',
      message: `Crew size ${mission.crew_size} is very large`,
      code: 'ABOVE_RECOMMENDED',
      value: mission.crew_size
    });
  }

  // Validate duration
  if (!Number.isInteger(mission.duration_days) || mission.duration_days < VALIDATION_CONSTANTS.MISSION.MIN_DURATION) {
    errors.push({
      field: 'duration_days',
      message: `Mission duration must be at least ${VALIDATION_CONSTANTS.MISSION.MIN_DURATION} day`,
      code: 'BELOW_MINIMUM',
      value: mission.duration_days
    });
  } else if (mission.duration_days > VALIDATION_CONSTANTS.MISSION.MAX_DURATION) {
    warnings.push({
      field: 'duration_days',
      message: `Mission duration ${mission.duration_days} days is very long`,
      code: 'ABOVE_RECOMMENDED',
      value: mission.duration_days
    });
  }

  // Validate priority weights sum to 1.0
  const weightSum = Object.values(mission.priority_weights).reduce((sum, weight) => sum + weight, 0);
  if (Math.abs(weightSum - 1.0) > 0.001) {
    errors.push({
      field: 'priority_weights',
      message: `Priority weights must sum to 1.0, current sum: ${weightSum.toFixed(3)}`,
      code: 'INVALID_SUM',
      value: weightSum
    });
  }

  // Validate individual weights are non-negative
  Object.entries(mission.priority_weights).forEach(([key, weight]) => {
    if (weight < 0) {
      errors.push({
        field: `priority_weights.${key}`,
        message: 'Priority weights cannot be negative',
        code: 'BELOW_MINIMUM',
        value: weight
      });
    }
  });

  // Validate activity schedule
  const scheduleSum = Object.values(mission.activity_schedule).reduce((sum, time) => sum + time, 0);
  if (scheduleSum > 24) {
    warnings.push({
      field: 'activity_schedule',
      message: `Daily activity schedule exceeds 24 hours: ${scheduleSum.toFixed(1)}h`,
      code: 'ABOVE_MAXIMUM',
      value: scheduleSum
    });
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
}

// ============================================================================
// UTILITY VALIDATION FUNCTIONS
// ============================================================================

export function validateRequired<T>(value: T, fieldName: string): ValidationError | null {
  if (value === null || value === undefined || (typeof value === 'string' && value.trim().length === 0)) {
    return {
      field: fieldName,
      message: `${fieldName} is required`,
      code: 'REQUIRED_FIELD',
      value
    };
  }
  return null;
}

export function validateRange(
  value: number, 
  min: number, 
  max: number, 
  fieldName: string
): ValidationError | null {
  if (value < min) {
    return {
      field: fieldName,
      message: `${fieldName} must be at least ${min}`,
      code: 'BELOW_MINIMUM',
      value
    };
  }
  if (value > max) {
    return {
      field: fieldName,
      message: `${fieldName} must be at most ${max}`,
      code: 'ABOVE_MAXIMUM',
      value
    };
  }
  return null;
}

export function validateEnum<T extends Record<string, string>>(
  value: string, 
  enumObject: T, 
  fieldName: string
): ValidationError | null {
  if (!Object.values(enumObject).includes(value as T[keyof T])) {
    return {
      field: fieldName,
      message: `Invalid ${fieldName}: ${value}. Valid values: ${Object.values(enumObject).join(', ')}`,
      code: 'INVALID_ENUM_VALUE',
      value
    };
  }
  return null;
}