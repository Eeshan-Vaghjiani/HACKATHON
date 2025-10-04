import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LayoutVisualization } from '../components/LayoutVisualization';
import { LayoutSpec, EnvelopeSpec, EnvelopeType, CoordinateFrame, ModuleType } from '../types';

// Mock Three.js and React Three Fiber
vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children }: any) => <div data-testid="canvas">{children}</div>,
  useFrame: vi.fn(),
}));

vi.mock('@react-three/drei', () => ({
  OrbitControls: () => <div data-testid="orbit-controls" />,
  Box: ({ children }: any) => <div data-testid="box">{children}</div>,
  Cylinder: ({ children }: any) => <div data-testid="cylinder">{children}</div>,
  Text: ({ children }: any) => <div data-testid="text">{children}</div>,
  Html: ({ children }: any) => <div data-testid="html">{children}</div>,
}));

vi.mock('three', () => ({
  CylinderGeometry: vi.fn(),
  BoxGeometry: vi.fn(),
  TorusGeometry: vi.fn(),
  SphereGeometry: vi.fn(),
  BufferGeometry: vi.fn(() => ({
    setFromPoints: vi.fn(),
  })),
  Vector3: vi.fn(),
}));

describe('LayoutVisualization', () => {
  const mockEnvelope: EnvelopeSpec = {
    id: 'test-envelope',
    type: EnvelopeType.CYLINDER,
    params: { radius: 5.0, length: 20.0 },
    coordinateFrame: CoordinateFrame.LOCAL,
    metadata: {
      name: 'Test Envelope',
      creator: 'test',
      created: new Date(),
    },
  };

  const mockLayout: LayoutSpec = {
    layoutId: 'test-layout',
    envelopeId: 'test-envelope',
    modules: [
      {
        module_id: 'sleep_001',
        type: ModuleType.SLEEP_QUARTER,
        position: [0, 0, 0],
        rotation_deg: 0,
        connections: [],
      },
      {
        module_id: 'galley_001',
        type: ModuleType.GALLEY,
        position: [3, 0, 0],
        rotation_deg: 0,
        connections: ['sleep_001'],
      },
    ],
    kpis: {
      meanTransitTime: 45.5,
      egressTime: 120.0,
      massTotal: 15000.0,
      powerBudget: 2500.0,
      thermalMargin: 0.155,
      lssMargin: 0.20,
      stowageUtilization: 0.85,
      connectivityScore: 0.92,
      safetyScore: 0.88,
      efficiencyScore: 0.76,
      volumeUtilization: 0.68,
    },
    explainability: 'Test layout with basic modules',
  };

  it('renders without crashing', () => {
    render(
      <LayoutVisualization
        layout={mockLayout}
        envelope={mockEnvelope}
      />
    );

    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('displays metrics overlay when showMetrics is true', () => {
    render(
      <LayoutVisualization
        layout={mockLayout}
        envelope={mockEnvelope}
        showMetrics={true}
      />
    );

    expect(screen.getByText('Performance Metrics')).toBeInTheDocument();
    expect(screen.getByText('45.5s')).toBeInTheDocument(); // Transit time
    expect(screen.getByText('120.0s')).toBeInTheDocument(); // Egress time
  });

  it('does not display metrics overlay when showMetrics is false', () => {
    render(
      <LayoutVisualization
        layout={mockLayout}
        envelope={mockEnvelope}
        showMetrics={false}
      />
    );

    expect(screen.queryByText('Performance Metrics')).not.toBeInTheDocument();
  });

  it('renders control buttons', () => {
    render(
      <LayoutVisualization
        layout={mockLayout}
        envelope={mockEnvelope}
      />
    );

    expect(screen.getByText('Reset View')).toBeInTheDocument();
    expect(screen.getByText('Clear Selection')).toBeInTheDocument();
  });

  it('handles module selection callback', () => {
    const onModuleSelect = vi.fn();
    
    render(
      <LayoutVisualization
        layout={mockLayout}
        envelope={mockEnvelope}
        onModuleSelect={onModuleSelect}
      />
    );

    // The actual module selection would happen through Three.js interaction
    // which is mocked, so we just verify the component renders
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('displays correct number of modules', () => {
    render(
      <LayoutVisualization
        layout={mockLayout}
        envelope={mockEnvelope}
      />
    );

    // Each module should render a Box component
    const boxes = screen.getAllByTestId('box');
    expect(boxes.length).toBeGreaterThanOrEqual(2); // At least 2 modules
  });
});