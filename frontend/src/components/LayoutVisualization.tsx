import React, { useRef, useState, useCallback, useMemo, useEffect } from 'react';
import { Canvas, useFrame, ThreeElements, useThree } from '@react-three/fiber';
import { OrbitControls, Box, Cylinder, Text, Html } from '@react-three/drei';
import * as THREE from 'three';
import { LayoutSpec, ModulePlacement, EnvelopeSpec, ModuleType, EnvelopeType, Vector3D, BoundingBox } from '../types';
import { 
  createBoundingBoxFromCenter, 
  boundingBoxesIntersect, 
  checkClearance,
  createVector3D,
  distance3D,
  roundVector3D
} from '../types/geometry';

// ============================================================================
// TYPES
// ============================================================================

interface LayoutVisualizationProps {
  layout: LayoutSpec;
  envelope: EnvelopeSpec;
  viewMode?: 'inspect' | 'edit' | 'compare';
  onModuleSelect?: (moduleId: string) => void;
  onModuleMove?: (moduleId: string, newPosition: [number, number, number]) => void;
  onModuleRotate?: (moduleId: string, newRotation: number) => void;
  onLayoutChange?: (updatedLayout: LayoutSpec) => void;
  showMetrics?: boolean;
  highlightedModules?: string[];
  constraintViolations?: string[];
  snapToGrid?: boolean;
  gridSize?: number;
}

interface ModuleVisualizationProps {
  module: ModulePlacement;
  isSelected?: boolean;
  isHighlighted?: boolean;
  hasConstraintViolation?: boolean;
  onSelect?: () => void;
  onMove?: (newPosition: [number, number, number]) => void;
  onRotate?: (newRotation: number) => void;
  editable?: boolean;
  snapToGrid?: boolean;
  gridSize?: number;
  allModules?: ModulePlacement[];
  envelope?: EnvelopeSpec;
}

interface EnvelopeVisualizationProps {
  envelope: EnvelopeSpec;
  opacity?: number;
}

interface ConstraintValidationResult {
  isValid: boolean;
  violations: ConstraintViolation[];
}

interface ConstraintViolation {
  type: 'collision' | 'clearance' | 'envelope' | 'connectivity';
  message: string;
  moduleIds: string[];
  severity: 'error' | 'warning';
}

// ============================================================================
// CONSTRAINT VALIDATION UTILITIES
// ============================================================================

const MIN_CLEARANCE = 0.8; // meters
const SNAP_THRESHOLD = 0.2; // meters for snap-to-grid

/**
 * Get module dimensions based on type
 */
function getModuleDimensions(moduleType: ModuleType): [number, number, number] {
  switch (moduleType) {
    case ModuleType.SLEEP_QUARTER:
      return [2.0, 2.0, 2.5];
    case ModuleType.GALLEY:
      return [3.0, 2.5, 2.2];
    case ModuleType.LABORATORY:
      return [4.0, 3.0, 2.8];
    case ModuleType.AIRLOCK:
      return [2.5, 2.5, 3.0];
    case ModuleType.MECHANICAL:
      return [3.5, 2.8, 2.5];
    case ModuleType.MEDICAL:
      return [3.0, 2.5, 2.5];
    case ModuleType.EXERCISE:
      return [4.0, 3.5, 2.8];
    case ModuleType.STORAGE:
      return [2.5, 2.0, 2.0];
    default:
      return [2.0, 2.0, 2.0];
  }
}

/**
 * Create bounding box for a module
 */
function createModuleBoundingBox(module: ModulePlacement): BoundingBox {
  const dimensions = getModuleDimensions(module.type);
  const center = createVector3D(module.position[0], module.position[1], module.position[2]);
  const size = createVector3D(dimensions[0], dimensions[1], dimensions[2]);
  return createBoundingBoxFromCenter(center, size);
}

/**
 * Check if a point is inside the envelope
 */
function pointInEnvelope(point: Vector3D, envelope: EnvelopeSpec): boolean {
  switch (envelope.type) {
    case EnvelopeType.CYLINDER:
      const radius = envelope.params.radius;
      const length = envelope.params.length;
      const distanceFromAxis = Math.sqrt(point.x * point.x + point.y * point.y);
      return distanceFromAxis <= radius && Math.abs(point.z) <= length / 2;
    
    case EnvelopeType.BOX:
      const width = envelope.params.width;
      const height = envelope.params.height;
      const depth = envelope.params.depth;
      return (
        Math.abs(point.x) <= width / 2 &&
        Math.abs(point.y) <= height / 2 &&
        Math.abs(point.z) <= depth / 2
      );
    
    case EnvelopeType.TORUS:
      const majorRadius = envelope.params.major_radius;
      const minorRadius = envelope.params.minor_radius;
      const distanceFromCenter = Math.sqrt(point.x * point.x + point.y * point.y);
      const distanceFromTube = Math.sqrt(
        Math.pow(distanceFromCenter - majorRadius, 2) + point.z * point.z
      );
      return distanceFromTube <= minorRadius;
    
    default:
      return true;
  }
}

/**
 * Validate module placement constraints
 */
