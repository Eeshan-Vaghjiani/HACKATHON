/**
 * Utility Service - Common utility functions and helpers
 */

import { 
  LayoutSpec, 
  ModulePlacement, 
  EnvelopeSpec, 
  PerformanceMetrics,
  Vector3D,
  BoundingBox
} from '../types';
import { 
  calculateEnvelopeVolume,
  calculateCentroid,
  distance3D,
  createVector3D,
  createBoundingBoxFromCenter
} from '../types/geometry';

// ============================================================================
// LAYOUT ANALYSIS UTILITIES
// ============================================================================

export class LayoutAnalyzer {
  /**
   * Calculate layout density (modules per unit volume)
   */
  static calculateLayoutDensity(layout: LayoutSpec, envelope: EnvelopeSpec): number {
    const envelopeVolume = calculateEnvelopeVolume(envelope);
    return layout.modules.length / envelopeVolume;
  }

  /**
   * Calculate the geometric center of all modules in a layout
   */
  static calculateLayoutCenter(layout: LayoutSpec): Vector3D {
    const positions = layout.modules.map(module => 
      createVector3D(module.position[0], module.position[1], module.position[2])
    );
    return calculateCentroid(positions);
  }

  /**
   * Calculate the spread (standard deviation) of module positions
   */
  static calculateLayoutSpread(layout: LayoutSpec): number {
    if (layout.modules.length === 0) return 0;

    const center = this.calculateLayoutCenter(layout);
    const distances = layout.modules.map(module => {
      const pos = createVector3D(module.position[0], module.position[1], module.position[2]);
      return distance3D(pos, center);
    });

    const mean = distances.reduce((sum, d) => sum + d, 0) / distances.length;
    const variance = distances.reduce((sum, d) => sum + Math.pow(d - mean, 2), 0) / distances.length;
    
    return Math.sqrt(variance);
  }

  /**
   * Find the most isolated module (furthest from others)
   */
  static findMostIsolatedModule(layout: LayoutSpec): ModulePlacement | null {
    if (layout.modules.length === 0) return null;

    let mostIsolated = layout.modules[0];
    let maxMinDistance = 0;

    for (const module of layout.modules) {
      const modulePos = createVector3D(module.position[0], module.position[1], module.position[2]);
      
      // Find minimum distance to any other module
      let minDistance = Infinity;
      for (const otherModule of layout.modules) {
        if (otherModule.module_id === module.module_id) continue;
        
        const otherPos = createVector3D(otherModule.position[0], otherModule.position[1], otherModule.position[2]);
        const distance = distance3D(modulePos, otherPos);
        minDistance = Math.min(minDistance, distance);
      }

      if (minDistance > maxMinDistance) {
        maxMinDistance = minDistance;
        mostIsolated = module;
      }
    }

    return mostIsolated;
  }

  /**
   * Calculate connectivity metrics for a layout
   */
  static calculateConnectivityMetrics(layout: LayoutSpec): {
    averageConnections: number;
    maxConnections: number;
    minConnections: number;
    isolatedModules: number;
    connectivityRatio: number;
  } {
    if (layout.modules.length === 0) {
      return {
        averageConnections: 0,
        maxConnections: 0,
        minConnections: 0,
        isolatedModules: 0,
        connectivityRatio: 0
      };
    }

    const connectionCounts = layout.modules.map(module => module.connections.length);
    const totalConnections = connectionCounts.reduce((sum, count) => sum + count, 0);
    const isolatedModules = connectionCounts.filter(count => count === 0).length;
    
    // Maximum possible connections (each module connected to all others)
    const maxPossibleConnections = layout.modules.length * (layout.modules.length - 1);

    return {
      averageConnections: totalConnections / layout.modules.length,
      maxConnections: Math.max(...connectionCounts),
      minConnections: Math.min(...connectionCounts),
      isolatedModules,
      connectivityRatio: maxPossibleConnections > 0 ? totalConnections / maxPossibleConnections : 0
    };
  }
}

// ============================================================================
// PERFORMANCE UTILITIES
// ============================================================================

