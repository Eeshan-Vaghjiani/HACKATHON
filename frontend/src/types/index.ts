// Core data types for HabitatCanvas frontend

// ============================================================================
// ENUMS
// ============================================================================

export enum ModuleType {
  SLEEP_QUARTER = "sleep_quarter",
  GALLEY = "galley",
  LABORATORY = "laboratory",
  AIRLOCK = "airlock",
  MECHANICAL = "mechanical",
  MEDICAL = "medical",
  EXERCISE = "exercise",
  STORAGE = "storage"
}

export enum EnvelopeType {
  CYLINDER = "cylinder",
  TORUS = "torus",
  BOX = "box",
  FREEFORM = "freeform"
}

export enum CoordinateFrame {
  LOCAL = "local",
  GLOBAL = "global"
}

// ============================================================================
// CORE INTERFACES
// ============================================================================

export interface Vector3D {
  x: number;
  y: number;
  z: number;
}

export interface BoundingBox {
  min: Vector3D;
  max: Vector3D;
}

export interface EnvelopeSpec {
  id: string;
  type: EnvelopeType;
  params: Record<string, number>;
  coordinateFrame: CoordinateFrame;
  metadata: {
    name: string;
    creator: string;
    created: Date;
    version?: string;
    description?: string;
  };
  constraints?: {
    minVolume?: number;
    maxVolume?: number;
    minDimension?: number;
    maxDimension?: number;
  };
}

export interface ModuleSpec {
  module_id: string;
  type: ModuleType;
  name: string;
  bbox_m: {
    x: number;
    y: number;
    z: number;
  };
  mass_kg: number;
  power_w: number;
  stowage_m3: number;
  connectivity_ports: string[];
  adjacency_preferences: ModuleType[];
  adjacency_restrictions: ModuleType[];
  metadata?: {
    description?: string;
    manufacturer?: string;
    model?: string;
    certification?: string;
  };
}

export interface ModulePlacement {
  module_id: string;
  type: ModuleType;
  position: [number, number, number];
  rotation_deg: number;
  connections: string[];
  isValid?: boolean;
  validationErrors?: string[];
}

export interface LayoutSpec {
  layoutId: string;
  envelopeId: string;
  modules: ModulePlacement[];
  kpis: PerformanceMetrics;
  explainability: string;
  metadata?: {
    name?: string;
    created: Date;
    generationParams?: Record<string, any>;
    version?: string;
  };
  constraints?: {
    totalMass?: number;
    totalPower?: number;
    minClearance?: number;
  };
}

export interface PerformanceMetrics {
  meanTransitTime: number;
  egressTime: number;
  massTotal: number;
  powerBudget: number;
  thermalMargin: number;
  lssMargin: number;
  stowageUtilization: number;
  // Additional metrics
  connectivityScore?: number;
  safetyScore?: number;
  efficiencyScore?: number;
  volumeUtilization?: number;
}

export interface MissionParameters {
  crew_size: number;
  duration_days: number;
  priority_weights: Record<string, number>;
  activity_schedule: Record<string, number>;
  emergency_scenarios: string[];
  constraints?: {
    maxCrewSize?: number;
    maxDuration?: number;
    minSafetyMargin?: number;
  };
}

// ============================================================================
// VALIDATION RESULT TYPES
// ============================================================================

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface ValidationError {
  field: string;
  message: string;
  code: string;
  value?: any;
}

export interface ValidationWarning {
  field: string;
  message: string;
  code: string;
  value?: any;
}

// ============================================================================
// GEOMETRY UTILITY TYPES
// ============================================================================

export interface Transform3D {
  position: Vector3D;
  rotation: Vector3D; // Euler angles in degrees
  scale: Vector3D;
}

export interface GeometryConstraints {
  minClearance: number;
  walkwayWidth: number;
  emergencyEgressWidth: number;
  maxReach: number;
}

// Re-export validation and geometry utilities
export * from './validation';
export * from './geometry';