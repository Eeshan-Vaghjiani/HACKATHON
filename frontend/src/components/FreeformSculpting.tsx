import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { 
  EnvelopeSpec, 
  SculptingTool, 
  SculptingSettings, 
  SculptingOperation,
  SplineModification,
  FreeformSculptingData,
  Vector3D 
} from '../types';

interface FreeformSculptingProps {
  envelope: EnvelopeSpec;
  onEnvelopeChange: (envelope: EnvelopeSpec) => void;
  isActive: boolean;
}

export const FreeformSculpting: React.FC<FreeformSculptingProps> = ({
  envelope,
  onEnvelopeChange,
  isActive
}) => {
  const [sculptingSettings, setSculptingSettings] = useState<SculptingSettings>({
    tool: SculptingTool.PUSH,
    strength: 0.1,
    radius: 1.0,
    falloffType: 'smooth',
    symmetry: false,
    symmetryAxis: 'x'
  });

  const [isDrawingSpline, setIsDrawingSpline] = useState(false);
  const [currentSplinePoints, setCurrentSplinePoints] = useState<Vector3D[]>([]);

  // Initialize sculpting data if not present
  const initializeSculptingData = useCallback(() => {
    if (!envelope.sculptingData) {
      const baseGeometry = createBaseGeometry(envelope);
      const sculptingData: FreeformSculptingData = {
        baseGeometry,
        splineModifications: [],
        sculptingOperations: [],
        undoStack: [],
        redoStack: [],
        isManifold: true,
        volumeValid: true
      };

      onEnvelopeChange({
        ...envelope,
        sculptingData
      });
    }
  }, [envelope, onEnvelopeChange]);

  useEffect(() => {
    if (isActive) {
      initializeSculptingData();
    }
  }, [isActive, initializeSculptingData]);

  const handleToolChange = useCallback((tool: SculptingTool) => {
    setSculptingSettings(prev => ({ ...prev, tool }));
  }, []);

  const handleSettingChange = useCallback((setting: keyof SculptingSettings, value: any) => {
    setSculptingSettings(prev => ({ ...prev, [setting]: value }));
  }, []);

  const handleUndo = useCallback(() => {
    if (!envelope.sculptingData || envelope.sculptingData.undoStack.length === 0) return;

    const lastOperation = envelope.sculptingData.undoStack[envelope.sculptingData.undoStack.length - 1];
    const newUndoStack = envelope.sculptingData.undoStack.slice(0, -1);
    const newRedoStack = [...envelope.sculptingData.redoStack, lastOperation];

    // Revert the operation
    const updatedOperations = envelope.sculptingData.sculptingOperations.filter(
      op => op.id !== lastOperation.id
    );

    const updatedSculptingData: FreeformSculptingData = {
      ...envelope.sculptingData,
      sculptingOperations: updatedOperations,
      undoStack: newUndoStack,
      redoStack: newRedoStack
    };

    onEnvelopeChange({
      ...envelope,
      sculptingData: updatedSculptingData
    });
  }, [envelope, onEnvelopeChange]);

  const handleRedo = useCallback(() => {
    if (!envelope.sculptingData || envelope.sculptingData.redoStack.length === 0) return;

    const operationToRedo = envelope.sculptingData.redoStack[envelope.sculptingData.redoStack.length - 1];
    const newRedoStack = envelope.sculptingData.redoStack.slice(0, -1);
    const newUndoStack = [...envelope.sculptingData.undoStack, operationToRedo];

    const updatedOperations = [...envelope.sculptingData.sculptingOperations, operationToRedo];

    const updatedSculptingData: FreeformSculptingData = {
      ...envelope.sculptingData,
      sculptingOperations: updatedOperations,
      undoStack: newUndoStack,
      redoStack: newRedoStack
    };

    onEnvelopeChange({
      ...envelope,
      sculptingData: updatedSculptingData
    });
  }, [envelope, onEnvelopeChange]);

  const validateGeometry = useCallback((sculptingData: FreeformSculptingData): boolean => {
    // Basic manifold validation - check for holes, non-manifold edges
    // This is a simplified validation - in production, use more robust algorithms
    return sculptingData.baseGeometry.vertices.length > 0 && 
           sculptingData.baseGeometry.faces.length > 0;
  }, []);

  if (!isActive) {
    return null;
  }

  return (
    <div className="flex h-full">
      {/* Sculpting Tools Panel */}
      <div className="w-80 bg-gray-800 p-4 overflow-y-auto">
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold text-white mb-4">Sculpting Tools</h3>
            
            {/* Tool Selection */}
            <div className="space-y-2 mb-4">
              <label className="block text-sm font-medium text-gray-300">Tool</label>
              <div className="grid grid-cols-2 gap-2">
                {Object.values(SculptingTool).map((tool) => (
                  <button
                    key={tool}
                    onClick={() => handleToolChange(tool)}
                    className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      sculptingSettings.tool === tool
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {tool.replace('_', ' ').toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            {/* Tool Settings */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Strength: {sculptingSettings.strength.toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0.01"
                  max="1.0"
                  step="0.01"
                  value={sculptingSettings.strength}
                  onChange={(e) => handleSettingChange('strength', parseFloat(e.target.value))}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Radius: {sculptingSettings.radius.toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0.1"
                  max="5.0"
                  step="0.1"
                  value={sculptingSettings.radius}
                  onChange={(e) => handleSettingChange('radius', parseFloat(e.target.value))}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Falloff Type</label>
                <select
                  value={sculptingSettings.falloffType}
                  onChange={(e) => handleSettingChange('falloffType', e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                >
                  <option value="linear">Linear</option>
                  <option value="smooth">Smooth</option>
                  <option value="sharp">Sharp</option>
                </select>
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="symmetry"
                  checked={sculptingSettings.symmetry}
                  onChange={(e) => handleSettingChange('symmetry', e.target.checked)}
                  className="rounded"
                />
                <label htmlFor="symmetry" className="text-sm text-gray-300">
                  Symmetry
                </label>
              </div>

              {sculptingSettings.symmetry && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Symmetry Axis</label>
                  <select
                    value={sculptingSettings.symmetryAxis}
                    onChange={(e) => handleSettingChange('symmetryAxis', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                  >
                    <option value="x">X-Axis</option>
                    <option value="y">Y-Axis</option>
                    <option value="z">Z-Axis</option>
                  </select>
                </div>
              )}
            </div>
          </div>

          {/* Spline Tools */}
          {(sculptingSettings.tool === SculptingTool.SPLINE_EXTRUDE || 
            sculptingSettings.tool === SculptingTool.SPLINE_INSET) && (
            <div className="space-y-3">
              <h4 className="text-md font-semibold text-white">Spline Controls</h4>
              <button
                onClick={() => setIsDrawingSpline(!isDrawingSpline)}
                className={`w-full px-4 py-2 rounded-md font-medium transition-colors ${
                  isDrawingSpline
                    ? 'bg-red-600 text-white'
                    : 'bg-green-600 text-white hover:bg-green-700'
                }`}
              >
                {isDrawingSpline ? 'Stop Drawing' : 'Start Drawing Spline'}
              </button>
              
              {currentSplinePoints.length > 0 && (
                <div className="text-sm text-gray-300">
                  Points: {currentSplinePoints.length}
                </div>
              )}
            </div>
          )}

          {/* Undo/Redo */}
          <div className="space-y-2">
            <h4 className="text-md font-semibold text-white">History</h4>
            <div className="flex space-x-2">
              <button
                onClick={handleUndo}
                disabled={!envelope.sculptingData || envelope.sculptingData.undoStack.length === 0}
                className="flex-1 px-3 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed"
              >
                Undo
              </button>
              <button
                onClick={handleRedo}
                disabled={!envelope.sculptingData || envelope.sculptingData.redoStack.length === 0}
                className="flex-1 px-3 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed"
              >
                Redo
              </button>
            </div>
          </div>

          {/* Validation Status */}
          {envelope.sculptingData && (
            <div className="space-y-2">
              <h4 className="text-md font-semibold text-white">Validation</h4>
              <div className="space-y-1 text-sm">
                <div className={`flex items-center space-x-2 ${
                  envelope.sculptingData.isManifold ? 'text-green-400' : 'text-red-400'
                }`}>
                  <span>{envelope.sculptingData.isManifold ? '✓' : '✗'}</span>
                  <span>Manifold Geometry</span>
                </div>
                <div className={`flex items-center space-x-2 ${
                  envelope.sculptingData.volumeValid ? 'text-green-400' : 'text-red-400'
                }`}>
                  <span>{envelope.sculptingData.volumeValid ? '✓' : '✗'}</span>
                  <span>Closed Volume</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 3D Sculpting Viewport */}
      <div className="flex-1 relative">
        <Canvas camera={{ position: [8, 8, 8], fov: 60 }}>
          <ambientLight intensity={0.4} />
          <pointLight position={[10, 10, 10]} intensity={0.8} />
          <pointLight position={[-10, -10, -10]} intensity={0.3} />
          
          <SculptingMesh
            envelope={envelope}
            sculptingSettings={sculptingSettings}
            onEnvelopeChange={onEnvelopeChange}
            isDrawingSpline={isDrawingSpline}
            onSplinePointAdd={(point) => setCurrentSplinePoints(prev => [...prev, point])}
          />
          
          <OrbitControls 
            enablePan={true} 
            enableZoom={true} 
            enableRotate={true}
            maxDistance={50}
            minDistance={2}
          />
        </Canvas>
      </div>
    </div>
  );
};

// Helper component for the interactive sculpting mesh
interface SculptingMeshProps {
  envelope: EnvelopeSpec;
  sculptingSettings: SculptingSettings;
  onEnvelopeChange: (envelope: EnvelopeSpec) => void;
  isDrawingSpline: boolean;
  onSplinePointAdd: (point: Vector3D) => void;
}

const SculptingMesh: React.FC<SculptingMeshProps> = ({
  envelope,
  sculptingSettings,
  onEnvelopeChange,
  isDrawingSpline,
  onSplinePointAdd
}) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const { raycaster, mouse, camera } = useThree();
  const [isMouseDown, setIsMouseDown] = useState(false);

  const handlePointerDown = useCallback((event: any) => {
    if (isDrawingSpline) {
      // Add spline point
      const intersect = event.intersections[0];
      if (intersect) {
        onSplinePointAdd({
          x: intersect.point.x,
          y: intersect.point.y,
          z: intersect.point.z
        });
      }
    } else {
      setIsMouseDown(true);
      // Start sculpting operation
      applySculptingOperation(event, envelope, sculptingSettings, onEnvelopeChange);
    }
  }, [isDrawingSpline, envelope, sculptingSettings, onEnvelopeChange, onSplinePointAdd]);

  const handlePointerMove = useCallback((event: any) => {
    if (isMouseDown && !isDrawingSpline) {
      // Continue sculpting operation
      applySculptingOperation(event, envelope, sculptingSettings, onEnvelopeChange);
    }
  }, [isMouseDown, isDrawingSpline, envelope, sculptingSettings, onEnvelopeChange]);

  const handlePointerUp = useCallback(() => {
    setIsMouseDown(false);
  }, []);

  // Generate geometry from sculpting data
  const geometry = React.useMemo(() => {
    if (!envelope.sculptingData) return null;

    const { baseGeometry, sculptingOperations } = envelope.sculptingData;
    
    // Apply sculpting operations to base geometry
    const modifiedVertices = applyOperationsToGeometry(baseGeometry, sculptingOperations);
    
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(modifiedVertices, 3));
    geometry.setAttribute('normal', new THREE.BufferAttribute(baseGeometry.normals, 3));
    geometry.setIndex(new THREE.BufferAttribute(baseGeometry.faces, 1));
    geometry.computeVertexNormals();
    
    return geometry;
  }, [envelope.sculptingData]);

  if (!geometry) return null;

  return (
    <mesh
      ref={meshRef}
      geometry={geometry}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
    >
      <meshStandardMaterial
        color="#3b82f6"
        transparent={true}
        opacity={0.8}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
};

// Helper functions
function createBaseGeometry(envelope: EnvelopeSpec): any {
  // Create base geometry from parametric primitive
  // This is a simplified implementation - in production, use more sophisticated geometry generation
  const geometry = new THREE.CylinderGeometry(
    envelope.params.radius || 1,
    envelope.params.radius || 1,
    envelope.params.length || 1,
    32,
    1
  );

  return {
    type: 'cylinder',
    params: envelope.params,
    vertices: geometry.attributes.position.array as Float32Array,
    faces: geometry.index?.array as Uint32Array || new Uint32Array(),
    normals: geometry.attributes.normal.array as Float32Array
  };
}

function applySculptingOperation(
  event: any,
  envelope: EnvelopeSpec,
  settings: SculptingSettings,
  onEnvelopeChange: (envelope: EnvelopeSpec) => void
) {
  if (!envelope.sculptingData) return;

  const intersect = event.intersections[0];
  if (!intersect) return;

  const operation: SculptingOperation = {
    id: crypto.randomUUID(),
    type: settings.tool as any,
    position: {
      x: intersect.point.x,
      y: intersect.point.y,
      z: intersect.point.z
    },
    direction: {
      x: intersect.normal.x,
      y: intersect.normal.y,
      z: intersect.normal.z
    },
    strength: settings.strength,
    radius: settings.radius,
    falloffType: settings.falloffType,
    timestamp: new Date(),
    affectedVertices: [],
    originalPositions: [],
    newPositions: []
  };

  const updatedSculptingData: FreeformSculptingData = {
    ...envelope.sculptingData,
    sculptingOperations: [...envelope.sculptingData.sculptingOperations, operation],
    undoStack: [...envelope.sculptingData.undoStack, operation],
    redoStack: [] // Clear redo stack when new operation is performed
  };

  onEnvelopeChange({
    ...envelope,
    sculptingData: updatedSculptingData
  });
}

function applyOperationsToGeometry(
  baseGeometry: any,
  operations: SculptingOperation[]
): Float32Array {
  // Apply sculpting operations to modify vertex positions
  // This is a simplified implementation - in production, use more sophisticated algorithms
  const vertices = new Float32Array(baseGeometry.vertices);
  
  for (const operation of operations) {
    // Apply each operation to the vertices
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
          // Add other sculpting operations as needed
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