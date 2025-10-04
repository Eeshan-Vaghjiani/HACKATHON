/**
 * Layout Service - High-level service for layout operations
 * 
 * This service provides a higher-level abstraction over the raw API calls,
 * including caching, error handling, and business logic.
 */

import { LayoutAPI, formatAPIError } from './api';
import { 
  LayoutSpec, 
  EnvelopeSpec, 
  MissionParameters, 
  ModulePlacement,
  PerformanceMetrics,
  ValidationResult
} from '../types';
import { 
  validateLayoutSpec, 
  validateModulePlacement,
  validatePerformanceMetrics 
} from '../types/validation';

// ============================================================================
// TYPES
// ============================================================================

export interface LayoutGenerationOptions {
  count?: number;
  algorithm?: 'random' | 'genetic' | 'hybrid';
  constraints?: {
    maxIterations?: number;
    convergenceThreshold?: number;
    priorityWeights?: Record<string, number>;
  };
}

export interface LayoutUpdateOptions {
  recalculateMetrics?: boolean;
  validateConstraints?: boolean;
  saveToDatabase?: boolean;
}

export interface LayoutSearchOptions {
  envelopeId?: string;
  minScore?: number;
  maxScore?: number;
  sortBy?: 'score' | 'created' | 'name';
  sortOrder?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export interface LayoutCache {
  layouts: Map<string, LayoutSpec>;
  lastUpdated: Map<string, number>;
  maxAge: number; // milliseconds
}

// ============================================================================
// LAYOUT SERVICE CLASS
// ============================================================================

export class LayoutService {
  private cache: LayoutCache;
  private readonly CACHE_MAX_AGE = 5 * 60 * 1000; // 5 minutes

  constructor() {
    this.cache = {
      layouts: new Map(),
      lastUpdated: new Map(),
      maxAge: this.CACHE_MAX_AGE
    };
  }

  // ============================================================================
  // LAYOUT GENERATION
  // ============================================================================

  /**
   * Generate multiple candidate layouts with validation and caching
   */
  async generateLayouts(
    envelope: EnvelopeSpec,
    mission: MissionParameters,
    options: LayoutGenerationOptions = {}
  ): Promise<LayoutSpec[]> {
    const { count = 5, algorithm = 'random', constraints } = options;

    try {
      // Validate inputs
      const validationErrors = this.validateGenerationInputs(envelope, mission);
      if (validationErrors.length > 0) {
        throw new Error(`Validation failed: ${validationErrors.join(', ')}`);
      }

      // Generate layouts using API
      const layouts = await LayoutAPI.generateLayouts(envelope, mission, count);

      // Validate and cache generated layouts
      const validatedLayouts = await this.validateAndCacheLayouts(layouts);

      return validatedLayouts;
    } catch (error) {
      throw new Error(`Layout generation failed: ${formatAPIError(error)}`);
    }
  }

  /**
   * Generate a single optimized layout
   */
  async generateOptimizedLayout(
    envelope: EnvelopeSpec,
    mission: MissionParameters,
    targetMetrics?: Partial<PerformanceMetrics>
  ): Promise<LayoutSpec> {
    const layouts = await this.generateLayouts(envelope, mission, { count: 8 });
    
    if (layouts.length === 0) {
      throw new Error('No layouts could be generated');
    }

    // Find the best layout based on target metrics or overall score
    let bestLayout = layouts[0];
    let bestScore = this.calculateLayoutScore(bestLayout, targetMetrics);

    for (const layout of layouts.slice(1)) {
      const score = this.calculateLayoutScore(layout, targetMetrics);
      if (score > bestScore) {
        bestLayout = layout;
        bestScore = score;
      }
    }

    return bestLayout;
  }

  // ============================================================================
  // LAYOUT RETRIEVAL
  // ============================================================================

