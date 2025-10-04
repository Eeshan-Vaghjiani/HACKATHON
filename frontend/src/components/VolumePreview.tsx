import React, { useMemo } from 'react';
import { Mesh } from 'three';
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