export class PerformanceAnalyzer {
  /**
   * Identify critical performance issues in a layout
   */
  static identifyCriticalIssues(metrics: PerformanceMetrics): string[] {
    const issues: string[] = [];

    if (metrics.thermalMargin < 0.05) {
      issues.push('Critical thermal margin - insufficient cooling capacity');
    }

    if (metrics.lssMargin < 0.1) {
      issues.push('Critical LSS margin - insufficient life support capacity');
    }

    if (metrics.egressTime > 300) {
      issues.push('Emergency egress time exceeds 5 minutes');
    }

    if (metrics.stowageUtilization > 1.2) {
      issues.push('Severe overcrowding - stowage utilization above 120%');
    }

    if (metrics.safetyScore && metrics.safetyScore < 0.3) {
      issues.push('Critical safety score - major safety concerns');
    }

    return issues;
  }

  /**
   * Calculate a normalized performance score (0-1)
   */
  static calculateNormalizedScore(metrics: PerformanceMetrics): number {
    const weights = {
      safety: 0.3,
      efficiency: 0.2,
      connectivity: 0.15,
      thermal: 0.15,
      lss: 0.15,
      stowage: 0.05
    };

    let score = 0;

    // Safety score (higher is better)
    if (metrics.safetyScore !== undefined) {
      score += (metrics.safetyScore || 0) * weights.safety;
    }

    // Efficiency score (higher is better)
    if (metrics.efficiencyScore !== undefined) {
      score += (metrics.efficiencyScore || 0) * weights.efficiency;
    }

    // Connectivity score (higher is better)
    if (metrics.connectivityScore !== undefined) {
      score += (metrics.connectivityScore || 0) * weights.connectivity;
    }

    // Thermal margin (higher is better, normalize to 0-1)
    const thermalScore = Math.min(1, Math.max(0, metrics.thermalMargin * 2)); // 50% margin = 1.0 score
    score += thermalScore * weights.thermal;

    // LSS margin (higher is better, normalize to 0-1)
    const lssScore = Math.min(1, Math.max(0, metrics.lssMargin * 2)); // 50% margin = 1.0 score
    score += lssScore * weights.lss;

    // Stowage utilization (optimal around 80%, penalize over/under)
    const optimalStowage = 0.8;
    const stowageDeviation = Math.abs(metrics.stowageUtilization - optimalStowage);
    const stowageScore = Math.max(0, 1 - stowageDeviation * 2);
    score += stowageScore * weights.stowage;

    return Math.min(1, Math.max(0, score));
  }

  /**
   * Compare two performance metrics and return improvement/degradation
   */
  static compareMetrics(
    baseline: PerformanceMetrics, 
    comparison: PerformanceMetrics
  ): Record<keyof PerformanceMetrics, { change: number; improvement: boolean }> {
    const result = {} as Record<keyof PerformanceMetrics, { change: number; improvement: boolean }>;

    // Metrics where higher is better
    const higherIsBetter = ['thermalMargin', 'lssMargin', 'connectivityScore', 'safetyScore', 'efficiencyScore'];
    
    // Metrics where lower is better
    const lowerIsBetter = ['meanTransitTime', 'egressTime', 'massTotal', 'powerBudget'];

    Object.keys(baseline).forEach(key => {
      const metricKey = key as keyof PerformanceMetrics;
      const baseValue = baseline[metricKey] as number;
      const compValue = comparison[metricKey] as number;

      if (typeof baseValue === 'number' && typeof compValue === 'number') {
        const change = ((compValue - baseValue) / baseValue) * 100; // Percentage change
        
        let improvement: boolean;
        if (higherIsBetter.includes(key)) {
          improvement = compValue > baseValue;
        } else if (lowerIsBetter.includes(key)) {
          improvement = compValue < baseValue;
        } else {
          // For stowageUtilization, closer to 80% is better
          if (key === 'stowageUtilization') {
            const baseDistance = Math.abs(baseValue - 0.8);
            const compDistance = Math.abs(compValue - 0.8);
            improvement = compDistance < baseDistance;
          } else {
            improvement = false; // Default for unknown metrics
          }
        }

        result[metricKey] = { change, improvement };
      }
    });

    return result;
  }
}