function validateModulePlacement(
  module: ModulePlacement,
  allModules: ModulePlacement[],
  envelope: EnvelopeSpec
): ConstraintValidationResult {
  const violations: ConstraintViolation[] = [];
  const moduleBBox = createModuleBoundingBox(module);
  
  // Check envelope constraints
  const moduleCenter = createVector3D(module.position[0], module.position[1], module.position[2]);
  if (!pointInEnvelope(moduleCenter, envelope)) {
    violations.push({
      type: 'envelope',
      message: 'Module extends outside habitat envelope',
      moduleIds: [module.module_id],
      severity: 'error'
    });
  }
  
  // Check collision with other modules
  for (const otherModule of allModules) {
    if (otherModule.module_id === module.module_id) continue;
    
    const otherBBox = createModuleBoundingBox(otherModule);
    
    // Check for collision
    if (boundingBoxesIntersect(moduleBBox, otherBBox)) {
      violations.push({
        type: 'collision',
        message: `Collision with ${otherModule.type}`,
        moduleIds: [module.module_id, otherModule.module_id],
        severity: 'error'
      });
    }
    
    // Check clearance
    if (!checkClearance(moduleBBox, otherBBox, MIN_CLEARANCE)) {
      violations.push({
        type: 'clearance',
        message: `Insufficient clearance with ${otherModule.type}`,
        moduleIds: [module.module_id, otherModule.module_id],
        severity: 'warning'
      });
    }
  }
  
  return {
    isValid: violations.filter(v => v.severity === 'error').length === 0,
    violations
  };
}

/**
 * Snap position to grid
 */
function snapToGrid(position: [number, number, number], gridSize: number): [number, number, number] {
  return [
    Math.round(position[0] / gridSize) * gridSize,
    Math.round(position[1] / gridSize) * gridSize,
    Math.round(position[2] / gridSize) * gridSize
  ];
}

// ============================================================================
// MODULE COLORS AND GEOMETRIES
// ============================================================================

const MODULE_COLORS: Record<ModuleType, string> = {
  [ModuleType.SLEEP_QUARTER]: '#4F46E5', // Indigo
  [ModuleType.GALLEY]: '#059669', // Emerald
  [ModuleType.LABORATORY]: '#DC2626', // Red
  [ModuleType.AIRLOCK]: '#EA580C', // Orange
  [ModuleType.MECHANICAL]: '#7C2D12', // Brown
  [ModuleType.MEDICAL]: '#BE185D', // Pink
  [ModuleType.EXERCISE]: '#7C3AED', // Violet
  [ModuleType.STORAGE]: '#6B7280', // Gray
};

const MODULE_NAMES: Record<ModuleType, string> = {
  [ModuleType.SLEEP_QUARTER]: 'Sleep Quarter',
  [ModuleType.GALLEY]: 'Galley',
  [ModuleType.LABORATORY]: 'Laboratory',
  [ModuleType.AIRLOCK]: 'Airlock',
  [ModuleType.MECHANICAL]: 'Mechanical',
  [ModuleType.MEDICAL]: 'Medical',
  [ModuleType.EXERCISE]: 'Exercise',
  [ModuleType.STORAGE]: 'Storage',
};

// ============================================================================
// ENVELOPE VISUALIZATION COMPONENT
// ============================================================================

const EnvelopeVisualization: React.FC<EnvelopeVisualizationProps> = ({ 
  envelope, 
  opacity = 0.1 
}) => {
  const meshRef = useRef<THREE.Mesh>(null);

  const geometry = useMemo(() => {
    switch (envelope.type) {
      case EnvelopeType.CYLINDER:
        return new THREE.CylinderGeometry(
          envelope.params.radius,
          envelope.params.radius,
          envelope.params.length,
          32
        );
      case EnvelopeType.BOX:
        return new THREE.BoxGeometry(
          envelope.params.width,
          envelope.params.height,
          envelope.params.depth
        );
      case EnvelopeType.TORUS:
        return new THREE.TorusGeometry(
          envelope.params.major_radius,
          envelope.params.minor_radius,
          16,
          32
        );
      default:
        return new THREE.SphereGeometry(5, 32, 32);
    }
  }, [envelope]);

  return (
    <mesh ref={meshRef} geometry={geometry}>
      <meshStandardMaterial
        color="#ffffff"
        transparent
        opacity={opacity}
        wireframe
      />
    </mesh>
  );
};

// ============================================================================
// INTERACTIVE MODULE COMPONENT
// ============================================================================