  /**
   * Get a layout by ID with caching
   */
  async getLayout(layoutId: string, useCache: boolean = true): Promise<LayoutSpec | null> {
    // Check cache first
    if (useCache && this.isLayoutCached(layoutId)) {
      return this.cache.layouts.get(layoutId) || null;
    }

    try {
      const layout = await LayoutAPI.getLayout(layoutId);
      
      // Cache the result
      this.cacheLayout(layout);
      
      return layout;
    } catch (error) {
      if (error instanceof Error && error.message.includes('not found')) {
        return null;
      }
      throw new Error(`Failed to retrieve layout: ${formatAPIError(error)}`);
    }
  }

  /**
   * Search layouts with advanced filtering
   */
  async searchLayouts(options: LayoutSearchOptions = {}): Promise<LayoutSpec[]> {
    const {
      envelopeId,
      minScore,
      maxScore,
      sortBy = 'score',
      sortOrder = 'desc',
      limit = 50,
      offset = 0
    } = options;

    try {
      let layouts: LayoutSpec[];

      if (minScore !== undefined || maxScore !== undefined) {
        layouts = await LayoutAPI.searchLayoutsByScore(minScore, maxScore);
      } else if (envelopeId) {
        layouts = await LayoutAPI.getLayouts(envelopeId);
      } else {
        layouts = await LayoutAPI.getLayouts();
      }

      // Apply client-side sorting and pagination
      const sortedLayouts = this.sortLayouts(layouts, sortBy, sortOrder);
      const paginatedLayouts = sortedLayouts.slice(offset, offset + limit);

      // Cache results
      paginatedLayouts.forEach(layout => this.cacheLayout(layout));

      return paginatedLayouts;
    } catch (error) {
      throw new Error(`Layout search failed: ${formatAPIError(error)}`);
    }
  }

  /**
   * Get top performing layouts for an envelope
   */
  async getTopPerformingLayouts(
    envelopeId?: string,
    limit: number = 10
  ): Promise<LayoutSpec[]> {
    try {
      const layouts = await LayoutAPI.getTopPerformingLayouts(envelopeId, limit);
      
      // Cache results
      layouts.forEach(layout => this.cacheLayout(layout));
      
      return layouts;
    } catch (error) {
      throw new Error(`Failed to get top performing layouts: ${formatAPIError(error)}`);
    }
  }

  // ============================================================================
  // LAYOUT MODIFICATION
  // ============================================================================

  /**
   * Update a layout with validation and metric recalculation
   */
  async updateLayout(
    layout: LayoutSpec,
    options: LayoutUpdateOptions = {}
  ): Promise<LayoutSpec> {
    const {
      recalculateMetrics = true,
      validateConstraints = true,
      saveToDatabase = true
    } = options;

    try {
      // Validate layout if requested
      if (validateConstraints) {
        const validation = validateLayoutSpec(layout);
        if (!validation.isValid) {
          throw new Error(`Layout validation failed: ${validation.errors.map(e => e.message).join(', ')}`);
        }
      }

      // Recalculate metrics if requested
      let updatedLayout = layout;
      if (recalculateMetrics) {
        updatedLayout = await this.recalculateLayoutMetrics(layout);
      }

      // Save to database if requested
      if (saveToDatabase) {
        updatedLayout = await LayoutAPI.updateLayout(updatedLayout);
      }

      // Update cache
      this.cacheLayout(updatedLayout);

      return updatedLayout;
    } catch (error) {
      throw new Error(`Layout update failed: ${formatAPIError(error)}`);
    }
  }

  /**
   * Update module position in a layout
   */
  async updateModulePosition(
    layoutId: string,
    moduleId: string,
    newPosition: [number, number, number],
    newRotation?: number
  ): Promise<LayoutSpec> {
    const layout = await this.getLayout(layoutId);
    if (!layout) {
      throw new Error(`Layout ${layoutId} not found`);
    }

    // Find and update the module
    const updatedModules = layout.modules.map(module => {
      if (module.module_id === moduleId) {
        return {
          ...module,
          position: newPosition,
          rotation_deg: newRotation !== undefined ? newRotation : module.rotation_deg
        };
      }
      return module;
    });

    const updatedLayout: LayoutSpec = {
      ...layout,
      modules: updatedModules
    };

    return this.updateLayout(updatedLayout, { recalculateMetrics: true });
  }

