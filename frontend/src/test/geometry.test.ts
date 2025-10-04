// Unit tests for geometry utility functions

import { describe, it, expect } from 'vitest';
import {
  degToRad,
  radToDeg,
  createVector3D,
  addVectors,
  subtractVectors,
  scaleVector,
  dotProduct,
  crossProduct,
  vectorMagnitude,
  normalizeVector,
  distance3D,
  distance2D,
  rotatePointZ,
  transformPoint,
  localToGlobal,
  globalToLocal,
  createBoundingBox,
  createBoundingBoxFromCenter,
  boundingBoxesIntersect,
  pointInBoundingBox,
  boundingBoxVolume,
  boundingBoxCenter,
  expandBoundingBox,
  calculateCylinderVolume,
  calculateBoxVolume,
  calculateTorusVolume,
  pointInCylinder,
  pointInBox,
  pointInTorus,
  spheresCollide,
  aabbCollision,
  minimumDistanceBetweenBoundingBoxes,
  checkClearance,
  calculateWalkwayWidth,
  clamp,
  lerp,
  lerpVector3D,
  approximately,
  approximatelyEqualVectors,
  roundToDecimals,
  roundVector3D
} from '../types/geometry';
import { Vector3D, BoundingBox, Transform3D } from '../types/index';

// ============================================================================
// ANGLE CONVERSION TESTS
// ============================================================================

describe('Angle Conversion', () => {
  it('should convert degrees to radians correctly', () => {
    expect(approximately(degToRad(0), 0)).toBe(true);
    expect(approximately(degToRad(90), Math.PI / 2)).toBe(true);
    expect(approximately(degToRad(180), Math.PI)).toBe(true);
    expect(approximately(degToRad(360), 2 * Math.PI)).toBe(true);
  });

  it('should convert radians to degrees correctly', () => {
    expect(approximately(radToDeg(0), 0)).toBe(true);
    expect(approximately(radToDeg(Math.PI / 2), 90)).toBe(true);
    expect(approximately(radToDeg(Math.PI), 180)).toBe(true);
    expect(approximately(radToDeg(2 * Math.PI), 360)).toBe(true);
  });

  it('should be inverse operations', () => {
    const degrees = 45;
    expect(approximately(radToDeg(degToRad(degrees)), degrees)).toBe(true);
    
    const radians = Math.PI / 3;
    expect(approximately(degToRad(radToDeg(radians)), radians)).toBe(true);
  });
});

// ============================================================================
// VECTOR OPERATIONS TESTS
// ============================================================================

describe('Vector Operations', () => {
  const v1 = createVector3D(1, 2, 3);
  const v2 = createVector3D(4, 5, 6);

  it('should create vectors correctly', () => {
    expect(v1).toEqual({ x: 1, y: 2, z: 3 });
  });

  it('should add vectors correctly', () => {
    const result = addVectors(v1, v2);
    expect(result).toEqual({ x: 5, y: 7, z: 9 });
  });

  it('should subtract vectors correctly', () => {
    const result = subtractVectors(v2, v1);
    expect(result).toEqual({ x: 3, y: 3, z: 3 });
  });

  it('should scale vectors correctly', () => {
    const result = scaleVector(v1, 2);
    expect(result).toEqual({ x: 2, y: 4, z: 6 });
  });

  it('should calculate dot product correctly', () => {
    const result = dotProduct(v1, v2);
    expect(result).toBe(32); // 1*4 + 2*5 + 3*6 = 4 + 10 + 18 = 32
  });

  it('should calculate cross product correctly', () => {
    const result = crossProduct(v1, v2);
    expect(result).toEqual({ x: -3, y: 6, z: -3 });
  });

  it('should calculate vector magnitude correctly', () => {
    const magnitude = vectorMagnitude(createVector3D(3, 4, 0));
    expect(approximately(magnitude, 5)).toBe(true);
  });

  it('should normalize vectors correctly', () => {
    const vector = createVector3D(3, 4, 0);
    const normalized = normalizeVector(vector);
    expect(approximately(vectorMagnitude(normalized), 1)).toBe(true);
    expect(approximately(normalized.x, 0.6)).toBe(true);
    expect(approximately(normalized.y, 0.8)).toBe(true);
  });

  it('should handle zero vector normalization', () => {
    const zero = createVector3D(0, 0, 0);
    const normalized = normalizeVector(zero);
    expect(normalized).toEqual({ x: 0, y: 0, z: 0 });
  });

  it('should calculate 3D distance correctly', () => {
    const p1 = createVector3D(0, 0, 0);
    const p2 = createVector3D(3, 4, 0);
    expect(approximately(distance3D(p1, p2), 5)).toBe(true);
  });

  it('should calculate 2D distance correctly', () => {
    const p1 = createVector3D(0, 0, 10);
    const p2 = createVector3D(3, 4, 20);
    expect(approximately(distance2D(p1, p2), 5)).toBe(true);
  });
});