const InteractiveModule: React.FC<ModuleVisualizationProps> = ({
  module,
  isSelected = false,
  isHighlighted = false,
  hasConstraintViolation = false,
  onSelect,
  onMove,
  onRotate,
  editable = false,
  snapToGrid = false,
  gridSize = 0.5,
  allModules = [],
  envelope
}) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const groupRef = useRef<THREE.Group>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [tempPosition, setTempPosition] = useState<[number, number, number]>(module.position);
  const [validationResult, setValidationResult] = useState<ConstraintValidationResult>({ isValid: true, violations: [] });

  const dimensions = useMemo(() => getModuleDimensions(module.type), [module.type]);

  // Validate current position
  useEffect(() => {
    if (envelope) {
      const result = validateModulePlacement(
        { ...module, position: tempPosition },
        allModules,
        envelope
      );
      setValidationResult(result);
    }
  }, [tempPosition, allModules, envelope, module]);

  const getModuleColor = useCallback(() => {
    if (hasConstraintViolation || !validationResult.isValid) return '#FF4444'; // Red for violations
    if (isSelected) return '#FFD700'; // Gold for selected
    if (isHighlighted) return '#FF6B6B'; // Light red for highlighted
    if (isDragging && !validationResult.isValid) return '#FF8888'; // Light red while dragging invalid
    if (isDragging && validationResult.isValid) return '#88FF88'; // Light green while dragging valid
    return MODULE_COLORS[module.type]; // Default color
  }, [hasConstraintViolation, validationResult.isValid, isSelected, isHighlighted, isDragging, module.type]);

  const opacity = useMemo(() => {
    if (isDragging) return 0.8;
    if (hovered) return 0.9;
    return 0.7;
  }, [isDragging, hovered]);

  const handleClick = useCallback((event: ThreeElements['mesh']['onClick']) => {
    event?.stopPropagation();
    onSelect?.();
  }, [onSelect]);

  const handlePointerOver = useCallback(() => {
    setHovered(true);
    document.body.style.cursor = editable ? 'grab' : 'pointer';
  }, [editable]);

  const handlePointerOut = useCallback(() => {
    setHovered(false);
    if (!isDragging) {
      document.body.style.cursor = 'default';
    }
  }, [isDragging]);

  const handlePointerDown = useCallback((event: ThreeElements['mesh']['onPointerDown']) => {
    if (!editable || !event) return;
    event.stopPropagation();
    setIsDragging(true);
    document.body.style.cursor = 'grabbing';
  }, [editable]);

  const handlePointerMove = useCallback((event: ThreeElements['mesh']['onPointerMove']) => {
    if (!isDragging || !editable || !event) return;
    
    // Get the intersection point
    const intersection = event.intersections[0];
    if (intersection) {
      let newPosition: [number, number, number] = [
        intersection.point.x,
        module.position[1], // Keep Y position constant for now
        intersection.point.z
      ];
      
      // Apply snap to grid if enabled
      if (snapToGrid) {
        newPosition = snapToGrid(newPosition, gridSize);
      }
      
      setTempPosition(newPosition);
    }
  }, [isDragging, editable, snapToGrid, gridSize, module.position]);

  const handlePointerUp = useCallback(() => {
    if (!editable) return;
    
    setIsDragging(false);
    document.body.style.cursor = 'default';
    
    // Only commit the move if it's valid
    if (validationResult.isValid) {
      onMove?.(tempPosition);
    } else {
      // Revert to original position
      setTempPosition(module.position);
    }
  }, [editable, validationResult.isValid, onMove, tempPosition, module.position]);

  const handleRotate = useCallback((rotation: number) => {
    if (!editable) return;
    onRotate?.(rotation);
  }, [editable, onRotate]);

  const currentPosition = isDragging ? tempPosition : module.position;

  return (
    <group ref={groupRef} position={currentPosition} rotation={[0, (module.rotation_deg * Math.PI) / 180, 0]}>
      {/* Visual feedback for dragging */}
      {isDragging && (
        <mesh position={[0, -dimensions[1] / 2 - 0.2, 0]}>
          <cylinderGeometry args={[0.1, 0.1, 0.1]} />
          <meshBasicMaterial 
            color={validationResult.isValid ? "#00FF00" : "#FF0000"} 
            transparent 
            opacity={0.8} 
          />
        </mesh>
      )}

      {/* Main module geometry */}
      <Box
        ref={meshRef}
        args={dimensions}
        onClick={handleClick}
        onPointerOver={handlePointerOver}
        onPointerOut={handlePointerOut}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
      >
        <meshStandardMaterial
          color={getModuleColor()}
          transparent
          opacity={opacity}
          roughness={0.3}
          metalness={0.1}
        />
      </Box>

      {/* Constraint violation indicators */}
      {!validationResult.isValid && (
        <Box args={[dimensions[0] + 0.4, dimensions[1] + 0.4, dimensions[2] + 0.4]}>
          <meshBasicMaterial
            color="#FF0000"
            transparent
            opacity={0.3}
            wireframe
          />
        </Box>
      )}

      {/* Selection indicator */}
      {isSelected && (
        <Box args={[dimensions[0] + 0.2, dimensions[1] + 0.2, dimensions[2] + 0.2]}>
          <meshBasicMaterial
            color="#FFD700"
            transparent
            opacity={0.2}
            wireframe
          />
        </Box>
      )}

      {/* Snap-to-grid indicator */}
      {isSelected && editable && snapToGrid && (
        <mesh position={[0, -dimensions[1] / 2 - 0.1, 0]}>
          <planeGeometry args={[gridSize, gridSize]} />
          <meshBasicMaterial
            color="#00FF00"
            transparent
            opacity={0.3}
            wireframe
          />
        </mesh>
      )}

      {/* Module label */}
      {(hovered || isSelected) && (
        <Html position={[0, dimensions[1] / 2 + 0.5, 0]} center>
          <div className="bg-black bg-opacity-75 text-white px-2 py-1 rounded text-sm whitespace-nowrap">
            {MODULE_NAMES[module.type]}
            <br />
            <span className="text-xs text-gray-300">{module.module_id}</span>
            {!validationResult.isValid && (
              <div className="text-xs text-red-400 mt-1">
                {validationResult.violations.map(v => v.message).join(', ')}
              </div>
            )}
          </div>
        </Html>
      )}

      {/* Connection ports */}
      {module.connections.map((connectionId, index) => (
        <mesh
          key={connectionId}
          position={[
            (dimensions[0] / 2) * Math.cos((index * 2 * Math.PI) / module.connections.length),
            0,
            (dimensions[2] / 2) * Math.sin((index * 2 * Math.PI) / module.connections.length)
          ]}
        >
          <sphereGeometry args={[0.1]} />
          <meshBasicMaterial color="#00FF00" />
        </mesh>
      ))}

      {/* Rotation controls */}
      {isSelected && editable && (
        <group position={[0, dimensions[1] / 2 + 1, 0]}>
          <Html center>
            <div className="flex space-x-1">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleRotate(module.rotation_deg - 15);
                }}
                className="bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded text-xs"
              >
                ↺ -15°
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleRotate(module.rotation_deg + 15);
                }}
                className="bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded text-xs"
              >
                ↻ +15°
              </button>
            </div>
          </Html>
        </group>
      )}
    </group>
  );
};