  /**
   * Delete a layout
   */
  async deleteLayout(layoutId: string): Promise<void> {
    try {
      await LayoutAPI.deleteLayout(layoutId);
      
      // Remove from cache
      this.cache.layouts.delete(layoutId);
      this.cache.lastUpdated.delete(layoutId);
    } catch (error) {
      throw new Error(`Layout deletion failed: ${formatAPIError(error)}`);
    }
  }

  // ============================================================================
  // LAYOUT ANALYSIS
  // ============================================================================

  /**
   * Compare multiple layouts and return analysis
   */
  compareLayouts(layouts: LayoutSpec[]): {
    bestPerforming: LayoutSpec;
    worstPerforming: LayoutSpec;
    averageMetrics: PerformanceMetrics;
    metricRanges: Record<keyof PerformanceMetrics, { min: number; max: number }>;
  } {
    if (layouts.length === 0) {
      throw new Error('No layouts provided for comparison');
    }

    let bestLayout = layouts[0];
    let worstLayout = layouts[0];
    let bestScore = this.calculateOverallScore(bestLayout.kpis);
    let worstScore = bestScore;

    // Calculate averages and find best/worst
    const metricSums: Partial<PerformanceMetrics> = {};
    const metricMins: Partial<PerformanceMetrics> = {};
    const metricMaxs: Partial<PerformanceMetrics> = {};

    layouts.forEach(layout => {
      const score = this.calculateOverallScore(layout.kpis);
      
      if (score > bestScore) {
        bestLayout = layout;
        bestScore = score;
      }
      if (score < worstScore) {
        worstLayout = layout;
        worstScore = score;
      }

      // Accumulate metrics for averages and ranges
      Object.entries(layout.kpis).forEach(([key, value]) => {
        if (typeof value === 'number') {
          const metricKey = key as keyof PerformanceMetrics;
          metricSums[metricKey] = (metricSums[metricKey] || 0) + value;
          metricMins[metricKey] = Math.min(metricMins[metricKey] || value, value);
          metricMaxs[metricKey] = Math.max(metricMaxs[metricKey] || value, value);
        }
      });
    });

    // Calculate averages
    const averageMetrics = {} as PerformanceMetrics;
    Object.entries(metricSums).forEach(([key, sum]) => {
      (averageMetrics as any)[key] = sum! / layouts.length;
    });

    // Build ranges
    const metricRanges = {} as Record<keyof PerformanceMetrics, { min: number; max: number }>;
    Object.keys(metricMins).forEach(key => {
      const metricKey = key as keyof PerformanceMetrics;
      metricRanges[metricKey] = {
        min: metricMins[metricKey]!,
        max: metricMaxs[metricKey]!
      };
    });

    return {
      bestPerforming: bestLayout,
      worstPerforming: worstLayout,
      averageMetrics,
      metricRanges
    };
  }

  // ============================================================================
  // PRIVATE HELPER METHODS
  // ============================================================================

  private validateGenerationInputs(
    envelope: EnvelopeSpec,
    mission: MissionParameters
  ): string[] {
    const errors: string[] = [];

    // Basic validation - more comprehensive validation would use the validation functions
    if (!envelope.id) {
      errors.push('Envelope ID is required');
    }

    if (mission.crew_size < 1 || mission.crew_size > 20) {
      errors.push('Crew size must be between 1 and 20');
    }

    if (mission.duration_days < 1) {
      errors.push('Mission duration must be at least 1 day');
    }

    return errors;
  }

  private async validateAndCacheLayouts(layouts: LayoutSpec[]): Promise<LayoutSpec[]> {
    const validatedLayouts: LayoutSpec[] = [];

    for (const layout of layouts) {
      const validation = validateLayoutSpec(layout);
      if (validation.isValid) {
        this.cacheLayout(layout);
        validatedLayouts.push(layout);
      } else {
        console.warn(`Layout ${layout.layoutId} failed validation:`, validation.errors);
      }
    }

    return validatedLayouts;
  }

