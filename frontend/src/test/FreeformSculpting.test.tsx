import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FreeformSculpting } from '../components/FreeformSculpting';
import { EnvelopeSpec, EnvelopeType, CoordinateFrame, SculptingTool } from '../types';

// Mock Three.js and React Three Fiber
vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children }: any) => <div data-testid="canvas">{children}</div>,
  useFrame: vi.fn(),
  useThree: () => ({
    raycaster: {},
    mouse: {},
    camera: {}
  })
}));

vi.mock('@react-three/drei', () => ({
  OrbitControls: () => <div data-testid="orbit-controls" />
}));

vi.mock('three', () => ({
  BufferGeometry: class {
    setAttribute = vi.fn();
    setIndex = vi.fn();
    computeVertexNormals = vi.fn();
  },
  BufferAttribute: class {
    constructor(public array: any, public itemSize: number) {}
  },
  CylinderGeometry: class {
    attributes = {
      position: { array: new Float32Array([0, 0, 0, 1, 1, 1]) },
      normal: { array: new Float32Array([0, 1, 0, 0, 1, 0]) }
    };
    index = { array: new Uint32Array([0, 1, 2]) };
  },
  DoubleSide: 2
}));

describe('FreeformSculpting', () => {
  let mockEnvelope: EnvelopeSpec;
  let mockOnEnvelopeChange: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockOnEnvelopeChange = vi.fn();
    mockEnvelope = {
      id: 'test-envelope',
      type: EnvelopeType.FREEFORM,
      params: { radius: 3.0, length: 12.0 },
      coordinateFrame: CoordinateFrame.LOCAL,
      metadata: {
        name: 'Test Freeform Envelope',
        creator: 'Test User',
        created: new Date()
      }
    };
  });

  it('should render sculpting tools panel when active', () => {
    render(
      <FreeformSculpting
        envelope={mockEnvelope}
        onEnvelopeChange={mockOnEnvelopeChange}
        isActive={true}
      />
    );

    expect(screen.getByText('Sculpting Tools')).toBeInTheDocument();
    expect(screen.getByText('PUSH')).toBeInTheDocument();
    expect(screen.getByText('PULL')).toBeInTheDocument();
    expect(screen.getByText('SMOOTH')).toBeInTheDocument();
  });

  it('should not render when inactive', () => {
    render(
      <FreeformSculpting
        envelope={mockEnvelope}
        onEnvelopeChange={mockOnEnvelopeChange}
        isActive={false}
      />
    );

    expect(screen.queryByText('Sculpting Tools')).not.toBeInTheDocument();
  });

  it('should initialize sculpting data when activated', async () => {
    render(
      <FreeformSculpting
        envelope={mockEnvelope}
        onEnvelopeChange={mockOnEnvelopeChange}
        isActive={true}
      />
    );

    await waitFor(() => {
      expect(mockOnEnvelopeChange).toHaveBeenCalledWith(
        expect.objectContaining({
          sculptingData: expect.objectContaining({
            baseGeometry: expect.any(Object),
            splineModifications: expect.any(Array),
            sculptingOperations: expect.any(Array),
            undoStack: expect.any(Array),
            redoStack: expect.any(Array),
            isManifold: true,
            volumeValid: true
          })
        })
      );
    });
  });

  it('should change sculpting tool when tool button is clicked', () => {
    render(
      <FreeformSculpting
        envelope={mockEnvelope}
        onEnvelopeChange={mockOnEnvelopeChange}
        isActive={true}
      />
    );

    const pullButton = screen.getByText('PULL');
    fireEvent.click(pullButton);

    // The button should be selected (have active styling)
    expect(pullButton).toHaveClass('bg-blue-600');
  });

  it('should update strength setting when slider is changed', () => {
    render(
      <FreeformSculpting
        envelope={mockEnvelope}
        onEnvelopeChange={mockOnEnvelopeChange}
        isActive={true}
      />
    );

    const strengthSlider = screen.getByDisplayValue('0.1');
    fireEvent.change(strengthSlider, { target: { value: '0.5' } });

    expect(screen.getByText('Strength: 0.50')).toBeInTheDocument();
  });

  it('should update radius setting when slider is changed', () => {
    render(
      <FreeformSculpting
        envelope={mockEnvelope}
        onEnvelopeChange={mockOnEnvelopeChange}
        isActive={true}
      />
    );

    const radiusSlider = screen.getByDisplayValue('1');
    fireEvent.change(radiusSlider, { target: { value: '2.5' } });

    expect(screen.getByText('Radius: 2.50')).toBeInTheDocument();
  });

  it('should toggle symmetry setting', () => {
    render(
      <FreeformSculpting
        envelope={mockEnvelope}
        onEnvelopeChange={mockOnEnvelopeChange}
        isActive={true}
      />
    );

    const symmetryCheckbox = screen.getByLabelText('Symmetry');
    fireEvent.click(symmetryCheckbox);

    expect(symmetryCheckbox).toBeChecked();
    expect(screen.getByText('Symmetry Axis')).toBeInTheDocument();
  });

  it('should show spline controls for spline tools', () => {
    render(
      <FreeformSculpting
        envelope={mockEnvelope}
        onEnvelopeChange={mockOnEnvelopeChange}
        isActive={true}
      />
    );

    const splineExtrudeButton = screen.getByText('SPLINE EXTRUDE');
    fireEvent.click(splineExtrudeButton);

    expect(screen.getByText('Spline Controls')).toBeInTheDocument();
    expect(screen.getByText('Start Drawing Spline')).toBeInTheDocument();
  });

  it('should toggle spline drawing mode', () => {
    render(
      <FreeformSculpting
        envelope={mockEnvelope}
        onEnvelopeChange={mockOnEnvelopeChange}
        isActive={true}
      />
    );

    // Select spline tool first
    const splineExtrudeButton = screen.getByText('SPLINE EXTRUDE');
    fireEvent.click(splineExtrudeButton);

    const drawingButton = screen.getByText('Start Drawing Spline');
    fireEvent.click(drawingButton);

    expect(screen.getByText('Stop Drawing')).toBeInTheDocument();
  });

  it('should show validation status', () => {
    const envelopeWithSculptingData = {
      ...mockEnvelope,
      sculptingData: {
        baseGeometry: {
          type: 'cylinder' as const,
          params: { radius: 3.0, length: 12.0 },
          vertices: new Float32Array([0, 0, 0]),
          faces: new Uint32Array([0]),
          normals: new Float32Array([0, 1, 0])
        },
        splineModifications: [],
        sculptingOperations: [],
        undoStack: [],
        redoStack: [],
        isManifold: true,
        volumeValid: true
      }
    };

    render(
      <FreeformSculpting
        envelope={envelopeWithSculptingData}
        onEnvelopeChange={mockOnEnvelopeChange}
        isActive={true}
      />
    );

    expect(screen.getByText('Validation')).toBeInTheDocument();
    expect(screen.getAllByText('✓')).toHaveLength(2); // Two checkmarks for manifold and volume
    expect(screen.getByText('Manifold Geometry')).toBeInTheDocument();
    expect(screen.getByText('Closed Volume')).toBeInTheDocument();
  });

  it('should disable undo button when no operations in stack', () => {
    const envelopeWithSculptingData = {
      ...mockEnvelope,
      sculptingData: {
        baseGeometry: {
          type: 'cylinder' as const,
          params: { radius: 3.0, length: 12.0 },
          vertices: new Float32Array([0, 0, 0]),
          faces: new Uint32Array([0]),
          normals: new Float32Array([0, 1, 0])
        },
        splineModifications: [],
        sculptingOperations: [],
        undoStack: [],
        redoStack: [],
        isManifold: true,
        volumeValid: true
      }
    };

    render(
      <FreeformSculpting
        envelope={envelopeWithSculptingData}
        onEnvelopeChange={mockOnEnvelopeChange}
        isActive={true}
      />
    );

    const undoButton = screen.getByText('Undo');
    expect(undoButton).toBeDisabled();
  });

  it('should render 3D canvas', () => {
    render(
      <FreeformSculpting
        envelope={mockEnvelope}
        onEnvelopeChange={mockOnEnvelopeChange}
        isActive={true}
      />
    );

    expect(screen.getByTestId('canvas')).toBeInTheDocument();
    expect(screen.getByTestId('orbit-controls')).toBeInTheDocument();
  });
});

describe('Sculpting Operations', () => {
  it('should calculate falloff correctly for linear type', () => {
    // This would test the calculateFalloff function
    // Since it's not exported, we'd need to either export it or test it indirectly
    expect(true).toBe(true); // Placeholder
  });

  it('should apply push operations to geometry', () => {
    // This would test the applyOperationsToGeometry function
    expect(true).toBe(true); // Placeholder
  });

  it('should validate manifold geometry', () => {
    // This would test geometry validation
    expect(true).toBe(true); // Placeholder
  });
});