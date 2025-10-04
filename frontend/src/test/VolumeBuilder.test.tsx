import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ParameterControls } from '../components/ParameterControls';
import { EnvelopeType, ValidationResult } from '../types';

// Mock Three.js components to avoid rendering issues in tests
vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children }: any) => <div data-testid="mock-canvas">{children}</div>,
}));

vi.mock('@react-three/drei', () => ({
  OrbitControls: () => <div data-testid="mock-orbit-controls" />,
  Grid: () => <div data-testid="mock-grid" />,
}));

describe('ParameterControls', () => {
  const mockOnParameterChange = vi.fn();
  const mockValidation: ValidationResult = {
    isValid: true,
    errors: [],
    warnings: []
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders cylinder parameters correctly', () => {
    render(
      <ParameterControls
        envelopeType={EnvelopeType.CYLINDER}
        params={{ radius: 3.0, length: 12.0 }}
        onParameterChange={mockOnParameterChange}
        validation={mockValidation}
      />
    );
    
    expect(screen.getByText('Parameters')).toBeInTheDocument();
    expect(screen.getByTestId('radius-input')).toBeInTheDocument();
    expect(screen.getByTestId('length-input')).toBeInTheDocument();
    expect(screen.getByTestId('radius-slider')).toBeInTheDocument();
    expect(screen.getByTestId('length-slider')).toBeInTheDocument();
  });

  it('renders box parameters correctly', () => {
    render(
      <ParameterControls
        envelopeType={EnvelopeType.BOX}
        params={{ width: 6.0, height: 6.0, depth: 12.0 }}
        onParameterChange={mockOnParameterChange}
        validation={mockValidation}
      />
    );
    
    expect(screen.getByTestId('width-input')).toBeInTheDocument();
    expect(screen.getByTestId('height-input')).toBeInTheDocument();
    expect(screen.getByTestId('depth-input')).toBeInTheDocument();
  });

  it('renders torus parameters correctly', () => {
    render(
      <ParameterControls
        envelopeType={EnvelopeType.TORUS}
        params={{ majorRadius: 5.0, minorRadius: 2.0 }}
        onParameterChange={mockOnParameterChange}
        validation={mockValidation}
      />
    );
    
    expect(screen.getByTestId('majorRadius-input')).toBeInTheDocument();
    expect(screen.getByTestId('minorRadius-input')).toBeInTheDocument();
  });

  it('calls onParameterChange when input values change', async () => {
    render(
      <ParameterControls
        envelopeType={EnvelopeType.CYLINDER}
        params={{ radius: 3.0, length: 12.0 }}
        onParameterChange={mockOnParameterChange}
        validation={mockValidation}
      />
    );
    
    const radiusInput = screen.getByTestId('radius-input');
    fireEvent.change(radiusInput, { target: { value: '4.0' } });
    
    expect(mockOnParameterChange).toHaveBeenCalledWith('radius', 4.0);
  });

  it('calls onParameterChange when slider values change', async () => {
    render(
      <ParameterControls
        envelopeType={EnvelopeType.CYLINDER}
        params={{ radius: 3.0, length: 12.0 }}
        onParameterChange={mockOnParameterChange}
        validation={mockValidation}
      />
    );
    
    const radiusSlider = screen.getByTestId('radius-slider');
    fireEvent.change(radiusSlider, { target: { value: '5.0' } });
    
    expect(mockOnParameterChange).toHaveBeenCalledWith('radius', 5.0);
  });

  it('displays validation errors correctly', () => {
    const validationWithErrors: ValidationResult = {
      isValid: false,
      errors: [{
        field: 'radius',
        message: 'Radius must be positive',
        code: 'INVALID_RANGE'
      }],
      warnings: []
    };

    render(
      <ParameterControls
        envelopeType={EnvelopeType.CYLINDER}
        params={{ radius: -1.0, length: 12.0 }}
        onParameterChange={mockOnParameterChange}
        validation={validationWithErrors}
      />
    );
    
    expect(screen.getByText('Radius must be positive')).toBeInTheDocument();
  });

  it('displays validation warnings correctly', () => {
    const validationWithWarnings: ValidationResult = {
      isValid: true,
      errors: [],
      warnings: [{
        field: 'radius',
        message: 'Radius is very large',
        code: 'ABOVE_RECOMMENDED'
      }]
    };

    render(
      <ParameterControls
        envelopeType={EnvelopeType.CYLINDER}
        params={{ radius: 15.0, length: 12.0 }}
        onParameterChange={mockOnParameterChange}
        validation={validationWithWarnings}
      />
    );
    
    expect(screen.getByText('Radius is very large')).toBeInTheDocument();
  });

  it('shows parameter constraints information', () => {
    render(
      <ParameterControls
        envelopeType={EnvelopeType.CYLINDER}
        params={{ radius: 3.0, length: 12.0 }}
        onParameterChange={mockOnParameterChange}
        validation={mockValidation}
      />
    );
    
    expect(screen.getByText(/Minimum volume: 10 m³/)).toBeInTheDocument();
    expect(screen.getByText(/Maximum aspect ratio: 20:1/)).toBeInTheDocument();
  });

  it('displays parameter ranges correctly', () => {
    render(
      <ParameterControls
        envelopeType={EnvelopeType.CYLINDER}
        params={{ radius: 3.0, length: 12.0 }}
        onParameterChange={mockOnParameterChange}
        validation={mockValidation}
      />
    );
    
    expect(screen.getByText('Range: 0.5 - 10 m')).toBeInTheDocument();
    expect(screen.getByText('Range: 1 - 50 m')).toBeInTheDocument();
  });

  it('handles invalid numeric input gracefully', () => {
    render(
      <ParameterControls
        envelopeType={EnvelopeType.CYLINDER}
        params={{ radius: 3.0, length: 12.0 }}
        onParameterChange={mockOnParameterChange}
        validation={mockValidation}
      />
    );
    
    const radiusInput = screen.getByTestId('radius-input');
    fireEvent.change(radiusInput, { target: { value: 'invalid' } });
    
    // Should not call onParameterChange with invalid input
    expect(mockOnParameterChange).not.toHaveBeenCalledWith('radius', NaN);
  });
});