  private calculateLayoutScore(
    layout: LayoutSpec,
    targetMetrics?: Partial<PerformanceMetrics>
  ): number {
    if (!targetMetrics) {
      return this.calculateOverallScore(layout.kpis);
    }

    // Calculate weighted score based on target metrics
    let score = 0;
    let weightSum = 0;

    Object.entries(targetMetrics).forEach(([key, targetValue]) => {
      if (typeof targetValue === 'number') {
        const actualValue = (layout.kpis as any)[key];
        if (typeof actualValue === 'number') {
          // Normalize score based on how close actual is to target
          const difference = Math.abs(actualValue - targetValue);
          const normalizedScore = Math.max(0, 1 - difference / targetValue);
          score += normalizedScore;
          weightSum += 1;
        }
      }
    });

    return weightSum > 0 ? score / weightSum : 0;
  }

  private calculateOverallScore(metrics: PerformanceMetrics): number {
    // Simple weighted average of key metrics
    const weights = {
      safetyScore: 0.3,
      efficiencyScore: 0.2,
      connectivityScore: 0.2,
      thermalMargin: 0.1,
      lssMargin: 0.1,
      stowageUtilization: 0.1
    };

    let score = 0;
    let totalWeight = 0;

    Object.entries(weights).forEach(([key, weight]) => {
      const value = (metrics as any)[key];
      if (typeof value === 'number') {
        score += value * weight;
        totalWeight += weight;
      }
    });

    return totalWeight > 0 ? score / totalWeight : 0;
  }

  private async recalculateLayoutMetrics(layout: LayoutSpec): Promise<LayoutSpec> {
    // In a real implementation, this would call the backend to recalculate metrics
    // For now, we'll return the layout unchanged
    console.log('Recalculating metrics for layout:', layout.layoutId);
    return layout;
  }

  private sortLayouts(
    layouts: LayoutSpec[],
    sortBy: string,
    sortOrder: 'asc' | 'desc'
  ): LayoutSpec[] {
    return [...layouts].sort((a, b) => {
      let aValue: any, bValue: any;

      switch (sortBy) {
        case 'score':
          aValue = this.calculateOverallScore(a.kpis);
          bValue = this.calculateOverallScore(b.kpis);
          break;
        case 'created':
          aValue = a.metadata?.created || new Date(0);
          bValue = b.metadata?.created || new Date(0);
          break;
        case 'name':
          aValue = a.metadata?.name || a.layoutId;
          bValue = b.metadata?.name || b.layoutId;
          break;
        default:
          return 0;
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortOrder === 'asc' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortOrder === 'asc' ? aValue - bValue : bValue - aValue;
      }

      if (aValue instanceof Date && bValue instanceof Date) {
        return sortOrder === 'asc' 
          ? aValue.getTime() - bValue.getTime()
          : bValue.getTime() - aValue.getTime();
      }

      return 0;
    });
  }

  private isLayoutCached(layoutId: string): boolean {
    const lastUpdated = this.cache.lastUpdated.get(layoutId);
    if (!lastUpdated) return false;
    
    const age = Date.now() - lastUpdated;
    return age < this.cache.maxAge && this.cache.layouts.has(layoutId);
  }

  private cacheLayout(layout: LayoutSpec): void {
    this.cache.layouts.set(layout.layoutId, layout);
    this.cache.lastUpdated.set(layout.layoutId, Date.now());
  }

  // ============================================================================
  // CACHE MANAGEMENT
  // ============================================================================

  /**
   * Clear the layout cache
   */
  clearCache(): void {
    this.cache.layouts.clear();
    this.cache.lastUpdated.clear();
  }

  /**
   * Get cache statistics
   */
  getCacheStats(): {
    size: number;
    oldestEntry: number;
    newestEntry: number;
  } {
    const timestamps = Array.from(this.cache.lastUpdated.values());
    
    return {
      size: this.cache.layouts.size,
      oldestEntry: timestamps.length > 0 ? Math.min(...timestamps) : 0,
      newestEntry: timestamps.length > 0 ? Math.max(...timestamps) : 0
    };
  }
}

// ============================================================================
// SINGLETON INSTANCE
// ============================================================================

export const layoutService = new LayoutService();
export default layoutService;