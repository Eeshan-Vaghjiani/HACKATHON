import React, { useMemo } from 'react';
import { Mesh } from 'three';
import * as THREE from 'three';
import { EnvelopeSpec, EnvelopeType } from '../types';

interface VolumePreviewProps {
  envelope: EnvelopeSpec;
}

export const VolumePreview: React.FC<VolumePreviewProps> = ({ envelope }) => {
  // Generate geometry based on envelope type and parameters
  const geometry = useMemo(() => {
    switch (envelope.type) {
      case EnvelopeType.CYLINDER:
        return (
          <cylinderGeometry
            args={[
              envelope.params.radius || 1,
              envelope.params.radius || 1,
              envelope.params.length || 1,
              32,
              1
            ]}
          />
        );
      
      case EnvelopeType.BOX:
        return (
          <boxGeometry
            args={[
              envelope.params.width || 1,
              envelope.params.height || 1,
              envelope.params.depth || 1
            ]}
          />
        );
      
      case EnvelopeType.TORUS:
        return (
          <torusGeometry
            args={[
              envelope.params.majorRadius || 2,
              envelope.params.minorRadius || 0.5,
              16,
              32
            ]}
          />
        );
      
      case EnvelopeType.FREEFORM:
        if (envelope.sculptingData) {
          return <FreeformGeometry sculptingData={envelope.sculptingData} />;
        }
        // Fallback to cylinder for freeform without sculpting data
        return (
          <cylinderGeometry
            args={[
              envelope.params.radius || 1,
              envelope.params.radius || 1,
              envelope.params.length || 1,
              32,
              1
            ]}
          />
        );
      
      default:
        return <boxGeometry args={[1, 1, 1]} />;
    }
  }, [envelope.type, envelope.params]);

  // Material configuration
  const material = useMemo(() => (
    <meshStandardMaterial
      color="#3b82f6"
      transparent={true}
      opacity={0.7}
      wireframe={false}
    />
  ), []);

  // Wireframe overlay for better visualization
  const wireframeMaterial = useMemo(() => (
    <meshBasicMaterial
      color="#60a5fa"
      wireframe={true}
      transparent={true}
      opacity={0.3}
    />
  ), []);

  // Position adjustment for cylinder (rotate to align with Z-axis)
  const rotation = envelope.type === EnvelopeType.CYLINDER ? [Math.PI / 2, 0, 0] : [0, 0, 0];

  return (
    <group>
      {/* Main volume mesh */}
      <mesh rotation={rotation}>
        {geometry}
        {material}
      </mesh>
      
      {/* Wireframe overlay */}
      <mesh rotation={rotation}>
        {geometry}
        {wireframeMaterial}
      </mesh>
      
      {/* Coordinate axes helper */}
      <axesHelper args={[2]} />
      
      {/* Bounding box visualization */}
      <BoundingBoxHelper envelope={envelope} />
    </group>
  );
};

// Helper component for freeform geometry
const FreeformGeometry: React.FC<{ sculptingData: any }> = ({ sculptingData }) => {
  const geometry = useMemo(() => {
    if (!sculptingData || !sculptingData.baseGeometry) return null;

    const { baseGeometry, sculptingOperations } = sculptingData;
    
    // Apply sculpting operations to base geometry
    const modifiedVertices = applyOperationsToGeometry(baseGeometry, sculptingOperations);
    
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(modifiedVertices, 3));
    geometry.setAttribute('normal', new THREE.BufferAttribute(baseGeometry.normals, 3));
    geometry.setIndex(new THREE.BufferAttribute(baseGeometry.faces, 1));
    geometry.computeVertexNormals();
    
    return geometry;
  }, [sculptingData]);

  if (!geometry) return null;

  return <primitive object={geometry} />;
};

