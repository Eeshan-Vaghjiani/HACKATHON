// Geometry utility functions for HabitatCanvas

import { Vector3D, BoundingBox, Transform3D, GeometryConstraints } from './index';

// ============================================================================
// COORDINATE TRANSFORMATION UTILITIES
// ============================================================================

/**
 * Convert degrees to radians
 */
export function degToRad(degrees: number): number {
  return degrees * (Math.PI / 180);
}

/**
 * Convert radians to degrees
 */
export function radToDeg(radians: number): number {
  return radians * (180 / Math.PI);
}

/**
 * Create a 3D vector
 */
export function createVector3D(x: number, y: number, z: number): Vector3D {
  return { x, y, z };
}

/**
 * Add two 3D vectors
 */
export function addVectors(a: Vector3D, b: Vector3D): Vector3D {
  return {
    x: a.x + b.x,
    y: a.y + b.y,
    z: a.z + b.z
  };
}

/**
 * Subtract two 3D vectors
 */
export function subtractVectors(a: Vector3D, b: Vector3D): Vector3D {
  return {
    x: a.x - b.x,
    y: a.y - b.y,
    z: a.z - b.z
  };
}

/**
 * Scale a 3D vector by a scalar
 */
export function scaleVector(vector: Vector3D, scalar: number): Vector3D {
  return {
    x: vector.x * scalar,
    y: vector.y * scalar,
    z: vector.z * scalar
  };
}

/**
 * Calculate the dot product of two 3D vectors
 */
export function dotProduct(a: Vector3D, b: Vector3D): number {
  return a.x * b.x + a.y * b.y + a.z * b.z;
}

/**
 * Calculate the cross product of two 3D vectors
 */
export function crossProduct(a: Vector3D, b: Vector3D): Vector3D {
  return {
    x: a.y * b.z - a.z * b.y,
    y: a.z * b.x - a.x * b.z,
    z: a.x * b.y - a.y * b.x
  };
}

/**
 * Calculate the magnitude (length) of a 3D vector
 */
export function vectorMagnitude(vector: Vector3D): number {
  return Math.sqrt(vector.x * vector.x + vector.y * vector.y + vector.z * vector.z);
}

/**
 * Normalize a 3D vector to unit length
 */
export function normalizeVector(vector: Vector3D): Vector3D {
  const magnitude = vectorMagnitude(vector);
  if (magnitude === 0) {
    return { x: 0, y: 0, z: 0 };
  }
  return scaleVector(vector, 1 / magnitude);
}

/**
 * Calculate the distance between two 3D points
 */
export function distance3D(a: Vector3D, b: Vector3D): number {
  return vectorMagnitude(subtractVectors(a, b));
}

/**
 * Calculate the distance between two 2D points (ignoring Z)
 */
export function distance2D(a: Vector3D, b: Vector3D): number {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.sqrt(dx * dx + dy * dy);
}

// ============================================================================
// ROTATION AND TRANSFORMATION UTILITIES
// ============================================================================

/**
 * Create a rotation matrix for rotation around Z-axis (yaw)
 */
export function createRotationMatrixZ(angleRad: number): number[][] {
  const cos = Math.cos(angleRad);
  const sin = Math.sin(angleRad);
  return [
    [cos, -sin, 0],
    [sin, cos, 0],
    [0, 0, 1]
  ];
}

/**
 * Apply a rotation matrix to a 3D vector
 */
export function applyRotationMatrix(vector: Vector3D, matrix: number[][]): Vector3D {
  return {
    x: matrix[0][0] * vector.x + matrix[0][1] * vector.y + matrix[0][2] * vector.z,
    y: matrix[1][0] * vector.x + matrix[1][1] * vector.y + matrix[1][2] * vector.z,
    z: matrix[2][0] * vector.x + matrix[2][1] * vector.y + matrix[2][2] * vector.z
  };
}

/**
 * Rotate a point around the Z-axis by the given angle in degrees
 */
export function rotatePointZ(point: Vector3D, angleDeg: number): Vector3D {
  const angleRad = degToRad(angleDeg);
  const rotMatrix = createRotationMatrixZ(angleRad);
  return applyRotationMatrix(point, rotMatrix);
}