// ============================================================================
// TRANSFORMATION TESTS
// ============================================================================

describe('Transformations', () => {
  it('should rotate points around Z-axis correctly', () => {
    const point = createVector3D(1, 0, 0);
    const rotated = rotatePointZ(point, 90);
    expect(approximately(rotated.x, 0, 1e-10)).toBe(true);
    expect(approximately(rotated.y, 1)).toBe(true);
    expect(approximately(rotated.z, 0)).toBe(true);
  });

  it('should apply full transformation correctly', () => {
    const point = createVector3D(1, 0, 0);
    const transform: Transform3D = {
      position: createVector3D(2, 3, 4),
      rotation: createVector3D(0, 0, 90),
      scale: createVector3D(2, 2, 2)
    };
    
    const transformed = transformPoint(point, transform);
    expect(approximately(transformed.x, 2, 1e-10)).toBe(true);
    expect(approximately(transformed.y, 5)).toBe(true);
    expect(approximately(transformed.z, 4)).toBe(true);
  });

  it('should convert between local and global coordinates', () => {
    const localPoint = createVector3D(1, 0, 0);
    const transform: Transform3D = {
      position: createVector3D(5, 5, 5),
      rotation: createVector3D(0, 0, 90),
      scale: createVector3D(1, 1, 1)
    };
    
    const globalPoint = localToGlobal(localPoint, transform);
    const backToLocal = globalToLocal(globalPoint, transform);
    
    expect(approximatelyEqualVectors(localPoint, backToLocal, 1e-10)).toBe(true);
  });
});

// ============================================================================
// BOUNDING BOX TESTS
// ============================================================================

describe('Bounding Boxes', () => {
  const bbox1 = createBoundingBox(
    createVector3D(0, 0, 0),
    createVector3D(2, 2, 2)
  );
  
  const bbox2 = createBoundingBox(
    createVector3D(1, 1, 1),
    createVector3D(3, 3, 3)
  );

  it('should create bounding boxes correctly', () => {
    expect(bbox1.min).toEqual({ x: 0, y: 0, z: 0 });
    expect(bbox1.max).toEqual({ x: 2, y: 2, z: 2 });
  });

  it('should create bounding boxes from center and dimensions', () => {
    const center = createVector3D(1, 1, 1);
    const dimensions = createVector3D(2, 2, 2);
    const bbox = createBoundingBoxFromCenter(center, dimensions);
    
    expect(bbox.min).toEqual({ x: 0, y: 0, z: 0 });
    expect(bbox.max).toEqual({ x: 2, y: 2, z: 2 });
  });

  it('should detect bounding box intersections correctly', () => {
    expect(boundingBoxesIntersect(bbox1, bbox2)).toBe(true);
    
    const bbox3 = createBoundingBox(
      createVector3D(3, 3, 3),
      createVector3D(4, 4, 4)
    );
    expect(boundingBoxesIntersect(bbox1, bbox3)).toBe(false);
  });

  it('should detect points inside bounding boxes', () => {
    const insidePoint = createVector3D(1, 1, 1);
    const outsidePoint = createVector3D(3, 3, 3);
    
    expect(pointInBoundingBox(insidePoint, bbox1)).toBe(true);
    expect(pointInBoundingBox(outsidePoint, bbox1)).toBe(false);
  });

  it('should calculate bounding box volume correctly', () => {
    const volume = boundingBoxVolume(bbox1);
    expect(volume).toBe(8); // 2 * 2 * 2
  });

  it('should calculate bounding box center correctly', () => {
    const center = boundingBoxCenter(bbox1);
    expect(center).toEqual({ x: 1, y: 1, z: 1 });
  });

  it('should expand bounding boxes correctly', () => {
    const expanded = expandBoundingBox(bbox1, 1);
    expect(expanded.min).toEqual({ x: -1, y: -1, z: -1 });
    expect(expanded.max).toEqual({ x: 3, y: 3, z: 3 });
  });
});