// ============================================================================
// MODULE UTILITIES
// ============================================================================

export class ModuleUtilities {
  /**
   * Get standard module dimensions by type
   */
  static getModuleDimensions(moduleType: string): { x: number; y: number; z: number } {
    const dimensions: Record<string, { x: number; y: number; z: number }> = {
      sleep_quarter: { x: 2.0, y: 2.0, z: 2.5 },
      galley: { x: 3.0, y: 2.5, z: 2.2 },
      laboratory: { x: 4.0, y: 3.0, z: 2.8 },
      airlock: { x: 2.5, y: 2.5, z: 3.0 },
      mechanical: { x: 3.5, y: 2.8, z: 2.5 },
      medical: { x: 3.0, y: 2.5, z: 2.5 },
      exercise: { x: 4.0, y: 3.5, z: 2.8 },
      storage: { x: 2.5, y: 2.0, z: 2.0 }
    };

    return dimensions[moduleType] || { x: 2.0, y: 2.0, z: 2.0 };
  }

  /**
   * Calculate module bounding box
   */
  static getModuleBoundingBox(module: ModulePlacement): BoundingBox {
    const dimensions = this.getModuleDimensions(module.type);
    const center = createVector3D(module.position[0], module.position[1], module.position[2]);
    const size = createVector3D(dimensions.x, dimensions.y, dimensions.z);
    
    return createBoundingBoxFromCenter(center, size);
  }

  /**
   * Check if two modules are adjacent (within connection distance)
   */
  static areModulesAdjacent(module1: ModulePlacement, module2: ModulePlacement, maxDistance: number = 3.0): boolean {
    const pos1 = createVector3D(module1.position[0], module1.position[1], module1.position[2]);
    const pos2 = createVector3D(module2.position[0], module2.position[1], module2.position[2]);
    
    return distance3D(pos1, pos2) <= maxDistance;
  }

  /**
   * Find all modules within a certain distance of a given module
   */
  static findNearbyModules(
    targetModule: ModulePlacement, 
    allModules: ModulePlacement[], 
    maxDistance: number = 5.0
  ): ModulePlacement[] {
    const targetPos = createVector3D(targetModule.position[0], targetModule.position[1], targetModule.position[2]);
    
    return allModules.filter(module => {
      if (module.module_id === targetModule.module_id) return false;
      
      const modulePos = createVector3D(module.position[0], module.position[1], module.position[2]);
      return distance3D(targetPos, modulePos) <= maxDistance;
    });
  }

  /**
   * Calculate the total volume occupied by modules
   */
  static calculateTotalModuleVolume(modules: ModulePlacement[]): number {
    return modules.reduce((total, module) => {
      const dimensions = this.getModuleDimensions(module.type);
      return total + (dimensions.x * dimensions.y * dimensions.z);
    }, 0);
  }
}

// ============================================================================
// FORMAT UTILITIES
// ============================================================================

export class FormatUtilities {
  /**
   * Format a number with appropriate units and precision
   */
  static formatMetric(value: number, unit: string, precision: number = 1): string {
    if (unit === 'kg' && value >= 1000) {
      return `${(value / 1000).toFixed(precision)}t`;
    }
    
    if (unit === 'W' && value >= 1000) {
      return `${(value / 1000).toFixed(precision)}kW`;
    }
    
    if (unit === '%') {
      return `${(value * 100).toFixed(precision)}%`;
    }
    
    return `${value.toFixed(precision)}${unit}`;
  }

  /**
   * Format a duration in seconds to human-readable format
   */
  static formatDuration(seconds: number): string {
    if (seconds < 60) {
      return `${seconds.toFixed(0)}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds.toFixed(0)}s` : `${minutes}m`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
    }
  }

  /**
   * Format a position vector for display
   */
  static formatPosition(position: [number, number, number], precision: number = 1): string {
    return `[${position.map(p => p.toFixed(precision)).join(', ')}]`;
  }