// Legacy component for backward compatibility
const ModuleVisualization: React.FC<ModuleVisualizationProps> = (props) => {
  return <InteractiveModule {...props} />;
};

// ============================================================================
// GRID VISUALIZATION COMPONENT
// ============================================================================

const GridVisualization: React.FC<{ size: number; divisions: number; visible: boolean }> = ({ 
  size, 
  divisions, 
  visible 
}) => {
  if (!visible) return null;

  return (
    <group>
      <gridHelper 
        args={[size, divisions, '#444444', '#222222']} 
        position={[0, -0.01, 0]} 
      />
      {/* Add vertical grid lines for 3D effect */}
      <gridHelper 
        args={[size, divisions, '#333333', '#111111']} 
        position={[0, -0.01, 0]}
        rotation={[Math.PI / 2, 0, 0]}
      />
    </group>
  );
};

// ============================================================================
// CONNECTION LINES COMPONENT
// ============================================================================

const ConnectionLines: React.FC<{ modules: ModulePlacement[] }> = ({ modules }) => {
  const lines = useMemo(() => {
    const connections: Array<[number[], number[]]> = [];
    
    // Create a map of module positions
    const modulePositions = new Map<string, number[]>();
    modules.forEach(module => {
      modulePositions.set(module.module_id, module.position);
    });

    // Find connections between modules
    modules.forEach(module => {
      module.connections.forEach(connectedId => {
        const connectedPosition = modulePositions.get(connectedId);
        if (connectedPosition) {
          connections.push([module.position, connectedPosition]);
        }
      });
    });

    return connections;
  }, [modules]);

  return (
    <>
      {lines.map(([start, end], index) => {
        const points = [new THREE.Vector3(...start), new THREE.Vector3(...end)];
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        
        return (
          <line key={index} geometry={geometry}>
            <lineBasicMaterial color="#00FF00" opacity={0.6} transparent />
          </line>
        );
      })}
    </>
  );
};

// ============================================================================
// HEATMAP VISUALIZATION COMPONENT
// ============================================================================

interface HeatmapData {
  position: Vector3D;
  intensity: number; // 0-1 scale
  type: 'movement' | 'congestion' | 'power' | 'thermal';
}

interface HeatmapVisualizationProps {
  data: HeatmapData[];
  type: 'movement' | 'congestion' | 'power' | 'thermal';
  visible: boolean;
  opacity?: number;
}

const HeatmapVisualization: React.FC<HeatmapVisualizationProps> = ({
  data,
  type,
  visible,
  opacity = 0.6
}) => {
  const getHeatmapColor = useCallback((intensity: number, heatmapType: string) => {
    // Normalize intensity to 0-1
    const normalizedIntensity = Math.max(0, Math.min(1, intensity));
    
    switch (heatmapType) {
      case 'movement':
        // Blue to red gradient for movement patterns
        return new THREE.Color().setHSL(0.7 - (normalizedIntensity * 0.7), 1, 0.5);
      case 'congestion':
        // Green to red gradient for congestion
        return new THREE.Color().setHSL(0.33 - (normalizedIntensity * 0.33), 1, 0.5);
      case 'power':
        // Yellow to red gradient for power consumption
        return new THREE.Color().setHSL(0.17 - (normalizedIntensity * 0.17), 1, 0.5);
      case 'thermal':
        // Blue to red gradient for thermal load
        return new THREE.Color().setHSL(0.67 - (normalizedIntensity * 0.67), 1, 0.5);
      default:
        return new THREE.Color(0x888888);
    }
  }, []);

  if (!visible || data.length === 0) return null;

  return (
    <group>
      {data.map((point, index) => {
        const color = getHeatmapColor(point.intensity, type);
        const size = 0.5 + (point.intensity * 1.5); // Scale size based on intensity
        
        return (
          <mesh
            key={index}
            position={[point.position.x, point.position.y + 0.1, point.position.z]}
          >
            <sphereGeometry args={[size, 8, 8]} />
            <meshBasicMaterial
              color={color}
              transparent
              opacity={opacity * point.intensity}
            />
          </mesh>
        );
      })}
    </group>
  );
};

// ============================================================================
// METRIC OVERLAY VISUALIZATION COMPONENT
// ============================================================================

interface MetricOverlayProps {
  modules: ModulePlacement[];
  overlayType: 'power' | 'thermal' | 'airflow' | 'none';
  visible: boolean;
}

