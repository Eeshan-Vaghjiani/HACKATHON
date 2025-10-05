/**
 * Envelope validation utilities
 * 
 * Validates that modules fit within the habitat envelope boundaries
 */

import { EnvelopeSpec, EnvelopeType, ModulePlacement } from '../types';

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * Check if a point is within a cylindrical envelope
 */
function isPointInCylinder(
  point: [number, number, number],
  radius: number,
  height: number
): boolean {
  const [x, y, z] = point;
  const distanceFromCenter = Math.sqrt(x * x + z * z);
  return distanceFromCenter <= radius && Math.abs(y) <= height / 2;
}

/**
 * Check if a point is within a box envelope
 */
function isPointInBox(
  point: [number, number, number],
  width: number,
  depth: number,
  height: number
): boolean {
  const [x, y, z] = point;
  return (
    Math.abs(x) <= width / 2 &&
    Math.abs(y) <= height / 2 &&
    Math.abs(z) <= depth / 2
  );
}

/**
 * Check if a point is within a torus envelope
 */
function isPointInTorus(
  point: [number, number, number],
  majorRadius: number,
  minorRadius: number
): boolean {
  const [x, y, z] = point;
  const distanceFromCenter = Math.sqrt(x * x + z * z);
  const distanceFromTorus = Math.sqrt(
    Math.pow(distanceFromCenter - majorRadius, 2) + y * y
  );
  return distanceFromTorus <= minorRadius;
}

/**
 * Validate that a module fits within the envelope
 */
export function validateModuleInEnvelope(
  module: ModulePlacement,
  envelope: EnvelopeSpec,
  moduleSize: { x: number; y: number; z: number } = { x: 2, y: 2, z: 2 }
): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  
  const params = envelope.params;
  const position = module.position;
  
  // Check all corners of the module bounding box
  const halfSize = {
    x: moduleSize.x / 2,
    y: moduleSize.y / 2,
    z: moduleSize.z / 2
  };
  
  const corners: [number, number, number][] = [
    [position[0] - halfSize.x, position[1] - halfSize.y, position[2] - halfSize.z],
    [position[0] + halfSize.x, position[1] - halfSize.y, position[2] - halfSize.z],
    [position[0] - halfSize.x, position[1] + halfSize.y, position[2] - halfSize.z],
    [position[0] + halfSize.x, position[1] + halfSize.y, position[2] - halfSize.z],
    [position[0] - halfSize.x, position[1] - halfSize.y, position[2] + halfSize.z],
    [position[0] + halfSize.x, position[1] - halfSize.y, position[2] + halfSize.z],
    [position[0] - halfSize.x, position[1] + halfSize.y, position[2] + halfSize.z],
    [position[0] + halfSize.x, position[1] + halfSize.y, position[2] + halfSize.z],
  ];
  
  let allCornersInside = true;
  
  switch (envelope.type) {
    case EnvelopeType.CYLINDER:
      const radius = params.radius || 5;
      const height = params.height || 10;
      
      for (const corner of corners) {
        if (!isPointInCylinder(corner, radius, height)) {
          allCornersInside = false;
          break;
        }
      }
      
      if (!allCornersInside) {
        errors.push(`Module ${module.module_id} extends outside cylindrical envelope (radius: ${radius}m, height: ${height}m)`);
      }
      break;
      
    case EnvelopeType.BOX:
      const width = params.width || 10;
      const depth = params.depth || 10;
      const boxHeight = params.height || 10;
      
      for (const corner of corners) {
        if (!isPointInBox(corner, width, depth, boxHeight)) {
          allCornersInside = false;
          break;
        }
      }
      
      if (!allCornersInside) {
        errors.push(`Module ${module.module_id} extends outside box envelope (${width}m × ${depth}m × ${boxHeight}m)`);
      }
      break;
      
    case EnvelopeType.TORUS:
      const majorRadius = params.majorRadius || 10;
      const minorRadius = params.minorRadius || 2;
      
      for (const corner of corners) {
        if (!isPointInTorus(corner, majorRadius, minorRadius)) {
          allCornersInside = false;
          break;
        }
      }
      
      if (!allCornersInside) {
        errors.push(`Module ${module.module_id} extends outside torus envelope (major: ${majorRadius}m, minor: ${minorRadius}m)`);
      }
      break;
      
    default:
      warnings.push(`Unknown envelope type: ${envelope.type}`);
  }
  
  // Check if module is close to boundaries (warning)
  const centerDistance = Math.sqrt(
    position[0] * position[0] + position[2] * position[2]
  );
  
  if (envelope.type === EnvelopeType.CYLINDER) {
    const radius = params.radius || 5;
    if (centerDistance > radius * 0.8) {
      warnings.push(`Module ${module.module_id} is very close to envelope boundary`);
    }
  }
  
  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
}

/**
 * Validate all modules in a layout
 */
export function validateLayoutInEnvelope(
  modules: ModulePlacement[],
  envelope: EnvelopeSpec
): ValidationResult {
  const allErrors: string[] = [];
  const allWarnings: string[] = [];
  
  for (const module of modules) {
    const result = validateModuleInEnvelope(module, envelope);
    allErrors.push(...result.errors);
    allWarnings.push(...result.warnings);
  }
  
  return {
    isValid: allErrors.length === 0,
    errors: allErrors,
    warnings: allWarnings
  };
}

/**
 * Get safe placement bounds for a given envelope
 */
export function getSafePlacementBounds(envelope: EnvelopeSpec): {
  maxRadius: number;
  maxHeight: number;
  description: string;
} {
  const params = envelope.params;
  
  switch (envelope.type) {
    case EnvelopeType.CYLINDER:
      const radius = params.radius || 5;
      const height = params.height || 10;
      return {
        maxRadius: radius * 0.7,  // 70% of radius for safety
        maxHeight: height * 0.7,  // 70% of height for safety
        description: `Safe zone: ${(radius * 0.7).toFixed(1)}m radius, ${(height * 0.7).toFixed(1)}m height`
      };
      
    case EnvelopeType.BOX:
      const width = params.width || 10;
      const depth = params.depth || 10;
      const boxHeight = params.height || 10;
      const minDim = Math.min(width, depth);
      return {
        maxRadius: minDim * 0.35,
        maxHeight: boxHeight * 0.7,
        description: `Safe zone: ${(minDim * 0.7).toFixed(1)}m × ${(boxHeight * 0.7).toFixed(1)}m`
      };
      
    case EnvelopeType.TORUS:
      const majorRadius = params.majorRadius || 10;
      const minorRadius = params.minorRadius || 2;
      return {
        maxRadius: minorRadius * 0.6,
        maxHeight: minorRadius * 0.8,
        description: `Safe zone: ${(minorRadius * 0.6).toFixed(1)}m from torus center`
      };
      
    default:
      return {
        maxRadius: 3,
        maxHeight: 5,
        description: 'Default safe zone: 3m radius, 5m height'
      };
  }
}