/**
 * Transform a point using position, rotation, and scale
 */
export function transformPoint(point: Vector3D, transform: Transform3D): Vector3D {
  // Apply scale
  let transformed = {
    x: point.x * transform.scale.x,
    y: point.y * transform.scale.y,
    z: point.z * transform.scale.z
  };

  // Apply rotation (simplified - only Z rotation for now)
  transformed = rotatePointZ(transformed, transform.rotation.z);

  // Apply translation
  transformed = addVectors(transformed, transform.position);

  return transformed;
}

/**
 * Convert local coordinates to global coordinates
 */
export function localToGlobal(localPoint: Vector3D, transform: Transform3D): Vector3D {
  return transformPoint(localPoint, transform);
}

/**
 * Convert global coordinates to local coordinates
 */
export function globalToLocal(globalPoint: Vector3D, transform: Transform3D): Vector3D {
  // Inverse transformation: translate, then inverse rotate, then inverse scale
  let local = subtractVectors(globalPoint, transform.position);
  
  // Inverse rotation (negative angle)
  local = rotatePointZ(local, -transform.rotation.z);
  
  // Inverse scale
  local = {
    x: local.x / transform.scale.x,
    y: local.y / transform.scale.y,
    z: local.z / transform.scale.z
  };

  return local;
}

// ============================================================================
// BOUNDING BOX UTILITIES
// ============================================================================

/**
 * Create a bounding box from min and max points
 */
export function createBoundingBox(min: Vector3D, max: Vector3D): BoundingBox {
  return { min, max };
}

/**
 * Create a bounding box from center point and dimensions
 */
export function createBoundingBoxFromCenter(center: Vector3D, dimensions: Vector3D): BoundingBox {
  const halfDims = scaleVector(dimensions, 0.5);
  return {
    min: subtractVectors(center, halfDims),
    max: addVectors(center, halfDims)
  };
}

/**
 * Check if two bounding boxes intersect
 */
export function boundingBoxesIntersect(a: BoundingBox, b: BoundingBox): boolean {
  return (
    a.min.x <= b.max.x && a.max.x >= b.min.x &&
    a.min.y <= b.max.y && a.max.y >= b.min.y &&
    a.min.z <= b.max.z && a.max.z >= b.min.z
  );
}

/**
 * Check if a point is inside a bounding box
 */
export function pointInBoundingBox(point: Vector3D, bbox: BoundingBox): boolean {
  return (
    point.x >= bbox.min.x && point.x <= bbox.max.x &&
    point.y >= bbox.min.y && point.y <= bbox.max.y &&
    point.z >= bbox.min.z && point.z <= bbox.max.z
  );
}

/**
 * Calculate the volume of a bounding box
 */
export function boundingBoxVolume(bbox: BoundingBox): number {
  const dimensions = subtractVectors(bbox.max, bbox.min);
  return dimensions.x * dimensions.y * dimensions.z;
}

/**
 * Calculate the center point of a bounding box
 */
export function boundingBoxCenter(bbox: BoundingBox): Vector3D {
  return {
    x: (bbox.min.x + bbox.max.x) / 2,
    y: (bbox.min.y + bbox.max.y) / 2,
    z: (bbox.min.z + bbox.max.z) / 2
  };
}

/**
 * Expand a bounding box by a given margin
 */
export function expandBoundingBox(bbox: BoundingBox, margin: number): BoundingBox {
  const marginVector = createVector3D(margin, margin, margin);
  return {
    min: subtractVectors(bbox.min, marginVector),
    max: addVectors(bbox.max, marginVector)
  };
}

// ============================================================================
// ENVELOPE GEOMETRY CALCULATIONS
// ============================================================================

/**
 * Calculate the volume of a cylindrical envelope
 */
export function calculateCylinderVolume(radius: number, length: number): number {
  return Math.PI * radius * radius * length;
}

/**
 * Calculate the volume of a box envelope
 */
export function calculateBoxVolume(width: number, height: number, depth: number): number {
  return width * height * depth;
}

/**
 * Calculate the volume of a torus envelope
 */
export function calculateTorusVolume(majorRadius: number, minorRadius: number): number {
  return 2 * Math.PI * Math.PI * majorRadius * minorRadius * minorRadius;
}