// ============================================================================
// ENVELOPE GEOMETRY TESTS
// ============================================================================

describe('Envelope Geometry', () => {
  it('should calculate cylinder volume correctly', () => {
    const volume = calculateCylinderVolume(2, 10);
    const expected = Math.PI * 4 * 10; // π * r² * h
    expect(approximately(volume, expected)).toBe(true);
  });

  it('should calculate box volume correctly', () => {
    const volume = calculateBoxVolume(2, 3, 4);
    expect(volume).toBe(24);
  });

  it('should calculate torus volume correctly', () => {
    const volume = calculateTorusVolume(5, 2);
    const expected = 2 * Math.PI * Math.PI * 5 * 4; // 2π²Rr²
    expect(approximately(volume, expected)).toBe(true);
  });

  it('should detect points inside cylinder correctly', () => {
    expect(pointInCylinder(createVector3D(1, 1, 2), 2, 10)).toBe(true);
    expect(pointInCylinder(createVector3D(3, 0, 2), 2, 10)).toBe(false);
    expect(pointInCylinder(createVector3D(0, 0, 6), 2, 10)).toBe(false);
  });

  it('should detect points inside box correctly', () => {
    expect(pointInBox(createVector3D(1, 1, 1), 4, 4, 4)).toBe(true);
    expect(pointInBox(createVector3D(3, 1, 1), 4, 4, 4)).toBe(false);
  });

  it('should detect points inside torus correctly', () => {
    expect(pointInTorus(createVector3D(3, 0, 0), 5, 2)).toBe(true);
    expect(pointInTorus(createVector3D(0, 0, 0), 5, 2)).toBe(false);
    expect(pointInTorus(createVector3D(8, 0, 0), 5, 2)).toBe(false);
  });
});

// ============================================================================
// COLLISION DETECTION TESTS
// ============================================================================

describe('Collision Detection', () => {
  it('should detect sphere collisions correctly', () => {
    const center1 = createVector3D(0, 0, 0);
    const center2 = createVector3D(3, 0, 0);
    
    expect(spheresCollide(center1, 2, center2, 2)).toBe(true);
    expect(spheresCollide(center1, 1, center2, 1)).toBe(false);
  });

  it('should detect AABB collisions correctly', () => {
    const bbox1 = createBoundingBox(
      createVector3D(0, 0, 0),
      createVector3D(2, 2, 2)
    );
    const bbox2 = createBoundingBox(
      createVector3D(1, 1, 1),
      createVector3D(3, 3, 3)
    );
    
    expect(aabbCollision(bbox1, bbox2)).toBe(true);
  });

  it('should calculate minimum distance between bounding boxes', () => {
    const bbox1 = createBoundingBox(
      createVector3D(0, 0, 0),
      createVector3D(1, 1, 1)
    );
    const bbox2 = createBoundingBox(
      createVector3D(3, 0, 0),
      createVector3D(4, 1, 1)
    );
    
    const distance = minimumDistanceBetweenBoundingBoxes(bbox1, bbox2);
    expect(distance).toBeGreaterThan(0);
  });

  it('should check clearance between modules', () => {
    const bbox1 = createBoundingBox(
      createVector3D(0, 0, 0),
      createVector3D(1, 1, 1)
    );
    const bbox2 = createBoundingBox(
      createVector3D(3, 0, 0),
      createVector3D(4, 1, 1)
    );
    
    expect(checkClearance(bbox1, bbox2, 1.0)).toBe(true);
    expect(checkClearance(bbox1, bbox2, 3.0)).toBe(false);
  });

  it('should calculate walkway width correctly', () => {
    const bbox1 = createBoundingBox(
      createVector3D(0, 0, 0),
      createVector3D(1, 1, 1)
    );
    const bbox2 = createBoundingBox(
      createVector3D(3, 0, 0),
      createVector3D(4, 1, 1)
    );
    
    const width = calculateWalkwayWidth(bbox1, bbox2);
    expect(width).toBeGreaterThan(0);
  });
});