const MetricOverlayVisualization: React.FC<MetricOverlayProps> = ({
  modules,
  overlayType,
  visible
}) => {
  const getMetricValue = useCallback((module: ModulePlacement, type: string): number => {
    // Mock metric values - in real implementation, these would come from the backend
    const mockMetrics: Record<string, Record<ModuleType, number>> = {
      power: {
        [ModuleType.SLEEP_QUARTER]: 0.2,
        [ModuleType.GALLEY]: 0.8,
        [ModuleType.LABORATORY]: 0.9,
        [ModuleType.AIRLOCK]: 0.3,
        [ModuleType.MECHANICAL]: 1.0,
        [ModuleType.MEDICAL]: 0.6,
        [ModuleType.EXERCISE]: 0.7,
        [ModuleType.STORAGE]: 0.1,
      },
      thermal: {
        [ModuleType.SLEEP_QUARTER]: 0.3,
        [ModuleType.GALLEY]: 0.9,
        [ModuleType.LABORATORY]: 0.7,
        [ModuleType.AIRLOCK]: 0.2,
        [ModuleType.MECHANICAL]: 0.8,
        [ModuleType.MEDICAL]: 0.5,
        [ModuleType.EXERCISE]: 0.8,
        [ModuleType.STORAGE]: 0.1,
      },
      airflow: {
        [ModuleType.SLEEP_QUARTER]: 0.4,
        [ModuleType.GALLEY]: 0.8,
        [ModuleType.LABORATORY]: 0.9,
        [ModuleType.AIRLOCK]: 1.0,
        [ModuleType.MECHANICAL]: 0.7,
        [ModuleType.MEDICAL]: 0.6,
        [ModuleType.EXERCISE]: 0.8,
        [ModuleType.STORAGE]: 0.2,
      }
    };
    
    return mockMetrics[type]?.[module.type] || 0;
  }, []);

  const getOverlayColor = useCallback((value: number, type: string) => {
    const normalizedValue = Math.max(0, Math.min(1, value));
    
    switch (type) {
      case 'power':
        // Green to red for power consumption
        return new THREE.Color().setHSL(0.33 - (normalizedValue * 0.33), 1, 0.5);
      case 'thermal':
        // Blue to red for thermal load
        return new THREE.Color().setHSL(0.67 - (normalizedValue * 0.67), 1, 0.5);
      case 'airflow':
        // Cyan to magenta for airflow
        return new THREE.Color().setHSL(0.5 + (normalizedValue * 0.33), 1, 0.5);
      default:
        return new THREE.Color(0x888888);
    }
  }, []);

  if (!visible || overlayType === 'none') return null;

  return (
    <group>
      {modules.map((module) => {
        const metricValue = getMetricValue(module, overlayType);
        const color = getOverlayColor(metricValue, overlayType);
        const dimensions = getModuleDimensions(module.type);
        
        return (
          <group key={`${module.module_id}-overlay`} position={module.position}>
            {/* Overlay box slightly larger than module */}
            <Box args={[dimensions[0] + 0.1, dimensions[1] + 0.1, dimensions[2] + 0.1]}>
              <meshBasicMaterial
                color={color}
                transparent
                opacity={0.3}
                wireframe
              />
            </Box>
            
            {/* Metric value display */}
            <Html position={[0, dimensions[1] / 2 + 0.8, 0]} center>
              <div className="bg-black bg-opacity-75 text-white px-2 py-1 rounded text-xs">
                {overlayType}: {(metricValue * 100).toFixed(0)}%
              </div>
            </Html>
          </group>
        );
      })}
    </group>
  );
};

// ============================================================================
// CONGESTION AND BOTTLENECK VISUALIZATION
// ============================================================================

interface CongestionPoint {
  position: Vector3D;
  severity: number; // 0-1 scale
  type: 'bottleneck' | 'high_traffic' | 'emergency_path';
}

interface CongestionVisualizationProps {
  congestionPoints: CongestionPoint[];
  visible: boolean;
}

const CongestionVisualization: React.FC<CongestionVisualizationProps> = ({
  congestionPoints,
  visible
}) => {
  if (!visible || congestionPoints.length === 0) return null;

  return (
    <group>
      {congestionPoints.map((point, index) => {
        const color = point.type === 'emergency_path' 
          ? new THREE.Color(0xFF0000) 
          : point.type === 'bottleneck'
          ? new THREE.Color(0xFF8800)
          : new THREE.Color(0xFFFF00);
        
        const size = 0.3 + (point.severity * 0.7);
        
        return (
          <group key={index}>
            {/* Pulsing indicator */}
            <mesh position={[point.position.x, point.position.y + 0.5, point.position.z]}>
              <cylinderGeometry args={[size, size * 0.5, 0.1]} />
              <meshBasicMaterial
                color={color}
                transparent
                opacity={0.7}
              />
            </mesh>
            
            {/* Warning icon */}
            <Html position={[point.position.x, point.position.y + 1, point.position.z]} center>
              <div className="text-yellow-400 text-xl animate-pulse">
                ⚠️
              </div>
            </Html>
          </group>
        );
      })}
    </group>
  );
};

// ============================================================================
// VISUALIZATION CONTROLS COMPONENT
// ============================================================================

interface VisualizationControlsProps {
  activeOverlay: 'none' | 'movement' | 'congestion' | 'power' | 'thermal' | 'airflow';
  onOverlayChange: (overlay: 'none' | 'movement' | 'congestion' | 'power' | 'thermal' | 'airflow') => void;
  showHeatmap: boolean;
  onHeatmapToggle: (show: boolean) => void;
  showCongestion: boolean;
  onCongestionToggle: (show: boolean) => void;
}