// Helper function to apply sculpting operations
function applyOperationsToGeometry(baseGeometry: any, operations: any[]): Float32Array {
  const vertices = new Float32Array(baseGeometry.vertices);
  
  for (const operation of operations) {
    for (let i = 0; i < vertices.length; i += 3) {
      const vertex = {
        x: vertices[i],
        y: vertices[i + 1],
        z: vertices[i + 2]
      };

      const distance = Math.sqrt(
        Math.pow(vertex.x - operation.position.x, 2) +
        Math.pow(vertex.y - operation.position.y, 2) +
        Math.pow(vertex.z - operation.position.z, 2)
      );

      if (distance < operation.radius) {
        const falloff = calculateFalloff(distance, operation.radius, operation.falloffType);
        const displacement = operation.strength * falloff;

        switch (operation.type) {
          case 'push':
            vertices[i] += operation.direction.x * displacement;
            vertices[i + 1] += operation.direction.y * displacement;
            vertices[i + 2] += operation.direction.z * displacement;
            break;
          case 'pull':
            vertices[i] -= operation.direction.x * displacement;
            vertices[i + 1] -= operation.direction.y * displacement;
            vertices[i + 2] -= operation.direction.z * displacement;
            break;
        }
      }
    }
  }

  return vertices;
}

function calculateFalloff(distance: number, radius: number, type: string): number {
  const normalizedDistance = distance / radius;
  
  switch (type) {
    case 'linear':
      return 1 - normalizedDistance;
    case 'smooth':
      return Math.cos(normalizedDistance * Math.PI * 0.5);
    case 'sharp':
      return normalizedDistance < 0.5 ? 1 : 0;
    default:
      return 1 - normalizedDistance;
  }
}

function calculateFreeformBoundingBox(sculptingData: any): [number, number, number] {
  if (!sculptingData || !sculptingData.baseGeometry) {
    return [1, 1, 1];
  }

  const modifiedVertices = applyOperationsToGeometry(
    sculptingData.baseGeometry, 
    sculptingData.sculptingOperations
  );

  let minX = Infinity, maxX = -Infinity;
  let minY = Infinity, maxY = -Infinity;
  let minZ = Infinity, maxZ = -Infinity;

  for (let i = 0; i < modifiedVertices.length; i += 3) {
    const x = modifiedVertices[i];
    const y = modifiedVertices[i + 1];
    const z = modifiedVertices[i + 2];

    minX = Math.min(minX, x);
    maxX = Math.max(maxX, x);
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
    minZ = Math.min(minZ, z);
    maxZ = Math.max(maxZ, z);
  }

  return [maxX - minX, maxY - minY, maxZ - minZ];
}

// Helper component to show bounding box
const BoundingBoxHelper: React.FC<{ envelope: EnvelopeSpec }> = ({ envelope }) => {
  const boundingBoxDimensions = useMemo(() => {
    switch (envelope.type) {
      case EnvelopeType.CYLINDER:
        const radius = envelope.params.radius || 1;
        const length = envelope.params.length || 1;
        return [radius * 2, radius * 2, length];
      
      case EnvelopeType.BOX:
        return [
          envelope.params.width || 1,
          envelope.params.height || 1,
          envelope.params.depth || 1
        ];
      
      case EnvelopeType.TORUS:
        const majorRadius = envelope.params.majorRadius || 2;
        const minorRadius = envelope.params.minorRadius || 0.5;
        const torusDiameter = (majorRadius + minorRadius) * 2;
        return [torusDiameter, torusDiameter, minorRadius * 2];
      
      case EnvelopeType.FREEFORM:
        if (envelope.sculptingData) {
          // Calculate bounding box from sculpted geometry
          return calculateFreeformBoundingBox(envelope.sculptingData);
        }
        // Fallback to cylinder dimensions
        const freeformRadius = envelope.params.radius || 1;
        const freeformLength = envelope.params.length || 1;
        return [freeformRadius * 2, freeformRadius * 2, freeformLength];
      
      default:
        return [1, 1, 1];
    }
  }, [envelope.type, envelope.params]);

  return (
    <mesh>
      <boxGeometry args={boundingBoxDimensions} />
      <meshBasicMaterial
        color="#fbbf24"
        wireframe={true}
        transparent={true}
        opacity={0.2}
      />
    </mesh>
  );
};