/**
 * Check if a point is inside a cylindrical envelope
 */
export function pointInCylinder(point: Vector3D, radius: number, length: number): boolean {
  // Assume cylinder is aligned with Z-axis and centered at origin
  const distanceFromAxis = Math.sqrt(point.x * point.x + point.y * point.y);
  return distanceFromAxis <= radius && Math.abs(point.z) <= length / 2;
}

/**
 * Check if a point is inside a box envelope
 */
export function pointInBox(point: Vector3D, width: number, height: number, depth: number): boolean {
  // Assume box is centered at origin
  return (
    Math.abs(point.x) <= width / 2 &&
    Math.abs(point.y) <= height / 2 &&
    Math.abs(point.z) <= depth / 2
  );
}

/**
 * Check if a point is inside a torus envelope
 */
export function pointInTorus(point: Vector3D, majorRadius: number, minorRadius: number): boolean {
  // Assume torus is in XY plane, centered at origin
  const distanceFromCenter = Math.sqrt(point.x * point.x + point.y * point.y);
  const distanceFromTube = Math.sqrt(
    Math.pow(distanceFromCenter - majorRadius, 2) + point.z * point.z
  );
  return distanceFromTube <= minorRadius;
}

// ============================================================================
// COLLISION DETECTION UTILITIES
// ============================================================================

/**
 * Check if two spheres collide
 */
export function spheresCollide(
  center1: Vector3D, 
  radius1: number, 
  center2: Vector3D, 
  radius2: number
): boolean {
  const distance = distance3D(center1, center2);
  return distance <= (radius1 + radius2);
}

/**
 * Check if two axis-aligned bounding boxes collide
 */
export function aabbCollision(bbox1: BoundingBox, bbox2: BoundingBox): boolean {
  return boundingBoxesIntersect(bbox1, bbox2);
}

/**
 * Calculate the minimum distance between two bounding boxes
 */
export function minimumDistanceBetweenBoundingBoxes(bbox1: BoundingBox, bbox2: BoundingBox): number {
  const center1 = boundingBoxCenter(bbox1);
  const center2 = boundingBoxCenter(bbox2);
  
  // Calculate the distance between centers
  const centerDistance = distance3D(center1, center2);
  
  // Calculate the maximum extent of each bounding box
  const extent1 = distance3D(bbox1.min, bbox1.max) / 2;
  const extent2 = distance3D(bbox2.min, bbox2.max) / 2;
  
  // Minimum distance is center distance minus extents
  return Math.max(0, centerDistance - extent1 - extent2);
}

// ============================================================================
// CLEARANCE AND ACCESSIBILITY UTILITIES
// ============================================================================

/**
 * Check if there's sufficient clearance between two modules
 */
export function checkClearance(
  bbox1: BoundingBox, 
  bbox2: BoundingBox, 
  minClearance: number
): boolean {
  const distance = minimumDistanceBetweenBoundingBoxes(bbox1, bbox2);
  return distance >= minClearance;
}

/**
 * Calculate walkway width between two modules
 */
export function calculateWalkwayWidth(
  bbox1: BoundingBox, 
  bbox2: BoundingBox
): number {
  return minimumDistanceBetweenBoundingBoxes(bbox1, bbox2);
}

/**
 * Check if a path between two points has sufficient clearance
 */
export function checkPathClearance(
  start: Vector3D, 
  end: Vector3D, 
  obstacles: BoundingBox[], 
  minClearance: number
): boolean {
  // Simplified check - create a bounding box around the path and check for intersections
  const pathBBox = createBoundingBox(
    {
      x: Math.min(start.x, end.x) - minClearance,
      y: Math.min(start.y, end.y) - minClearance,
      z: Math.min(start.z, end.z) - minClearance
    },
    {
      x: Math.max(start.x, end.x) + minClearance,
      y: Math.max(start.y, end.y) + minClearance,
      z: Math.max(start.z, end.z) + minClearance
    }
  );

  // Check if any obstacle intersects with the path
  return !obstacles.some(obstacle => boundingBoxesIntersect(pathBBox, obstacle));
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Clamp a value between min and max
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Linear interpolation between two values
 */
export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * clamp(t, 0, 1);
}

