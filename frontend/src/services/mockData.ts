import { EnvelopeSpec, LayoutSpec, MissionParameters, RoomSpec } from '../types';
import { v4 as uuidv4 } from 'uuid';

/**
 * Generate mock layout data for demonstration purposes when the API is not available
 */
export function generateMockLayouts(
  envelope?: EnvelopeSpec,
  missionParams?: MissionParameters,
  count: number = 5
): LayoutSpec[] {
  const mockLayouts: LayoutSpec[] = [];
  
  // Use provided envelope or create a default one
  const envelopeSpec = envelope || {
    id: uuidv4(),
    width: 6.0,
    depth: 12.0,
    height: 6.0,
    name: 'Default Envelope',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  // Generate the specified number of mock layouts
  for (let i = 0; i < count; i++) {
    mockLayouts.push(generateMockLayout(envelopeSpec, i));
  }

  return mockLayouts;
}

/**
 * Generate a single mock layout
 */
function generateMockLayout(envelope: EnvelopeSpec, index: number): LayoutSpec {
  const layoutId = uuidv4();
  
  // Create a set of rooms with different sizes and positions
  const rooms: RoomSpec[] = [
    // Living area
    {
      id: uuidv4(),
      name: 'Living Area',
      width: 4.0,
      depth: 4.0,
      height: 2.8,
      position: { x: 1.0, y: 0.0, z: 1.0 },
      rotation: { x: 0, y: 0, z: 0 },
      room_type: 'LIVING',
      layout_id: layoutId,
    },
    // Sleeping quarters
    {
      id: uuidv4(),
      name: 'Sleeping Quarters',
      width: 3.0,
      depth: 3.0,
      height: 2.5,
      position: { x: 1.5, y: 0.0, z: 6.0 },
      rotation: { x: 0, y: 0, z: 0 },
      room_type: 'SLEEPING',
      layout_id: layoutId,
    },
    // Work area
    {
      id: uuidv4(),
      name: 'Work Area',
      width: 3.0,
      depth: 3.0,
      height: 2.5,
      position: { x: -1.5, y: 0.0, z: 3.5 },
      rotation: { x: 0, y: 0, z: 0 },
      room_type: 'WORK',
      layout_id: layoutId,
    },
    // Hygiene
    {
      id: uuidv4(),
      name: 'Hygiene',
      width: 2.0,
      depth: 2.0,
      height: 2.3,
      position: { x: -2.0, y: 0.0, z: 8.0 },
      rotation: { x: 0, y: 0, z: 0 },
      room_type: 'HYGIENE',
      layout_id: layoutId,
    },
    // Exercise
    {
      id: uuidv4(),
      name: 'Exercise',
      width: 2.5,
      depth: 2.5,
      height: 2.5,
      position: { x: 2.0, y: 0.0, z: 9.5 },
      rotation: { x: 0, y: 0, z: 0 },
      room_type: 'EXERCISE',
      layout_id: layoutId,
    },
  ];

  // Slightly vary the positions for each layout to make them different
  rooms.forEach(room => {
    room.position.x += (Math.random() - 0.5) * (index + 1) * 0.3;
    room.position.z += (Math.random() - 0.5) * (index + 1) * 0.3;
    room.rotation.y = Math.random() * Math.PI * 0.25; // Random rotation up to 45 degrees
  });

  return {
    id: layoutId,
    name: `Mock Layout ${index + 1}`,
    envelope_id: envelope.id,
    rooms: rooms,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    metrics: {
      adjacency_score: 0.75 + Math.random() * 0.2,
      circulation_score: 0.7 + Math.random() * 0.25,
      privacy_score: 0.8 + Math.random() * 0.15,
      overall_score: 0.75 + Math.random() * 0.2,
    },
  };
}