/**
 * Comprehensive tests for services and utilities
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { LayoutService } from '../services/layoutService';
import { 
  LayoutAnalyzer, 
  PerformanceAnalyzer, 
  ModuleUtilities, 
  FormatUtilities 
} from '../services/utilityService';
import { 
  LayoutSpec, 
  EnvelopeSpec, 
  MissionParameters, 
  ModulePlacement, 
  PerformanceMetrics,
  ModuleType,
  EnvelopeType,
  CoordinateFrame
} from '../types';

// ============================================================================
// TEST DATA
// ============================================================================

const mockEnvelope: EnvelopeSpec = {
  id: 'test-envelope-1',
  type: EnvelopeType.CYLINDER,
  params: {
    radius: 5.0,
    length: 20.0
  },
  coordinateFrame: CoordinateFrame.LOCAL,
  metadata: {
    name: 'Test Cylinder Habitat',
    creator: 'Test User',
    created: new Date('2024-01-01')
  },
  volume: Math.PI * 5 * 5 * 20 // ~1571 m³
};

const mockMission: MissionParameters = {
  crew_size: 4,
  duration_days: 180,
  priority_weights: {
    safety: 0.4,
    efficiency: 0.3,
    mass: 0.2,
    power: 0.1
  },
  activity_schedule: {
    sleep: 8,
    work: 8,
    exercise: 2,
    meals: 3,
    personal: 3
  },
  emergency_scenarios: ['fire', 'depressurization', 'medical']
};

const mockModules: ModulePlacement[] = [
  {
    module_id: 'sleep_001',
    type: ModuleType.SLEEP_QUARTER,
    position: [2, 0, -5],
    rotation_deg: 0,
    connections: ['galley_001']
  },
  {
    module_id: 'sleep_002',
    type: ModuleType.SLEEP_QUARTER,
    position: [-2, 0, -5],
    rotation_deg: 0,
    connections: ['galley_001']
  },
  {
    module_id: 'galley_001',
    type: ModuleType.GALLEY,
    position: [0, 0, 0],
    rotation_deg: 0,
    connections: ['sleep_001', 'sleep_002', 'lab_001', 'airlock_001']
  },
  {
    module_id: 'lab_001',
    type: ModuleType.LABORATORY,
    position: [0, 0, 5],
    rotation_deg: 0,
    connections: ['galley_001', 'airlock_001']
  },
  {
    module_id: 'airlock_001',
    type: ModuleType.AIRLOCK,
    position: [3, 0, 8],
    rotation_deg: 90,
    connections: ['galley_001', 'lab_001']
  }
];

const mockMetrics: PerformanceMetrics = {
  meanTransitTime: 45.2,
  egressTime: 120.5,
  massTotal: 15000,
  powerBudget: 25000,
  thermalMargin: 0.25,
  lssMargin: 0.35,
  stowageUtilization: 0.82,
  connectivityScore: 0.85,
  safetyScore: 0.78,
  efficiencyScore: 0.72,
  volumeUtilization: 0.45
};

const mockLayout: LayoutSpec = {
  layoutId: 'test-layout-1',
  envelopeId: mockEnvelope.id,
  modules: mockModules,
  kpis: mockMetrics,
  explainability: 'Test layout with balanced module placement for crew efficiency.',
  metadata: {
    name: 'Test Layout',
    created: new Date('2024-01-01'),
    generationParams: {
      algorithm: 'test',
      crew_size: 4
    }
  }
};

// ============================================================================
// LAYOUT ANALYZER TESTS
// ============================================================================

describe('LayoutAnalyzer', () => {
  it('should calculate layout density correctly', () => {
    const density = LayoutAnalyzer.calculateLayoutDensity(mockLayout, mockEnvelope);
    expect(density).toBeCloseTo(mockLayout.modules.length / mockEnvelope.volume!, 3);
  });

  it('should calculate layout center', () => {
    const center = LayoutAnalyzer.calculateLayoutCenter(mockLayout);
    expect(center).toBeDefined();
    expect(typeof center.x).toBe('number');
    expect(typeof center.y).toBe('number');
    expect(typeof center.z).toBe('number');
  });

  it('should calculate layout spread', () => {
    const spread = LayoutAnalyzer.calculateLayoutSpread(mockLayout);
    expect(spread).toBeGreaterThan(0);
    expect(typeof spread).toBe('number');
  });

  it('should find most isolated module', () => {
    const isolated = LayoutAnalyzer.findMostIsolatedModule(mockLayout);
    expect(isolated).toBeDefined();
    expect(isolated?.module_id).toBeDefined();
  });

  it('should calculate connectivity metrics', () => {
    const metrics = LayoutAnalyzer.calculateConnectivityMetrics(mockLayout);
    expect(metrics.averageConnections).toBeGreaterThan(0);
    expect(metrics.maxConnections).toBeGreaterThanOrEqual(metrics.minConnections);
    expect(metrics.connectivityRatio).toBeGreaterThanOrEqual(0);
    expect(metrics.connectivityRatio).toBeLessThanOrEqual(1);
  });

  it('should handle empty layout', () => {
    const emptyLayout: LayoutSpec = {
      ...mockLayout,
      modules: []
    };
    
    const metrics = LayoutAnalyzer.calculateConnectivityMetrics(emptyLayout);
    expect(metrics.averageConnections).toBe(0);
    expect(metrics.maxConnections).toBe(0);
    expect(metrics.minConnections).toBe(0);
    expect(metrics.isolatedModules).toBe(0);
    expect(metrics.connectivityRatio).toBe(0);
  });
});

// ============================================================================
// PERFORMANCE ANALYZER TESTS
// ============================================================================

describe('PerformanceAnalyzer', () => {
  it('should identify critical issues', () => {
    const criticalMetrics: PerformanceMetrics = {
      ...mockMetrics,
      thermalMargin: 0.02, // Critical
      lssMargin: 0.05,     // Critical
      egressTime: 350,     // Critical
      stowageUtilization: 1.3, // Critical
      safetyScore: 0.2     // Critical
    };

    const issues = PerformanceAnalyzer.identifyCriticalIssues(criticalMetrics);
    expect(issues.length).toBeGreaterThan(0);
    expect(issues.some(issue => issue.includes('thermal'))).toBe(true);
    expect(issues.some(issue => issue.includes('LSS'))).toBe(true);
    expect(issues.some(issue => issue.includes('egress'))).toBe(true);
    expect(issues.some(issue => issue.includes('overcrowding'))).toBe(true);
    expect(issues.some(issue => issue.includes('safety'))).toBe(true);
  });

  it('should calculate normalized score', () => {
    const score = PerformanceAnalyzer.calculateNormalizedScore(mockMetrics);
    expect(score).toBeGreaterThanOrEqual(0);
    expect(score).toBeLessThanOrEqual(1);
  });

  it('should compare metrics correctly', () => {
    const improvedMetrics: PerformanceMetrics = {
      ...mockMetrics,
      meanTransitTime: 35.0, // Improved (lower is better)
      thermalMargin: 0.35,   // Improved (higher is better)
      safetyScore: 0.85      // Improved (higher is better)
    };

    const comparison = PerformanceAnalyzer.compareMetrics(mockMetrics, improvedMetrics);
    
    expect(comparison.meanTransitTime.improvement).toBe(true);
    expect(comparison.thermalMargin.improvement).toBe(true);
    expect(comparison.safetyScore.improvement).toBe(true);
  });
});

// ============================================================================
// MODULE UTILITIES TESTS
// ============================================================================

describe('ModuleUtilities', () => {
  it('should get correct module dimensions', () => {
    const sleepDimensions = ModuleUtilities.getModuleDimensions('sleep_quarter');
    expect(sleepDimensions.x).toBe(2.0);
    expect(sleepDimensions.y).toBe(2.0);
    expect(sleepDimensions.z).toBe(2.5);

    const galleryDimensions = ModuleUtilities.getModuleDimensions('galley');
    expect(galleryDimensions.x).toBe(3.0);
    expect(galleryDimensions.y).toBe(2.5);
    expect(galleryDimensions.z).toBe(2.2);
  });

  it('should calculate module bounding box', () => {
    const module = mockModules[0]; // sleep_001
    const bbox = ModuleUtilities.getModuleBoundingBox(module);
    
    expect(bbox.min).toBeDefined();
    expect(bbox.max).toBeDefined();
    expect(bbox.min.x).toBeLessThan(bbox.max.x);
    expect(bbox.min.y).toBeLessThan(bbox.max.y);
    expect(bbox.min.z).toBeLessThan(bbox.max.z);
  });

  it('should check module adjacency', () => {
    const module1 = mockModules[0]; // sleep_001 at [2, 0, -5]
    const module2 = mockModules[2]; // galley_001 at [0, 0, 0]
    
    const adjacent = ModuleUtilities.areModulesAdjacent(module1, module2, 10.0);
    expect(adjacent).toBe(true);
    
    const notAdjacent = ModuleUtilities.areModulesAdjacent(module1, module2, 2.0);
    expect(notAdjacent).toBe(false);
  });

  it('should find nearby modules', () => {
    const targetModule = mockModules[2]; // galley_001 (central)
    const nearby = ModuleUtilities.findNearbyModules(targetModule, mockModules, 10.0);
    
    expect(nearby.length).toBeGreaterThan(0);
    expect(nearby.every(m => m.module_id !== targetModule.module_id)).toBe(true);
  });

  it('should calculate total module volume', () => {
    const totalVolume = ModuleUtilities.calculateTotalModuleVolume(mockModules);
    expect(totalVolume).toBeGreaterThan(0);
    
    // Verify calculation
    let expectedVolume = 0;
    mockModules.forEach(module => {
      const dims = ModuleUtilities.getModuleDimensions(module.type);
      expectedVolume += dims.x * dims.y * dims.z;
    });
    
    expect(totalVolume).toBeCloseTo(expectedVolume, 3);
  });
});

// ============================================================================
// FORMAT UTILITIES TESTS
// ============================================================================

describe('FormatUtilities', () => {
  it('should format metrics with appropriate units', () => {
    expect(FormatUtilities.formatMetric(1500, 'kg')).toBe('1.5t');
    expect(FormatUtilities.formatMetric(500, 'kg')).toBe('500.0kg');
    expect(FormatUtilities.formatMetric(2500, 'W')).toBe('2.5kW');
    expect(FormatUtilities.formatMetric(800, 'W')).toBe('800.0W');
    expect(FormatUtilities.formatMetric(0.75, '%')).toBe('75.0%');
  });

  it('should format duration correctly', () => {
    expect(FormatUtilities.formatDuration(45)).toBe('45s');
    expect(FormatUtilities.formatDuration(90)).toBe('1m 30s');
    expect(FormatUtilities.formatDuration(120)).toBe('2m');
    expect(FormatUtilities.formatDuration(3665)).toBe('1h 1m');
    expect(FormatUtilities.formatDuration(7200)).toBe('2h');
  });

  it('should format position vectors', () => {
    const position: [number, number, number] = [1.234, -2.567, 3.891];
    expect(FormatUtilities.formatPosition(position)).toBe('[1.2, -2.6, 3.9]');
    expect(FormatUtilities.formatPosition(position, 2)).toBe('[1.23, -2.57, 3.89]');
  });

  it('should format percentage with color coding', () => {
    const thresholds = { good: 80, warning: 60 };
    
    const good = FormatUtilities.formatPercentageWithColor(0.85, thresholds);
    expect(good.color).toBe('green');
    expect(good.text).toBe('85.0%');
    
    const warning = FormatUtilities.formatPercentageWithColor(0.70, thresholds);
    expect(warning.color).toBe('yellow');
    
    const bad = FormatUtilities.formatPercentageWithColor(0.50, thresholds);
    expect(bad.color).toBe('red');
  });
});

// ============================================================================
// LAYOUT SERVICE TESTS
// ============================================================================

describe('LayoutService', () => {
  let layoutService: LayoutService;

  beforeEach(() => {
    layoutService = new LayoutService();
  });

  it('should initialize with empty cache', () => {
    const stats = layoutService.getCacheStats();
    expect(stats.size).toBe(0);
  });

  it('should clear cache', () => {
    layoutService.clearCache();
    const stats = layoutService.getCacheStats();
    expect(stats.size).toBe(0);
  });

  it('should compare layouts correctly', () => {
    const layouts = [mockLayout];
    const comparison = layoutService.compareLayouts(layouts);
    
    expect(comparison.bestPerforming).toBeDefined();
    expect(comparison.worstPerforming).toBeDefined();
    expect(comparison.averageMetrics).toBeDefined();
    expect(comparison.metricRanges).toBeDefined();
  });

  it('should handle empty layout comparison', () => {
    expect(() => layoutService.compareLayouts([])).toThrow('No layouts provided for comparison');
  });
});

// ============================================================================
// INTEGRATION TESTS
// ============================================================================

describe('Integration Tests', () => {
  it('should work with complete workflow', () => {
    // Analyze layout
    const density = LayoutAnalyzer.calculateLayoutDensity(mockLayout, mockEnvelope);
    const connectivity = LayoutAnalyzer.calculateConnectivityMetrics(mockLayout);
    
    // Analyze performance
    const score = PerformanceAnalyzer.calculateNormalizedScore(mockMetrics);
    const issues = PerformanceAnalyzer.identifyCriticalIssues(mockMetrics);
    
    // Calculate module metrics
    const totalVolume = ModuleUtilities.calculateTotalModuleVolume(mockModules);
    
    // Format results
    const formattedScore = FormatUtilities.formatMetric(score, '%');
    const formattedVolume = FormatUtilities.formatMetric(totalVolume, 'm³');
    
    expect(density).toBeGreaterThan(0);
    expect(connectivity.averageConnections).toBeGreaterThan(0);
    expect(score).toBeGreaterThan(0);
    expect(issues).toBeDefined();
    expect(totalVolume).toBeGreaterThan(0);
    expect(formattedScore).toContain('%');
    expect(formattedVolume).toContain('m³');
  });
});