/**
 * Linear interpolation between two 3D vectors
 */
export function lerpVector3D(a: Vector3D, b: Vector3D, t: number): Vector3D {
  return {
    x: lerp(a.x, b.x, t),
    y: lerp(a.y, b.y, t),
    z: lerp(a.z, b.z, t)
  };
}

/**
 * Check if two numbers are approximately equal within a tolerance
 */
export function approximately(a: number, b: number, tolerance: number = 1e-6): boolean {
  return Math.abs(a - b) <= tolerance;
}

/**
 * Check if two 3D vectors are approximately equal within a tolerance
 */
export function approximatelyEqualVectors(a: Vector3D, b: Vector3D, tolerance: number = 1e-6): boolean {
  return (
    approximately(a.x, b.x, tolerance) &&
    approximately(a.y, b.y, tolerance) &&
    approximately(a.z, b.z, tolerance)
  );
}

/**
 * Round a number to a specified number of decimal places
 */
export function roundToDecimals(value: number, decimals: number): number {
  const factor = Math.pow(10, decimals);
  return Math.round(value * factor) / factor;
}

/**
 * Round a 3D vector to a specified number of decimal places
 */
export function roundVector3D(vector: Vector3D, decimals: number): Vector3D {
  return {
    x: roundToDecimals(vector.x, decimals),
    y: roundToDecimals(vector.y, decimals),
    z: roundToDecimals(vector.z, decimals)
  };
}

// ============================================================================
// ADVANCED GEOMETRY CALCULATIONS
// ============================================================================

/**
 * Calculate the volume of an envelope based on its type and parameters
 */
export function calculateEnvelopeVolume(envelope: { type: string; params: Record<string, number> }): number {
  switch (envelope.type) {
    case 'cylinder':
      return calculateCylinderVolume(envelope.params.radius, envelope.params.length);
    case 'box':
      return calculateBoxVolume(envelope.params.width, envelope.params.height, envelope.params.depth);
    case 'torus':
      return calculateTorusVolume(envelope.params.major_radius, envelope.params.minor_radius);
    case 'freeform':
      return envelope.params.volume || 0;
    default:
      return 0;
  }
}

/**
 * Calculate the surface area of an envelope
 */
export function calculateEnvelopeSurfaceArea(envelope: { type: string; params: Record<string, number> }): number {
  switch (envelope.type) {
    case 'cylinder':
      const r = envelope.params.radius;
      const l = envelope.params.length;
      return 2 * Math.PI * r * (r + l); // 2πr² + 2πrl
    case 'box':
      const w = envelope.params.width;
      const h = envelope.params.height;
      const d = envelope.params.depth;
      return 2 * (w * h + w * d + h * d);
    case 'torus':
      const R = envelope.params.major_radius;
      const r2 = envelope.params.minor_radius;
      return 4 * Math.PI * Math.PI * R * r2;
    default:
      return 0;
  }
}

/**
 * Calculate the centroid of a set of points
 */
export function calculateCentroid(points: Vector3D[]): Vector3D {
  if (points.length === 0) {
    return createVector3D(0, 0, 0);
  }

  const sum = points.reduce(
    (acc, point) => addVectors(acc, point),
    createVector3D(0, 0, 0)
  );

  return scaleVector(sum, 1 / points.length);
}

/**
 * Calculate the bounding box of a set of points
 */
export function calculateBoundingBoxFromPoints(points: Vector3D[]): BoundingBox {
  if (points.length === 0) {
    return createBoundingBox(createVector3D(0, 0, 0), createVector3D(0, 0, 0));
  }

  let minX = points[0].x, maxX = points[0].x;
  let minY = points[0].y, maxY = points[0].y;
  let minZ = points[0].z, maxZ = points[0].z;

  for (const point of points) {
    minX = Math.min(minX, point.x);
    maxX = Math.max(maxX, point.x);
    minY = Math.min(minY, point.y);
    maxY = Math.max(maxY, point.y);
    minZ = Math.min(minZ, point.z);
    maxZ = Math.max(maxZ, point.z);
  }

  return createBoundingBox(
    createVector3D(minX, minY, minZ),
    createVector3D(maxX, maxY, maxZ)
  );
}

