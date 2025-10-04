import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MetricsDashboard } from '../components/MetricsDashboard';
import { LayoutSpec, EnvelopeType, CoordinateFrame, ModuleType } from '../types';

describe('MetricsDashboard', () => {
  const mockLayouts: LayoutSpec[] = [
    {
      layoutId: 'layout-1',
      envelopeId: 'envelope-1',
      modules: [
        {
          module_id: 'sleep_001',
          type: ModuleType.SLEEP_QUARTER,
          position: [0, 0, 0],
          rotation_deg: 0,
          connections: [],
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
      explainability: 'Test layout 1',
    },
    {
      layoutId: 'layout-2',
      envelopeId: 'envelope-1',
      modules: [
        {
          module_id: 'sleep_002',
          type: ModuleType.SLEEP_QUARTER,
          position: [3, 0, 0],
          rotation_deg: 0,
          connections: [],
        },
      ],
      kpis: {
        meanTransitTime: 60.2,
        egressTime: 180.0,
        massTotal: 18000.0,
        powerBudget: 3000.0,
        thermalMargin: 0.25,
        lssMargin: 0.30,
        stowageUtilization: 0.75,
        connectivityScore: 0.85,
        safetyScore: 0.90,
        efficiencyScore: 0.70,
        volumeUtilization: 0.72,
      },
      explainability: 'Test layout 2',
    },
  ];

  it('renders without crashing', () => {
    render(
      <MetricsDashboard
        layouts={mockLayouts}
        selectedLayout={mockLayouts[0]}
      />
    );

    expect(screen.getByText('Performance Dashboard')).toBeInTheDocument();
  });

  it('displays overall score for selected layout', () => {
    render(
      <MetricsDashboard
        layouts={mockLayouts}
        selectedLayout={mockLayouts[0]}
      />
    );

    expect(screen.getByText('Overall Score')).toBeInTheDocument();
    // The overall score should be calculated from safety, efficiency, and connectivity scores
    // Look for the large overall score specifically
    const overallScoreElement = screen.getByText('Overall Score').parentElement;
    expect(overallScoreElement).toHaveTextContent(/\d+%/);
  });

  it('shows metric cards in overview mode', () => {
    render(
      <MetricsDashboard
        layouts={mockLayouts}
        selectedLayout={mockLayouts[0]}
      />
    );

    expect(screen.getByText('Mean Transit Time')).toBeInTheDocument();
    expect(screen.getByText('Emergency Egress Time')).toBeInTheDocument();
    expect(screen.getByText('Total Mass')).toBeInTheDocument();
    expect(screen.getByText('Power Budget')).toBeInTheDocument();
    expect(screen.getByText('Thermal Margin')).toBeInTheDocument();
    expect(screen.getByText('Life Support Margin')).toBeInTheDocument();
    expect(screen.getByText('Stowage Utilization')).toBeInTheDocument();
  });

  it('displays formatted metric values', () => {
    render(
      <MetricsDashboard
        layouts={mockLayouts}
        selectedLayout={mockLayouts[0]}
      />
    );

    // Check for formatted values
    expect(screen.getByText('45.5s')).toBeInTheDocument(); // Transit time
    expect(screen.getByText('120.0s')).toBeInTheDocument(); // Egress time
    expect(screen.getByText('15.0t')).toBeInTheDocument(); // Mass in tonnes
    expect(screen.getByText('2.5kW')).toBeInTheDocument(); // Power in kW
  });

  it('switches to comparison mode when compare button is clicked', () => {
    render(
      <MetricsDashboard
        layouts={mockLayouts}
        selectedLayout={mockLayouts[0]}
      />
    );

    const compareButton = screen.getByText('Compare');
    fireEvent.click(compareButton);

    expect(screen.getByText('Compare by Metric:')).toBeInTheDocument();
  });

  it('shows comparison view with multiple layouts', () => {
    render(
      <MetricsDashboard
        layouts={mockLayouts}
        selectedLayout={mockLayouts[0]}
      />
    );

    // Switch to comparison mode
    const compareButton = screen.getByText('Compare');
    fireEvent.click(compareButton);

    // Should show layout comparison
    expect(screen.getByText('Transit Time Comparison')).toBeInTheDocument();
    expect(screen.getByText('Layout 1')).toBeInTheDocument();
    expect(screen.getByText('Layout 2')).toBeInTheDocument();
  });

  it('renders in compact mode', () => {
    render(
      <MetricsDashboard
        layouts={mockLayouts}
        selectedLayout={mockLayouts[0]}
        compactMode={true}
      />
    );

    expect(screen.getByText('Performance Metrics')).toBeInTheDocument();
    // In compact mode, should show fewer metrics
    expect(screen.getByText('Mean Transit Time')).toBeInTheDocument();
  });

  it('shows no layout selected message when no layout is provided', () => {
    render(
      <MetricsDashboard
        layouts={mockLayouts}
        selectedLayout={null}
      />
    );

    expect(screen.getByText('No layout selected')).toBeInTheDocument();
    expect(screen.getByText('Select a layout to view performance metrics')).toBeInTheDocument();
  });

  it('displays critical issues when present', () => {
    const layoutWithIssues: LayoutSpec = {
      ...mockLayouts[0],
      kpis: {
        ...mockLayouts[0].kpis,
        thermalMargin: 0.05, // Low thermal margin
        lssMargin: 0.15, // Low LSS margin
        egressTime: 350, // High egress time
      },
    };

    render(
      <MetricsDashboard
        layouts={[layoutWithIssues]}
        selectedLayout={layoutWithIssues}
      />
    );

    expect(screen.getByText('Critical Issues')).toBeInTheDocument();
    expect(screen.getByText(/Low thermal margin/)).toBeInTheDocument();
    expect(screen.getByText(/Low LSS margin/)).toBeInTheDocument();
    expect(screen.getByText(/Excessive egress time/)).toBeInTheDocument();
  });

  it('calls onLayoutSelect when layout is clicked in comparison mode', () => {
    const onLayoutSelect = vi.fn();
    
    render(
      <MetricsDashboard
        layouts={mockLayouts}
        selectedLayout={mockLayouts[0]}
        onLayoutSelect={onLayoutSelect}
      />
    );

    // Switch to comparison mode
    const compareButton = screen.getByText('Compare');
    fireEvent.click(compareButton);

    // Click on a layout in the comparison
    const layout2 = screen.getByText('Layout 2');
    fireEvent.click(layout2);

    expect(onLayoutSelect).toHaveBeenCalledWith(mockLayouts[1]);
  });

  it('changes comparison metric when dropdown is changed', () => {
    render(
      <MetricsDashboard
        layouts={mockLayouts}
        selectedLayout={mockLayouts[0]}
      />
    );

    // Switch to comparison mode
    const compareButton = screen.getByText('Compare');
    fireEvent.click(compareButton);

    // Change the metric
    const select = screen.getByDisplayValue('Transit Time');
    fireEvent.change(select, { target: { value: 'egressTime' } });

    expect(screen.getByText('Egress Time Comparison')).toBeInTheDocument();
  });
});