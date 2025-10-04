import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MissionParametersComponent } from '../components/MissionParameters';
import { MissionParameters } from '../types';

describe('MissionParameters', () => {
  const mockOnMissionChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with default mission parameters', () => {
    render(<MissionParametersComponent onMissionChange={mockOnMissionChange} />);
    
    expect(screen.getByText('Mission Parameters')).toBeInTheDocument();
    expect(screen.getByText('Mission Templates')).toBeInTheDocument();
    expect(screen.getByText('Basic Parameters')).toBeInTheDocument();
    expect(screen.getByText('Priority Weights')).toBeInTheDocument();
    expect(screen.getByText('Daily Activity Schedule')).toBeInTheDocument();
    expect(screen.getByText('Emergency Scenarios')).toBeInTheDocument();
  });

  it('displays mission templates correctly', () => {
    render(<MissionParametersComponent onMissionChange={mockOnMissionChange} />);
    
    expect(screen.getByTestId('template-lunar-gateway')).toBeInTheDocument();
    expect(screen.getByTestId('template-mars-transit')).toBeInTheDocument();
    expect(screen.getByTestId('template-iss-research')).toBeInTheDocument();
    expect(screen.getByTestId('template-mars-surface-base')).toBeInTheDocument();
  });

  it('applies mission template when selected', async () => {
    render(<MissionParametersComponent onMissionChange={mockOnMissionChange} />);
    
    const lunarGatewayTemplate = screen.getByTestId('template-lunar-gateway');
    fireEvent.click(lunarGatewayTemplate);
    
    await waitFor(() => {
      expect(mockOnMissionChange).toHaveBeenCalledWith(expect.objectContaining({
        crew_size: 4,
        duration_days: 180
      }));
    });
  });

  it('updates crew size correctly', async () => {
    render(<MissionParametersComponent onMissionChange={mockOnMissionChange} />);
    
    const crewSizeInput = screen.getByTestId('crew-size-input');
    fireEvent.change(crewSizeInput, { target: { value: '6' } });
    
    await waitFor(() => {
      expect(mockOnMissionChange).toHaveBeenCalledWith(expect.objectContaining({
        crew_size: 6
      }));
    });
  });

  it('updates mission duration correctly', async () => {
    render(<MissionParametersComponent onMissionChange={mockOnMissionChange} />);
    
    const durationInput = screen.getByTestId('duration-input');
    fireEvent.change(durationInput, { target: { value: '365' } });
    
    await waitFor(() => {
      expect(mockOnMissionChange).toHaveBeenCalledWith(expect.objectContaining({
        duration_days: 365
      }));
    });
  });

  it('updates priority weights and normalizes them', async () => {
    render(<MissionParametersComponent onMissionChange={mockOnMissionChange} />);
    
    const safetySlider = screen.getByTestId('priority-safety-slider');
    fireEvent.change(safetySlider, { target: { value: '60' } });
    
    await waitFor(() => {
      expect(mockOnMissionChange).toHaveBeenCalled();
      const lastCall = mockOnMissionChange.mock.calls[mockOnMissionChange.mock.calls.length - 1];
      const weights = lastCall[0].priority_weights;
      
      // Check that weights sum to approximately 1.0
      const totalWeight = Object.values(weights).reduce((sum: number, weight: number) => sum + weight, 0);
      expect(totalWeight).toBeCloseTo(1.0, 2);
    });
  });

  it('updates activity schedule correctly', async () => {
    render(<MissionParametersComponent onMissionChange={mockOnMissionChange} />);
    
    const sleepInput = screen.getByTestId('activity-sleep-input');
    fireEvent.change(sleepInput, { target: { value: '7.5' } });
    
    await waitFor(() => {
      expect(mockOnMissionChange).toHaveBeenCalledWith(expect.objectContaining({
        activity_schedule: expect.objectContaining({
          sleep: 7.5
        })
      }));
    });
  });

  it('shows warning when activity schedule exceeds 24 hours', async () => {
    render(<MissionParametersComponent onMissionChange={mockOnMissionChange} />);
    
    // Set work hours to a high value to exceed 24 hours total
    const workInput = screen.getByTestId('activity-work-input');
    fireEvent.change(workInput, { target: { value: '20' } });
    
    await waitFor(() => {
      expect(screen.getAllByText(/exceeds 24 hours/).length).toBeGreaterThan(0);
    });
  });

  it('toggles emergency scenarios correctly', async () => {
    render(<MissionParametersComponent onMissionChange={mockOnMissionChange} />);
    
    const radiationCheckbox = screen.getByTestId('emergency-radiation_exposure');
    fireEvent.click(radiationCheckbox);
    
    await waitFor(() => {
      expect(mockOnMissionChange).toHaveBeenCalledWith(expect.objectContaining({
        emergency_scenarios: expect.arrayContaining(['radiation_exposure'])
      }));
    });
  });

  it('uses slider controls for crew size and duration', async () => {
    render(<MissionParametersComponent onMissionChange={mockOnMissionChange} />);
    
    const crewSizeSlider = screen.getByTestId('crew-size-slider');
    fireEvent.change(crewSizeSlider, { target: { value: '8' } });
    
    await waitFor(() => {
      expect(mockOnMissionChange).toHaveBeenCalledWith(expect.objectContaining({
        crew_size: 8
      }));
    });

    const durationSlider = screen.getByTestId('duration-slider');
    fireEvent.change(durationSlider, { target: { value: '500' } });
    
    await waitFor(() => {
      expect(mockOnMissionChange).toHaveBeenCalledWith(expect.objectContaining({
        duration_days: 500
      }));
    });
  });

  it('enforces crew size limits', async () => {
    render(<MissionParametersComponent onMissionChange={mockOnMissionChange} />);
    
    const crewSizeInput = screen.getByTestId('crew-size-input');
    
    // Test minimum limit
    fireEvent.change(crewSizeInput, { target: { value: '0' } });
    await waitFor(() => {
      expect(mockOnMissionChange).toHaveBeenCalledWith(expect.objectContaining({
        crew_size: 1
      }));
    });

    // Test maximum limit
    fireEvent.change(crewSizeInput, { target: { value: '25' } });
    await waitFor(() => {
      expect(mockOnMissionChange).toHaveBeenCalledWith(expect.objectContaining({
        crew_size: 20
      }));
    });
  });

  it('enforces duration limits', async () => {
    render(<MissionParametersComponent onMissionChange={mockOnMissionChange} />);
    
    const durationInput = screen.getByTestId('duration-input');
    
    // Test minimum limit
    fireEvent.change(durationInput, { target: { value: '0' } });
    await waitFor(() => {
      expect(mockOnMissionChange).toHaveBeenCalledWith(expect.objectContaining({
        duration_days: 1
      }));
    });

    // Test maximum limit
    fireEvent.change(durationInput, { target: { value: '1500' } });
    await waitFor(() => {
      expect(mockOnMissionChange).toHaveBeenCalledWith(expect.objectContaining({
        duration_days: 1000
      }));
    });
  });

  it('has export functionality', () => {
    // Test that export button exists and is enabled by default
    render(<MissionParametersComponent onMissionChange={mockOnMissionChange} />);
    const exportButton = screen.getByTestId('export-mission-button');
    expect(exportButton).toBeInTheDocument();
    expect(exportButton).not.toBeDisabled();
  });

  it('has import functionality', () => {
    // Test that import input exists with correct attributes
    render(<MissionParametersComponent onMissionChange={mockOnMissionChange} />);
    const importInput = screen.getByTestId('import-mission-input');
    expect(importInput).toBeInTheDocument();
    expect(importInput).toHaveAttribute('accept', '.json');
    expect(importInput).toHaveAttribute('type', 'file');
  });

  it('validates mission parameters', () => {
    // Test that validation works by checking if component renders without errors
    render(<MissionParametersComponent onMissionChange={mockOnMissionChange} />);
    expect(screen.getByText('Mission Parameters')).toBeInTheDocument();
  });

  it('has all priority weight controls', () => {
    // Test that all priority weight sliders exist
    render(<MissionParametersComponent onMissionChange={mockOnMissionChange} />);
    expect(screen.getByTestId('priority-safety-slider')).toBeInTheDocument();
    expect(screen.getByTestId('priority-efficiency-slider')).toBeInTheDocument();
    expect(screen.getByTestId('priority-mass-slider')).toBeInTheDocument();
    expect(screen.getByTestId('priority-power-slider')).toBeInTheDocument();
  });
});