/**
 * Calculate the shortest path distance between two points avoiding obstacles
 */
export function calculateShortestPath(
  start: Vector3D,
  end: Vector3D,
  obstacles: BoundingBox[]
): number {
  // Simplified A* pathfinding - for a more complete implementation,
  // this would use a proper pathfinding algorithm
  
  // If direct path is clear, return straight-line distance
  if (checkPathClearance(start, end, obstacles, 0.6)) {
    return distance3D(start, end);
  }

  // Otherwise, estimate path around obstacles (simplified)
  const directDistance = distance3D(start, end);
  const obstacleCount = obstacles.length;
  
  // Rough estimation: add 50% for each obstacle that might be in the way
  return directDistance * (1 + obstacleCount * 0.5);
}

/**
 * Check if a point is inside any of the given bounding boxes
 */
export function pointInAnyBoundingBox(point: Vector3D, boxes: BoundingBox[]): boolean {
  return boxes.some(box => pointInBoundingBox(point, box));
}

/**
 * Find the closest point on a bounding box to a given point
 */
export function closestPointOnBoundingBox(point: Vector3D, bbox: BoundingBox): Vector3D {
  return createVector3D(
    clamp(point.x, bbox.min.x, bbox.max.x),
    clamp(point.y, bbox.min.y, bbox.max.y),
    clamp(point.z, bbox.min.z, bbox.max.z)
  );
}

/**
 * Calculate the overlap volume between two bounding boxes
 */
export function calculateBoundingBoxOverlap(bbox1: BoundingBox, bbox2: BoundingBox): number {
  if (!boundingBoxesIntersect(bbox1, bbox2)) {
    return 0;
  }

  const overlapMin = createVector3D(
    Math.max(bbox1.min.x, bbox2.min.x),
    Math.max(bbox1.min.y, bbox2.min.y),
    Math.max(bbox1.min.z, bbox2.min.z)
  );

  const overlapMax = createVector3D(
    Math.min(bbox1.max.x, bbox2.max.x),
    Math.min(bbox1.max.y, bbox2.max.y),
    Math.min(bbox1.max.z, bbox2.max.z)
  );

  const dimensions = subtractVectors(overlapMax, overlapMin);
  return dimensions.x * dimensions.y * dimensions.z;
}

/**
 * Generate a grid of points within a bounding box
 */
export function generateGridPoints(bbox: BoundingBox, spacing: number): Vector3D[] {
  const points: Vector3D[] = [];
  const dimensions = subtractVectors(bbox.max, bbox.min);
  
  const stepsX = Math.ceil(dimensions.x / spacing);
  const stepsY = Math.ceil(dimensions.y / spacing);
  const stepsZ = Math.ceil(dimensions.z / spacing);

  for (let i = 0; i <= stepsX; i++) {
    for (let j = 0; j <= stepsY; j++) {
      for (let k = 0; k <= stepsZ; k++) {
        const x = bbox.min.x + (i / stepsX) * dimensions.x;
        const y = bbox.min.y + (j / stepsY) * dimensions.y;
        const z = bbox.min.z + (k / stepsZ) * dimensions.z;
        points.push(createVector3D(x, y, z));
      }
    }
  }

  return points;
}

/**
 * Calculate the angle between two vectors in radians
 */
export function angleBetweenVectors(v1: Vector3D, v2: Vector3D): number {
  const dot = dotProduct(normalizeVector(v1), normalizeVector(v2));
  return Math.acos(clamp(dot, -1, 1));
}

/**
 * Project a vector onto another vector
 */
export function projectVector(vector: Vector3D, onto: Vector3D): Vector3D {
  const ontoNormalized = normalizeVector(onto);
  const projectionLength = dotProduct(vector, ontoNormalized);
  return scaleVector(ontoNormalized, projectionLength);
}

/**
 * Calculate the area of a triangle given three points
 */
export function triangleArea(p1: Vector3D, p2: Vector3D, p3: Vector3D): number {
  const v1 = subtractVectors(p2, p1);
  const v2 = subtractVectors(p3, p1);
  const cross = crossProduct(v1, v2);
  return vectorMagnitude(cross) / 2;
}