// ============================================================================
// UTILITY FUNCTION TESTS
// ============================================================================

describe('Utility Functions', () => {
  it('should clamp values correctly', () => {
    expect(clamp(5, 0, 10)).toBe(5);
    expect(clamp(-5, 0, 10)).toBe(0);
    expect(clamp(15, 0, 10)).toBe(10);
  });

  it('should interpolate linearly', () => {
    expect(lerp(0, 10, 0.5)).toBe(5);
    expect(lerp(0, 10, 0)).toBe(0);
    expect(lerp(0, 10, 1)).toBe(10);
  });

  it('should interpolate vectors linearly', () => {
    const v1 = createVector3D(0, 0, 0);
    const v2 = createVector3D(10, 10, 10);
    const result = lerpVector3D(v1, v2, 0.5);
    
    expect(result).toEqual({ x: 5, y: 5, z: 5 });
  });

  it('should check approximate equality correctly', () => {
    expect(approximately(1.0, 1.0000001, 1e-6)).toBe(true);
    expect(approximately(1.0, 1.1, 1e-6)).toBe(false);
  });

  it('should check approximate vector equality correctly', () => {
    const v1 = createVector3D(1.0, 2.0, 3.0);
    const v2 = createVector3D(1.0000001, 2.0000001, 3.0000001);
    const v3 = createVector3D(1.1, 2.1, 3.1);
    
    expect(approximatelyEqualVectors(v1, v2, 1e-6)).toBe(true);
    expect(approximatelyEqualVectors(v1, v3, 1e-6)).toBe(false);
  });

  it('should round to decimals correctly', () => {
    expect(roundToDecimals(3.14159, 2)).toBe(3.14);
    expect(roundToDecimals(3.14159, 4)).toBe(3.1416);
  });

  it('should round vectors to decimals correctly', () => {
    const vector = createVector3D(3.14159, 2.71828, 1.41421);
    const rounded = roundVector3D(vector, 2);
    
    expect(rounded).toEqual({ x: 3.14, y: 2.72, z: 1.41 });
  });
});

// ============================================================================
// EDGE CASE TESTS
// ============================================================================

describe('Edge Cases', () => {
  it('should handle zero vectors in operations', () => {
    const zero = createVector3D(0, 0, 0);
    const nonZero = createVector3D(1, 2, 3);
    
    expect(addVectors(zero, nonZero)).toEqual(nonZero);
    expect(subtractVectors(nonZero, zero)).toEqual(nonZero);
    expect(scaleVector(zero, 5)).toEqual(zero);
    expect(dotProduct(zero, nonZero)).toBe(0);
    expect(vectorMagnitude(zero)).toBe(0);
  });

  it('should handle very small numbers in approximately function', () => {
    expect(approximately(1e-15, 0, 1e-14)).toBe(true);
    expect(approximately(1e-5, 0, 1e-6)).toBe(false);
  });

  it('should handle degenerate bounding boxes', () => {
    const point = createVector3D(1, 1, 1);
    const degenerateBBox = createBoundingBox(point, point);
    
    expect(boundingBoxVolume(degenerateBBox)).toBe(0);
    expect(boundingBoxCenter(degenerateBBox)).toEqual(point);
  });

  it('should handle negative scaling', () => {
    const vector = createVector3D(1, 2, 3);
    const scaled = scaleVector(vector, -1);
    
    expect(scaled).toEqual({ x: -1, y: -2, z: -3 });
  });

  it('should handle 360-degree rotations', () => {
    const point = createVector3D(1, 0, 0);
    const rotated = rotatePointZ(point, 360);
    
    expect(approximatelyEqualVectors(point, rotated, 1e-10)).toBe(true);
  });
});