const VisualizationControls: React.FC<VisualizationControlsProps> = ({
  activeOverlay,
  onOverlayChange,
  showHeatmap,
  onHeatmapToggle,
  showCongestion,
  onCongestionToggle
}) => {
  return (
    <div className="absolute bottom-4 right-4 bg-black bg-opacity-75 text-white p-3 rounded-lg">
      <h4 className="text-sm font-semibold mb-2">Visualization Overlays</h4>
      
      <div className="space-y-2">
        {/* Overlay type selector */}
        <div>
          <label className="text-xs text-gray-300 block mb-1">Metric Overlay:</label>
          <select
            value={activeOverlay}
            onChange={(e) => onOverlayChange(e.target.value as any)}
            className="bg-gray-700 text-white text-sm rounded px-2 py-1 w-full"
          >
            <option value="none">None</option>
            <option value="power">Power Consumption</option>
            <option value="thermal">Thermal Load</option>
            <option value="airflow">Airflow</option>
          </select>
        </div>
        
        {/* Heatmap toggle */}
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="heatmapToggle"
            checked={showHeatmap}
            onChange={(e) => onHeatmapToggle(e.target.checked)}
            className="rounded"
          />
          <label htmlFor="heatmapToggle" className="text-sm">Movement Heatmap</label>
        </div>
        
        {/* Congestion toggle */}
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="congestionToggle"
            checked={showCongestion}
            onChange={(e) => onCongestionToggle(e.target.checked)}
            className="rounded"
          />
          <label htmlFor="congestionToggle" className="text-sm">Congestion Points</label>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// METRICS OVERLAY COMPONENT
// ============================================================================

const MetricsOverlay: React.FC<{ layout: LayoutSpec }> = ({ layout }) => {
  const { kpis } = layout;

  return (
    <div className="absolute top-4 right-4 bg-black bg-opacity-75 text-white p-4 rounded-lg min-w-64">
      <h3 className="text-lg font-semibold mb-3">Performance Metrics</h3>
      
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span>Transit Time:</span>
          <span>{kpis.meanTransitTime.toFixed(1)}s</span>
        </div>
        
        <div className="flex justify-between">
          <span>Egress Time:</span>
          <span>{kpis.egressTime.toFixed(1)}s</span>
        </div>
        
        <div className="flex justify-between">
          <span>Total Mass:</span>
          <span>{(kpis.massTotal / 1000).toFixed(1)}t</span>
        </div>
        
        <div className="flex justify-between">
          <span>Power Budget:</span>
          <span>{(kpis.powerBudget / 1000).toFixed(1)}kW</span>
        </div>
        
        <div className="flex justify-between">
          <span>Thermal Margin:</span>
          <span className={kpis.thermalMargin < 0 ? 'text-red-400' : 'text-green-400'}>
            {(kpis.thermalMargin * 100).toFixed(1)}%
          </span>
        </div>
        
        <div className="flex justify-between">
          <span>LSS Margin:</span>
          <span className={kpis.lssMargin < 0 ? 'text-red-400' : 'text-green-400'}>
            {(kpis.lssMargin * 100).toFixed(1)}%
          </span>
        </div>
        
        <div className="flex justify-between">
          <span>Stowage Util:</span>
          <span className={kpis.stowageUtilization > 1 ? 'text-red-400' : 'text-green-400'}>
            {(kpis.stowageUtilization * 100).toFixed(1)}%
          </span>
        </div>

        {kpis.connectivityScore !== undefined && (
          <div className="flex justify-between">
            <span>Connectivity:</span>
            <span>{(kpis.connectivityScore * 100).toFixed(1)}%</span>
          </div>
        )}

        {kpis.safetyScore !== undefined && (
          <div className="flex justify-between">
            <span>Safety Score:</span>
            <span>{(kpis.safetyScore * 100).toFixed(1)}%</span>
          </div>
        )}
      </div>

      <div className="mt-3 pt-3 border-t border-gray-600">
        <div className="flex justify-between font-semibold">
          <span>Overall Score:</span>
          <span className="text-blue-400">
            {((kpis.safetyScore || 0.8) * 100).toFixed(1)}%
          </span>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// MAIN LAYOUT VISUALIZATION COMPONENT
// ============================================================================

export const LayoutVisualization: React.FC<LayoutVisualizationProps> = ({
  layout,
  envelope,
  viewMode = 'inspect',
  onModuleSelect,
  onModuleMove,
  onModuleRotate,
  onLayoutChange,
  showMetrics = true,
  highlightedModules = [],
  constraintViolations = [],
  snapToGrid = false,
  gridSize = 0.5
}) => {
  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);
  const [showGrid, setShowGrid] = useState(viewMode === 'edit');
  const [editingMode, setEditingMode] = useState<'translate' | 'rotate'>('translate');
  const [localLayout, setLocalLayout] = useState<LayoutSpec>(layout);
  
  // Visualization overlay states
  const [activeOverlay, setActiveOverlay] = useState<'none' | 'movement' | 'congestion' | 'power' | 'thermal' | 'airflow'>('none');
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [showCongestion, setShowCongestion] = useState(false);

  // Update local layout when prop changes
  useEffect(() => {
    setLocalLayout(layout);
  }, [layout]);

  // Show grid when in edit mode
  useEffect(() => {
    setShowGrid(viewMode === 'edit');
  }, [viewMode]);

  const handleModuleSelect = useCallback((moduleId: string) => {
    setSelectedModuleId(moduleId);
    onModuleSelect?.(moduleId);
  }, [onModuleSelect]);

  const handleModuleMove = useCallback((moduleId: string, newPosition: [number, number, number]) => {
    // Update local layout
    const updatedLayout = {
      ...localLayout,
      modules: localLayout.modules.map(module =>
        module.module_id === moduleId
          ? { ...module, position: newPosition }
          : module
      )
    };
    
    setLocalLayout(updatedLayout);
    onModuleMove?.(moduleId, newPosition);
    onLayoutChange?.(updatedLayout);
  }, [localLayout, onModuleMove, onLayoutChange]);

  const handleModuleRotate = useCallback((moduleId: string, newRotation: number) => {
    // Normalize rotation to 0-360 range
    const normalizedRotation = ((newRotation % 360) + 360) % 360;
    
    // Update local layout
    const updatedLayout = {
      ...localLayout,
      modules: localLayout.modules.map(module =>
        module.module_id === moduleId
          ? { ...module, rotation_deg: normalizedRotation }
          : module
      )
    };
    
    setLocalLayout(updatedLayout);
    onModuleRotate?.(moduleId, normalizedRotation);
    onLayoutChange?.(updatedLayout);
  }, [localLayout, onModuleRotate, onLayoutChange]);

  // Calculate constraint violations for each module
  const moduleViolations = useMemo(() => {
    const violations = new Set<string>();
    
    localLayout.modules.forEach(module => {
      const result = validateModulePlacement(module, localLayout.modules, envelope);
      if (!result.isValid) {
        violations.add(module.module_id);
      }
    });
    
    // Add violations from props
    constraintViolations.forEach(moduleId => violations.add(moduleId));
    
    return violations;
  }, [localLayout.modules, envelope, constraintViolations]);

  // Generate mock heatmap data
  const heatmapData = useMemo((): HeatmapData[] => {
    if (!showHeatmap) return [];
    
    // Generate movement heatmap based on module positions and connections
    const data: HeatmapData[] = [];
    
    localLayout.modules.forEach(module => {
      // Add high-traffic areas around galley, laboratory, and airlocks
      const baseIntensity = module.type === ModuleType.GALLEY ? 0.9 :
                           module.type === ModuleType.LABORATORY ? 0.7 :
                           module.type === ModuleType.AIRLOCK ? 0.8 :
                           module.type === ModuleType.EXERCISE ? 0.6 : 0.3;
      
      // Add points around the module
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2;
        const radius = 2 + Math.random() * 2;
        data.push({
          position: createVector3D(
            module.position[0] + Math.cos(angle) * radius,
            module.position[1],
            module.position[2] + Math.sin(angle) * radius
          ),
          intensity: baseIntensity * (0.5 + Math.random() * 0.5),
          type: 'movement'
        });
      }
    });
    
    return data;
  }, [localLayout.modules, showHeatmap]);

  // Generate mock congestion points
  const congestionPoints = useMemo((): CongestionPoint[] => {
    if (!showCongestion) return [];
    
    const points: CongestionPoint[] = [];
    
    // Find potential bottlenecks between modules
    for (let i = 0; i < localLayout.modules.length; i++) {
      for (let j = i + 1; j < localLayout.modules.length; j++) {
        const module1 = localLayout.modules[i];
        const module2 = localLayout.modules[j];
        
        const distance = distance3D(
          createVector3D(...module1.position),
          createVector3D(...module2.position)
        );
        
        // If modules are close, create a potential bottleneck point
        if (distance < 6) {
          const midpoint = createVector3D(
            (module1.position[0] + module2.position[0]) / 2,
            (module1.position[1] + module2.position[1]) / 2,
            (module1.position[2] + module2.position[2]) / 2
          );
          
          points.push({
            position: midpoint,
            severity: Math.max(0.3, 1 - (distance / 6)),
            type: distance < 3 ? 'bottleneck' : 'high_traffic'
          });
        }
      }
    }
    
    // Add emergency path points near airlocks
    localLayout.modules
      .filter(m => m.type === ModuleType.AIRLOCK)
      .forEach(airlock => {
        points.push({
          position: createVector3D(
            airlock.position[0],
            airlock.position[1] + 0.5,
            airlock.position[2] + 3
          ),
          severity: 0.8,
          type: 'emergency_path'
        });
      });
    
    return points;
  }, [localLayout.modules, showCongestion]);

  // Calculate optimal camera position based on layout bounds
  const optimalCameraPosition = useMemo(() => {
    if (localLayout.modules.length === 0) return [10, 10, 10] as [number, number, number];

    const positions = localLayout.modules.map(m => m.position);
    const bounds = {
      minX: Math.min(...positions.map(p => p[0])),
      maxX: Math.max(...positions.map(p => p[0])),
      minY: Math.min(...positions.map(p => p[1])),
      maxY: Math.max(...positions.map(p => p[1])),
      minZ: Math.min(...positions.map(p => p[2])),
      maxZ: Math.max(...positions.map(p => p[2]))
    };

    const size = Math.max(
      bounds.maxX - bounds.minX,
      bounds.maxY - bounds.minY,
      bounds.maxZ - bounds.minZ
    );

    const distance = Math.max(size * 1.5, 15);
    return [distance, distance, distance] as [number, number, number];
  }, [localLayout.modules]);

  return (
    <div className="relative w-full h-full bg-gray-900">
      <Canvas
        camera={{ 
          position: optimalCameraPosition, 
          fov: 60,
          near: 0.1,
          far: 1000
        }}
        shadows
      >
        {/* Lighting */}
        <ambientLight intensity={0.4} />
        <directionalLight
          position={[10, 10, 5]}
          intensity={1}
          castShadow
          shadow-mapSize-width={2048}
          shadow-mapSize-height={2048}
        />
        <pointLight position={[-10, -10, -5]} intensity={0.5} />

        {/* Envelope visualization */}
        <EnvelopeVisualization envelope={envelope} opacity={0.1} />

        {/* Grid visualization */}
        <GridVisualization 
          size={50} 
          divisions={Math.floor(50 / gridSize)} 
          visible={showGrid} 
        />

        {/* Module visualizations */}
        {localLayout.modules.map((module) => (
          <InteractiveModule
            key={module.module_id}
            module={module}
            isSelected={selectedModuleId === module.module_id}
            isHighlighted={highlightedModules.includes(module.module_id)}
            hasConstraintViolation={moduleViolations.has(module.module_id)}
            onSelect={() => handleModuleSelect(module.module_id)}
            onMove={(newPosition) => handleModuleMove(module.module_id, newPosition)}
            onRotate={(newRotation) => handleModuleRotate(module.module_id, newRotation)}
            editable={viewMode === 'edit'}
            snapToGrid={snapToGrid}
            gridSize={gridSize}
            allModules={localLayout.modules}
            envelope={envelope}
          />
        ))}

        {/* Connection lines */}
        <ConnectionLines modules={localLayout.modules} />

        {/* Heatmap visualization */}
        <HeatmapVisualization
          data={heatmapData}
          type="movement"
          visible={showHeatmap}
          opacity={0.6}
        />

        {/* Metric overlay visualization */}
        <MetricOverlayVisualization
          modules={localLayout.modules}
          overlayType={activeOverlay === 'movement' ? 'none' : activeOverlay}
          visible={activeOverlay !== 'none' && activeOverlay !== 'movement'}
        />

        {/* Congestion visualization */}
        <CongestionVisualization
          congestionPoints={congestionPoints}
          visible={showCongestion}
        />

        {/* Camera controls */}
        <OrbitControls
          enablePan={true}
          enableZoom={true}
          enableRotate={true}
          maxDistance={200}
          minDistance={1}
        />
        
        {/* Axes helper */}
        <axesHelper args={[5]} />
      </Canvas>

      {/* Metrics overlay */}
      {showMetrics && <MetricsOverlay layout={localLayout} />}

      {/* Visualization controls */}
      <VisualizationControls
        activeOverlay={activeOverlay}
        onOverlayChange={setActiveOverlay}
        showHeatmap={showHeatmap}
        onHeatmapToggle={setShowHeatmap}
        showCongestion={showCongestion}
        onCongestionToggle={setShowCongestion}
      />

      {/* Module info panel */}
      {selectedModuleId && (
        <div className="absolute bottom-4 left-4 bg-black bg-opacity-75 text-white p-4 rounded-lg max-w-sm">
          <h4 className="font-semibold mb-2">Module Details</h4>
          {(() => {
            const selectedModule = localLayout.modules.find(m => m.module_id === selectedModuleId);
            if (!selectedModule) return null;
            
            const validationResult = validateModulePlacement(selectedModule, localLayout.modules, envelope);
            const dimensions = getModuleDimensions(selectedModule.type);
            
            return (
              <div className="text-sm space-y-2">
                <div><strong>ID:</strong> {selectedModule.module_id}</div>
                <div><strong>Type:</strong> {MODULE_NAMES[selectedModule.type]}</div>
                <div><strong>Position:</strong> [{selectedModule.position.map(p => p.toFixed(1)).join(', ')}]</div>
                <div><strong>Rotation:</strong> {selectedModule.rotation_deg.toFixed(1)}°</div>
                <div><strong>Dimensions:</strong> {dimensions.map(d => d.toFixed(1)).join(' × ')}m</div>
                <div><strong>Connections:</strong> {selectedModule.connections.length}</div>
                
                {/* Constraint status */}
                <div className="border-t border-gray-600 pt-2">
                  <div className="flex items-center space-x-2">
                    <strong>Status:</strong>
                    <span className={validationResult.isValid ? 'text-green-400' : 'text-red-400'}>
                      {validationResult.isValid ? '✓ Valid' : '✗ Invalid'}
                    </span>
                  </div>
                  
                  {validationResult.violations.length > 0 && (
                    <div className="mt-2">
                      <div className="text-xs text-gray-300 mb-1">Issues:</div>
                      {validationResult.violations.map((violation, index) => (
                        <div 
                          key={index} 
                          className={`text-xs ${violation.severity === 'error' ? 'text-red-400' : 'text-yellow-400'}`}
                        >
                          • {violation.message}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                
                {/* Edit instructions */}
                {viewMode === 'edit' && (
                  <div className="border-t border-gray-600 pt-2 text-xs text-gray-300">
                    <div>• Drag to move module</div>
                    <div>• Use rotation buttons to rotate</div>
                    <div>• Red outline indicates violations</div>
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      )}

      {/* View mode controls */}
      <div className="absolute top-4 left-4 bg-black bg-opacity-75 text-white p-3 rounded-lg">
        <div className="space-y-2">
          <div className="flex space-x-2">
            <button
              onClick={() => setSelectedModuleId(null)}
              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm"
            >
              Reset View
            </button>
            <button
              onClick={() => setSelectedModuleId(null)}
              className="px-3 py-1 bg-gray-600 hover:bg-gray-700 rounded text-sm"
            >
              Clear Selection
            </button>
          </div>
          
          {viewMode === 'edit' && (
            <div className="space-y-2 border-t border-gray-600 pt-2">
              <div className="text-xs text-gray-300">Edit Controls</div>
              
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="snapToGrid"
                  checked={snapToGrid}
                  onChange={(e) => {
                    // This would need to be passed as a prop or managed by parent
                    console.log('Snap to grid:', e.target.checked);
                  }}
                  className="rounded"
                />
                <label htmlFor="snapToGrid" className="text-sm">Snap to Grid</label>
              </div>
              
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="showGrid"
                  checked={showGrid}
                  onChange={(e) => setShowGrid(e.target.checked)}
                  className="rounded"
                />
                <label htmlFor="showGrid" className="text-sm">Show Grid</label>
              </div>
              
              <div className="flex items-center space-x-2">
                <label className="text-sm">Grid Size:</label>
                <select 
                  value={gridSize} 
                  onChange={(e) => {
                    // This would need to be passed as a prop or managed by parent
                    console.log('Grid size:', e.target.value);
                  }}
                  className="bg-gray-700 text-white text-sm rounded px-1"
                >
                  <option value={0.25}>0.25m</option>
                  <option value={0.5}>0.5m</option>
                  <option value={1.0}>1.0m</option>
                </select>
              </div>
            </div>
          )}
          
          {/* Constraint violations summary */}
          {moduleViolations.size > 0 && (
            <div className="border-t border-gray-600 pt-2">
              <div className="text-xs text-red-400">
                {moduleViolations.size} constraint violation{moduleViolations.size > 1 ? 's' : ''}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LayoutVisualization;