  /**
   * Format a percentage with color coding
   */
  static formatPercentageWithColor(value: number, thresholds: { good: number; warning: number }): {
    text: string;
    color: 'green' | 'yellow' | 'red';
  } {
    const percentage = value * 100;
    const text = `${percentage.toFixed(1)}%`;
    
    let color: 'green' | 'yellow' | 'red';
    if (percentage >= thresholds.good) {
      color = 'green';
    } else if (percentage >= thresholds.warning) {
      color = 'yellow';
    } else {
      color = 'red';
    }
    
    return { text, color };
  }
}

// ============================================================================
// EXPORT UTILITIES
// ============================================================================

export class ExportUtilities {
  /**
   * Export layout data as JSON
   */
  static exportLayoutAsJSON(layout: LayoutSpec): string {
    return JSON.stringify(layout, null, 2);
  }

  /**
   * Export layout summary as CSV
   */
  static exportLayoutSummaryAsCSV(layouts: LayoutSpec[]): string {
    const headers = [
      'Layout ID',
      'Module Count',
      'Transit Time (s)',
      'Egress Time (s)',
      'Mass (kg)',
      'Power (W)',
      'Thermal Margin (%)',
      'LSS Margin (%)',
      'Stowage Util (%)',
      'Safety Score',
      'Overall Score'
    ];

    const rows = layouts.map(layout => [
      layout.layoutId,
      layout.modules.length,
      layout.kpis.meanTransitTime.toFixed(1),
      layout.kpis.egressTime.toFixed(1),
      layout.kpis.massTotal.toFixed(0),
      layout.kpis.powerBudget.toFixed(0),
      (layout.kpis.thermalMargin * 100).toFixed(1),
      (layout.kpis.lssMargin * 100).toFixed(1),
      (layout.kpis.stowageUtilization * 100).toFixed(1),
      layout.kpis.safetyScore?.toFixed(2) || 'N/A',
      PerformanceAnalyzer.calculateNormalizedScore(layout.kpis).toFixed(2)
    ]);

    return [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
  }

  /**
   * Generate a layout report in markdown format
   */
  static generateLayoutReport(layout: LayoutSpec): string {
    const report = [
      `# Layout Report: ${layout.metadata?.name || layout.layoutId}`,
      '',
      '## Overview',
      `- **Layout ID**: ${layout.layoutId}`,
      `- **Envelope ID**: ${layout.envelopeId}`,
      `- **Module Count**: ${layout.modules.length}`,
      `- **Created**: ${layout.metadata?.created ? new Date(layout.metadata.created).toLocaleString() : 'Unknown'}`,
      '',
      '## Performance Metrics',
      `- **Mean Transit Time**: ${FormatUtilities.formatDuration(layout.kpis.meanTransitTime)}`,
      `- **Emergency Egress Time**: ${FormatUtilities.formatDuration(layout.kpis.egressTime)}`,
      `- **Total Mass**: ${FormatUtilities.formatMetric(layout.kpis.massTotal, 'kg')}`,
      `- **Power Budget**: ${FormatUtilities.formatMetric(layout.kpis.powerBudget, 'W')}`,
      `- **Thermal Margin**: ${FormatUtilities.formatMetric(layout.kpis.thermalMargin, '%')}`,
      `- **LSS Margin**: ${FormatUtilities.formatMetric(layout.kpis.lssMargin, '%')}`,
      `- **Stowage Utilization**: ${FormatUtilities.formatMetric(layout.kpis.stowageUtilization, '%')}`,
      '',
      '## Module Layout',
      '| Module ID | Type | Position | Rotation | Connections |',
      '|-----------|------|----------|----------|-------------|'
    ];

    layout.modules.forEach(module => {
      report.push(
        `| ${module.module_id} | ${module.type} | ${FormatUtilities.formatPosition(module.position)} | ${module.rotation_deg.toFixed(0)}° | ${module.connections.length} |`
      );
    });

    report.push('');
    report.push('## Analysis');
    report.push(layout.explainability || 'No analysis available.');

    const criticalIssues = PerformanceAnalyzer.identifyCriticalIssues(layout.kpis);
    if (criticalIssues.length > 0) {
      report.push('');
      report.push('## Critical Issues');
      criticalIssues.forEach(issue => {
        report.push(`- ⚠️ ${issue}`);
      });
    }

    return report.join('\n');
  }
}

// All utilities are already exported as classes above