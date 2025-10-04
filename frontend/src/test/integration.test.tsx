/**
 * Integration tests for frontend components and services
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { act } from 'react';
import axios from 'axios';

import { LayoutService } from '../services/layoutService';
import { exportService } from '../services/exportService';
import { 
  LayoutAnalyzer, 
  PerformanceAnalyzer, 
  ModuleUtilities 
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

// Mock axios
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      }
    })),
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() }
    }
  }
}));

const mockedAxios = vi.mocked(axios, true);

// Mock data
const mockEnvelope: EnvelopeSpec = {
  id: 'test-envelope-1',
  type: EnvelopeType.CYLINDER,
  params: {
    radius: 4.0,
    length: 16.0
  },
  coordinateFrame: CoordinateFrame.LOCAL,
  metadata: {
    name: 'Test Integration Habitat',
    creator: 'Integration Test',
    created: new Date('2024-01-01')
  },
  volume: Math.PI * 4 * 4 * 16
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
  emergency_scenarios: ['fire', 'depressurization']
};

const mockModules: ModulePlacement[] = [
  {
    module_id: 'sleep_001',
    type: ModuleType.SLEEP_QUARTER,
    position: [2, 0, -6],
    rotation_deg: 0,
    connections: ['galley_001']
  },
  {
    module_id: 'sleep_002',
    type: ModuleType.SLEEP_QUARTER,
    position: [-2, 0, -6],
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
    position: [0, 0, 6],
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
  layoutId: 'integration-test-layout',
  envelopeId: mockEnvelope.id,
  modules: mockModules,
  kpis: mockMetrics,
  explainability: 'Integration test layout with balanced module placement.',
  metadata: {
    name: 'Integration Test Layout',
    created: new Date('2024-01-01'),
    generationParams: {
      algorithm: 'test',
      crew_size: 4
    }
  }
};

// ============================================================================
// SERVICE INTEGRATION TESTS
// ============================================================================

describe('Service Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('LayoutService Integration', () => {
    it('should handle complete layout workflow', async () => {
      const layoutService = new LayoutService();
      
      // Mock API responses
      mockedAxios.post.mockResolvedValueOnce({
        data: { layouts: [mockLayout] }
      });
      
      mockedAxios.get.mockResolvedValueOnce({
        data: { layout: mockLayout }
      });
      
      // Test layout generation
      const generatedLayouts = await layoutService.generateLayouts(mockEnvelope, mockMission);
      expect(generatedLayouts).toHaveLength(1);
      expect(generatedLayouts[0].layoutId).toBe(mockLayout.layoutId);
      
      // Test layout retrieval
      const retrievedLayout = await layoutService.getLayout(mockLayout.layoutId);
      expect(retrievedLayout).toBeDefined();
      expect(retrievedLayout?.layoutId).toBe(mockLayout.layoutId);
      
      // Verify API calls
      expect(mockedAxios.post).toHaveBeenCalledWith('/api/layouts/generate', {
        envelope: mockEnvelope,
        mission: mockMission,
        count: 3
      });
      
      expect(mockedAxios.get).toHaveBeenCalledWith(`/api/layouts/${mockLayout.layoutId}`);
    });

    it('should handle layout comparison workflow', () => {
      const layoutService = new LayoutService();
      
      // Create multiple layouts for comparison
      const layout2: LayoutSpec = {
        ...mockLayout,
        layoutId: 'layout-2',
        kpis: {
          ...mockMetrics,
          meanTransitTime: 55.0,
          safetyScore: 0.85
        }
      };
      
      const layouts = [mockLayout, layout2];
      const comparison = layoutService.compareLayouts(layouts);
      
      expect(comparison.bestPerforming).toBeDefined();
      expect(comparison.worstPerforming).toBeDefined();
      expect(comparison.averageMetrics).toBeDefined();
      expect(comparison.metricRanges).toBeDefined();
      
      // Best performing should have better overall metrics
      expect(comparison.bestPerforming.layoutId).toBe(layout2.layoutId); // Higher safety score
      expect(comparison.worstPerforming.layoutId).toBe(mockLayout.layoutId);
    });

    it('should handle caching correctly', async () => {
      const layoutService = new LayoutService();
      
      // Mock API response
      mockedAxios.get.mockResolvedValueOnce({
        data: { layout: mockLayout }
      });
      
      // First call should hit API
      const layout1 = await layoutService.getLayout(mockLayout.layoutId);
      expect(mockedAxios.get).toHaveBeenCalledTimes(1);
      
      // Second call should use cache
      const layout2 = await layoutService.getLayout(mockLayout.layoutId);
      expect(mockedAxios.get).toHaveBeenCalledTimes(1); // Still only 1 call
      
      expect(layout1).toEqual(layout2);
      
      // Cache stats should reflect usage
      const stats = layoutService.getCacheStats();
      expect(stats.size).toBe(1);
      expect(stats.hits).toBe(1);
      expect(stats.misses).toBe(1);
    });
  });

  describe('Export Service Integration', () => {
    it('should handle complete export workflow', async () => {
      // Mock successful export
      mockedAxios.post.mockResolvedValueOnce({
        data: { 
          downloadUrl: 'http://example.com/export.gltf',
          filename: 'layout_export.gltf'
        }
      });
      
      const result = await exportService.exportLayout(
        mockLayout.layoutId, 
        'gltf',
        { includeTextures: true }
      );
      
      expect(result.success).toBe(true);
      expect(result.downloadUrl).toBeDefined();
      expect(result.filename).toBe('layout_export.gltf');
      
      expect(mockedAxios.post).toHaveBeenCalledWith('/api/export/layout', {
        layoutId: mockLayout.layoutId,
        format: 'gltf',
        options: { includeTextures: true }
      });
    });

    it('should handle batch export workflow', async () => {
      const layoutIds = ['layout-1', 'layout-2', 'layout-3'];
      
      mockedAxios.post.mockResolvedValueOnce({
        data: { 
          downloadUrl: 'http://example.com/batch_export.zip',
          filename: 'layouts_batch.zip'
        }
      });
      
      const result = await exportService.exportBatch(layoutIds, 'pdf');
      
      expect(result.success).toBe(true);
      expect(result.downloadUrl).toBeDefined();
      expect(result.filename).toBe('layouts_batch.zip');
    });

    it('should generate export preview correctly', async () => {
      mockedAxios.post.mockResolvedValueOnce({
        data: { 
          previewUrl: 'http://example.com/preview.png',
          estimatedSize: '2.5 MB',
          estimatedTime: '15 seconds'
        }
      });
      
      const preview = await exportService.generatePreview(mockLayout.layoutId, 'gltf');
      
      expect(preview.previewUrl).toBeDefined();
      expect(preview.estimatedSize).toBe('2.5 MB');
      expect(preview.estimatedTime).toBe('15 seconds');
    });
  });

  describe('Utility Services Integration', () => {
    it('should integrate layout analysis with performance analysis', () => {
      // Test integration between LayoutAnalyzer and PerformanceAnalyzer
      const layoutDensity = LayoutAnalyzer.calculateLayoutDensity(mockLayout, mockEnvelope);
      const layoutCenter = LayoutAnalyzer.calculateLayoutCenter(mockLayout);
      const connectivityMetrics = LayoutAnalyzer.calculateConnectivityMetrics(mockLayout);
      
      const normalizedScore = PerformanceAnalyzer.calculateNormalizedScore(mockMetrics);
      const criticalIssues = PerformanceAnalyzer.identifyCriticalIssues(mockMetrics);
      
      // Results should be consistent and meaningful
      expect(layoutDensity).toBeGreaterThan(0);
      expect(layoutCenter).toBeDefined();
      expect(connectivityMetrics.averageConnections).toBeGreaterThan(0);
      expect(normalizedScore).toBeGreaterThanOrEqual(0);
      expect(normalizedScore).toBeLessThanOrEqual(1);
      expect(Array.isArray(criticalIssues)).toBe(true);
      
      // Integration: high connectivity should correlate with good performance
      if (connectivityMetrics.connectivityRatio > 0.8) {
        expect(normalizedScore).toBeGreaterThan(0.5);
      }
    });

    it('should integrate module utilities with layout analysis', () => {
      const totalVolume = ModuleUtilities.calculateTotalModuleVolume(mockModules);
      const layoutSpread = LayoutAnalyzer.calculateLayoutSpread(mockLayout);
      
      // Results should be consistent
      expect(totalVolume).toBeGreaterThan(0);
      expect(layoutSpread).toBeGreaterThan(0);
      
      // More modules should generally mean larger spread (unless very compact)
      const moduleCount = mockModules.length;
      expect(totalVolume / moduleCount).toBeGreaterThan(0); // Average module volume
    });
  });
});

// ============================================================================
// ERROR HANDLING INTEGRATION TESTS
// ============================================================================

describe('Error Handling Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should handle API errors gracefully', async () => {
    const layoutService = new LayoutService();
    
    // Mock API error
    mockedAxios.post.mockRejectedValueOnce(new Error('Network error'));
    
    await expect(
      layoutService.generateLayouts(mockEnvelope, mockMission)
    ).rejects.toThrow('Network error');
    
    // Service should remain functional after error
    mockedAxios.post.mockResolvedValueOnce({
      data: { layouts: [mockLayout] }
    });
    
    const layouts = await layoutService.generateLayouts(mockEnvelope, mockMission);
    expect(layouts).toHaveLength(1);
  });

  it('should handle invalid data gracefully', () => {
    const layoutService = new LayoutService();
    
    // Test with empty layouts array
    expect(() => layoutService.compareLayouts([])).toThrow('No layouts provided for comparison');
    
    // Test with invalid layout data
    const invalidLayout = { ...mockLayout, modules: [] };
    const comparison = layoutService.compareLayouts([invalidLayout]);
    
    expect(comparison.bestPerforming).toBeDefined();
    expect(comparison.worstPerforming).toBeDefined();
  });

  it('should handle service initialization errors', () => {
    // Test that services can be created even with missing dependencies
    expect(() => new LayoutService()).not.toThrow();
    
    // Test utility functions with edge cases
    expect(() => LayoutAnalyzer.calculateLayoutDensity(mockLayout, mockEnvelope)).not.toThrow();
    expect(() => PerformanceAnalyzer.calculateNormalizedScore(mockMetrics)).not.toThrow();
    expect(() => ModuleUtilities.calculateTotalModuleVolume(mockModules)).not.toThrow();
  });
});

// ============================================================================
// PERFORMANCE INTEGRATION TESTS
// ============================================================================

describe('Performance Integration', () => {
  it('should handle large datasets efficiently', () => {
    // Create large dataset
    const largeModuleSet: ModulePlacement[] = [];
    for (let i = 0; i < 100; i++) {
      largeModuleSet.push({
        module_id: `module_${i}`,
        type: ModuleType.SLEEP_QUARTER,
        position: [Math.random() * 10, Math.random() * 10, Math.random() * 10],
        rotation_deg: Math.random() * 360,
        connections: []
      });
    }
    
    const largeLayout: LayoutSpec = {
      ...mockLayout,
      modules: largeModuleSet
    };
    
    // Test performance of analysis functions
    const startTime = performance.now();
    
    const density = LayoutAnalyzer.calculateLayoutDensity(largeLayout, mockEnvelope);
    const center = LayoutAnalyzer.calculateLayoutCenter(largeLayout);
    const connectivity = LayoutAnalyzer.calculateConnectivityMetrics(largeLayout);
    const totalVolume = ModuleUtilities.calculateTotalModuleVolume(largeModuleSet);
    
    const endTime = performance.now();
    const executionTime = endTime - startTime;
    
    // Should complete within reasonable time (< 100ms for 100 modules)
    expect(executionTime).toBeLessThan(100);
    
    // Results should still be valid
    expect(density).toBeGreaterThan(0);
    expect(center).toBeDefined();
    expect(connectivity.averageConnections).toBeGreaterThanOrEqual(0);
    expect(totalVolume).toBeGreaterThan(0);
  });

  it('should handle concurrent operations', async () => {
    const layoutService = new LayoutService();
    
    // Mock multiple API responses
    mockedAxios.get
      .mockResolvedValueOnce({ data: { layout: { ...mockLayout, layoutId: 'layout-1' } } })
      .mockResolvedValueOnce({ data: { layout: { ...mockLayout, layoutId: 'layout-2' } } })
      .mockResolvedValueOnce({ data: { layout: { ...mockLayout, layoutId: 'layout-3' } } });
    
    // Execute concurrent requests
    const promises = [
      layoutService.getLayout('layout-1'),
      layoutService.getLayout('layout-2'),
      layoutService.getLayout('layout-3')
    ];
    
    const results = await Promise.all(promises);
    
    expect(results).toHaveLength(3);
    expect(results[0]?.layoutId).toBe('layout-1');
    expect(results[1]?.layoutId).toBe('layout-2');
    expect(results[2]?.layoutId).toBe('layout-3');
  });
});

// ============================================================================
// DATA CONSISTENCY INTEGRATION TESTS
// ============================================================================

describe('Data Consistency Integration', () => {
  it('should maintain data consistency across service calls', async () => {
    const layoutService = new LayoutService();
    
    // Mock API response
    mockedAxios.get.mockResolvedValue({
      data: { layout: mockLayout }
    });
    
    // Get layout multiple times
    const layout1 = await layoutService.getLayout(mockLayout.layoutId);
    const layout2 = await layoutService.getLayout(mockLayout.layoutId);
    
    // Data should be identical
    expect(layout1).toEqual(layout2);
    
    // Analyze both layouts
    const analysis1 = {
      density: LayoutAnalyzer.calculateLayoutDensity(layout1!, mockEnvelope),
      center: LayoutAnalyzer.calculateLayoutCenter(layout1!),
      connectivity: LayoutAnalyzer.calculateConnectivityMetrics(layout1!)
    };
    
    const analysis2 = {
      density: LayoutAnalyzer.calculateLayoutDensity(layout2!, mockEnvelope),
      center: LayoutAnalyzer.calculateLayoutCenter(layout2!),
      connectivity: LayoutAnalyzer.calculateConnectivityMetrics(layout2!)
    };
    
    // Analysis results should be identical
    expect(analysis1.density).toBe(analysis2.density);
    expect(analysis1.center).toEqual(analysis2.center);
    expect(analysis1.connectivity).toEqual(analysis2.connectivity);
  });

  it('should handle data transformations consistently', () => {
    // Test serialization/deserialization consistency
    const originalLayout = mockLayout;
    const serialized = JSON.stringify(originalLayout);
    const deserialized = JSON.parse(serialized) as LayoutSpec;
    
    // Core data should be preserved
    expect(deserialized.layoutId).toBe(originalLayout.layoutId);
    expect(deserialized.envelopeId).toBe(originalLayout.envelopeId);
    expect(deserialized.modules).toHaveLength(originalLayout.modules.length);
    
    // Analysis should produce same results
    const originalAnalysis = LayoutAnalyzer.calculateLayoutCenter(originalLayout);
    const deserializedAnalysis = LayoutAnalyzer.calculateLayoutCenter(deserialized);
    
    expect(originalAnalysis).toEqual(deserializedAnalysis);
  });
});

// ============================================================================
// REAL-WORLD SCENARIO TESTS
// ============================================================================

describe('Real-World Scenario Integration', () => {
  it('should handle complete design workflow', async () => {
    const layoutService = new LayoutService();
    
    // Mock the complete workflow
    mockedAxios.post.mockResolvedValueOnce({
      data: { layouts: [mockLayout] }
    });
    
    mockedAxios.get.mockResolvedValueOnce({
      data: { layout: mockLayout }
    });
    
    mockedAxios.post.mockResolvedValueOnce({
      data: { 
        downloadUrl: 'http://example.com/export.pdf',
        filename: 'design_report.pdf'
      }
    });
    
    // Step 1: Generate layouts
    const layouts = await layoutService.generateLayouts(mockEnvelope, mockMission);
    expect(layouts).toHaveLength(1);
    
    // Step 2: Analyze best layout
    const bestLayout = layouts[0];
    const analysis = {
      density: LayoutAnalyzer.calculateLayoutDensity(bestLayout, mockEnvelope),
      performance: PerformanceAnalyzer.calculateNormalizedScore(bestLayout.kpis),
      issues: PerformanceAnalyzer.identifyCriticalIssues(bestLayout.kpis)
    };
    
    expect(analysis.density).toBeGreaterThan(0);
    expect(analysis.performance).toBeGreaterThanOrEqual(0);
    expect(Array.isArray(analysis.issues)).toBe(true);
    
    // Step 3: Export results
    const exportResult = await exportService.exportLayout(bestLayout.layoutId, 'pdf');
    expect(exportResult.success).toBe(true);
    
    console.log('Complete workflow test passed:');
    console.log(`- Generated ${layouts.length} layout(s)`);
    console.log(`- Layout density: ${analysis.density.toFixed(3)}`);
    console.log(`- Performance score: ${analysis.performance.toFixed(3)}`);
    console.log(`- Critical issues: ${analysis.issues.length}`);
    console.log(`- Export successful: ${exportResult.success}`);
  });

  it('should handle iterative design process', async () => {
    const layoutService = new LayoutService();
    
    // Simulate multiple design iterations
    const iterations = [
      { ...mockLayout, layoutId: 'iteration-1', kpis: { ...mockMetrics, safetyScore: 0.6 } },
      { ...mockLayout, layoutId: 'iteration-2', kpis: { ...mockMetrics, safetyScore: 0.7 } },
      { ...mockLayout, layoutId: 'iteration-3', kpis: { ...mockMetrics, safetyScore: 0.8 } }
    ];
    
    // Compare iterations
    const comparison = layoutService.compareLayouts(iterations);
    
    expect(comparison.bestPerforming.layoutId).toBe('iteration-3');
    expect(comparison.worstPerforming.layoutId).toBe('iteration-1');
    
    // Verify improvement trend
    const scores = iterations.map(layout => 
      PerformanceAnalyzer.calculateNormalizedScore(layout.kpis)
    );
    
    expect(scores[2]).toBeGreaterThan(scores[1]);
    expect(scores[1]).toBeGreaterThan(scores[0]);
  });
});