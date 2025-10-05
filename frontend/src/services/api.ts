import axios from 'axios';
import { EnvelopeSpec, MissionParameters, LayoutSpec } from '../types';
import { generateMockLayouts } from './mockData';

// ============================================================================
// API CONFIGURATION
// ============================================================================

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
console.log('API_BASE_URL:', API_BASE_URL);

// Flag to enable mock mode when API is not available
const ENABLE_MOCK_MODE = true; // Set to true to use mock data when API fails
let useMockData = false;

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds for layout generation
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request/response interceptors for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ============================================================================
// API TYPES
// ============================================================================

export interface GenerateLayoutsRequest {
  envelope: EnvelopeSpec;
  mission_params: MissionParameters;
  count?: number;
}

export interface GenerateLayoutsResponse {
  layouts: LayoutSpec[];
}

export interface ApiError {
  detail: string;
  error_code?: string;
}

// ============================================================================
// LAYOUT API FUNCTIONS
// ============================================================================

export class LayoutAPI {
  /**
   * Generate multiple candidate layouts for a habitat envelope
   */
  static async generateLayouts(
    envelope: EnvelopeSpec,
    missionParams: MissionParameters,
    count: number = 5
  ): Promise<LayoutSpec[]> {
    if (useMockData) {
      console.log('Using mock data for layout generation');
      return generateMockLayouts(envelope, missionParams, count);
    }
    
    try {
      const response = await apiClient.post<LayoutSpec[]>('/layouts/generate', {
        envelope,
        mission_params: missionParams,
        count
      });

      return response.data;
    } catch (error: any) {
      if (ENABLE_MOCK_MODE) {
        console.log('API connection failed, switching to mock mode');
        useMockData = true;
        return generateMockLayouts(envelope, missionParams, count);
      }
      
      if (error.response?.status === 400) {
        throw new Error(`Layout generation failed: ${error.response.data.detail}`);
      } else if (error.response?.status === 500) {
        throw new Error('Server error during layout generation. Please try again.');
      } else {
        throw new Error('Failed to generate layouts. Please check your connection.');
      }
    }
  }

  /**
   * Get all generated layouts
   */
  static async getLayouts(envelopeId?: string): Promise<LayoutSpec[]> {
    if (useMockData) {
      console.log('Using mock data for fetching layouts');
      return generateMockLayouts();
    }
    
    try {
      const params = envelopeId ? { envelope_id: envelopeId } : {};
      const response = await apiClient.get<LayoutSpec[]>('/layouts/', { params });
      return response.data;
    } catch (error: any) {
      if (ENABLE_MOCK_MODE) {
        console.log('API connection failed, switching to mock mode');
        useMockData = true;
        return generateMockLayouts();
      }
      throw new Error('Failed to fetch layouts');
    }
  }

  /**
   * Get a specific layout by ID
   */
  static async getLayout(layoutId: string): Promise<LayoutSpec> {
    if (useMockData) {
      console.log('Using mock data for fetching layout');
      const mockLayouts = generateMockLayouts();
      const layout = mockLayouts.find(l => l.id === layoutId) || mockLayouts[0];
      return layout;
    }
    
    try {
      const response = await apiClient.get<LayoutSpec>(`/layouts/${layoutId}`);
      return response.data;
    } catch (error: any) {
      if (ENABLE_MOCK_MODE) {
        console.log('API connection failed, switching to mock mode');
        useMockData = true;
        const mockLayouts = generateMockLayouts();
        const layout = mockLayouts.find(l => l.id === layoutId) || mockLayouts[0];
        return layout;
      }
      
      if (error.response?.status === 404) {
        throw new Error('Layout not found');
      }
      throw new Error('Failed to fetch layout');
    }
  }

  /**
   * Update a layout (for manual editing)
   */
  static async updateLayout(layout: LayoutSpec): Promise<LayoutSpec> {
    try {
      const response = await apiClient.put<LayoutSpec>(
        `/layouts/${layout.layoutId}`,
        layout
      );
      return response.data;
    } catch (error: any) {
      throw new Error('Failed to update layout');
    }
  }

  /**
   * Delete a layout
   */
  static async deleteLayout(layoutId: string): Promise<void> {
    try {
      await apiClient.delete(`/layouts/${layoutId}`);
    } catch (error: any) {
      throw new Error('Failed to delete layout');
    }
  }

  /**
   * Get top performing layouts
   */
  static async getTopPerformingLayouts(
    envelopeId?: string,
    limit: number = 10
  ): Promise<LayoutSpec[]> {
    try {
      const params: any = { limit };
      if (envelopeId) params.envelope_id = envelopeId;
      
      const response = await apiClient.get<LayoutSpec[]>('/layouts/search/top-performing', {
        params
      });
      return response.data;
    } catch (error: any) {
      throw new Error('Failed to fetch top performing layouts');
    }
  }

  /**
   * Search layouts by score range
   */
  static async searchLayoutsByScore(
    minScore?: number,
    maxScore?: number
  ): Promise<LayoutSpec[]> {
    try {
      const params: any = {};
      if (minScore !== undefined) params.min_score = minScore;
      if (maxScore !== undefined) params.max_score = maxScore;
      
      const response = await apiClient.get<LayoutSpec[]>('/layouts/search/score-range', {
        params
      });
      return response.data;
    } catch (error: any) {
      throw new Error('Failed to search layouts by score');
    }
  }
}

// ============================================================================
// ENVELOPE API FUNCTIONS
// ============================================================================

export class EnvelopeAPI {
  /**
   * Create a new envelope
   */
  static async createEnvelope(envelope: EnvelopeSpec): Promise<EnvelopeSpec> {
    try {
      const response = await apiClient.post<EnvelopeSpec>('/envelopes/', envelope);
      return response.data;
    } catch (error: any) {
      throw new Error('Failed to create envelope');
    }
  }

  /**
   * Get all envelopes
   */
  static async getEnvelopes(): Promise<EnvelopeSpec[]> {
    try {
      const response = await apiClient.get<EnvelopeSpec[]>('/envelopes/');
      return response.data;
    } catch (error: any) {
      throw new Error('Failed to fetch envelopes');
    }
  }

  /**
   * Get a specific envelope by ID
   */
  static async getEnvelope(envelopeId: string): Promise<EnvelopeSpec> {
    try {
      const response = await apiClient.get<EnvelopeSpec>(`/envelopes/${envelopeId}`);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        throw new Error('Envelope not found');
      }
      throw new Error('Failed to fetch envelope');
    }
  }

  /**
   * Update an envelope
   */
  static async updateEnvelope(envelope: EnvelopeSpec): Promise<EnvelopeSpec> {
    try {
      const response = await apiClient.put<EnvelopeSpec>(
        `/envelopes/${envelope.id}`,
        envelope
      );
      return response.data;
    } catch (error: any) {
      throw new Error('Failed to update envelope');
    }
  }

  /**
   * Delete an envelope
   */
  static async deleteEnvelope(envelopeId: string): Promise<void> {
    try {
      await apiClient.delete(`/envelopes/${envelopeId}`);
    } catch (error: any) {
      throw new Error('Failed to delete envelope');
    }
  }
}

// ============================================================================
// MODULE LIBRARY API FUNCTIONS
// ============================================================================

export class ModuleAPI {
  /**
   * Get all available modules
   */
  static async getModules(): Promise<any[]> {
    try {
      const response = await apiClient.get('/module-library/');
      return response.data;
    } catch (error: any) {
      throw new Error('Failed to fetch modules');
    }
  }

  /**
   * Get modules by type
   */
  static async getModulesByType(moduleType: string): Promise<any[]> {
    try {
      const response = await apiClient.get(`/module-library/type/${moduleType}`);
      return response.data;
    } catch (error: any) {
      throw new Error('Failed to fetch modules by type');
    }
  }

  /**
   * Search modules
   */
  static async searchModules(query: string): Promise<any[]> {
    try {
      const response = await apiClient.get('/module-library/search', {
        params: { q: query }
      });
      return response.data;
    } catch (error: any) {
      throw new Error('Failed to search modules');
    }
  }
}

// ============================================================================
// HEALTH CHECK
// ============================================================================

export class HealthAPI {
  /**
   * Check API health
   */
  static async checkHealth(): Promise<{ status: string; timestamp: string }> {
    try {
      const response = await apiClient.get('/health/');
      return response.data;
    } catch (error: any) {
      throw new Error('API health check failed');
    }
  }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Check if the API is available
 */
export async function checkAPIConnection(): Promise<boolean> {
  try {
    await HealthAPI.checkHealth();
    return true;
  } catch {
    return false;
  }
}

/**
 * Format API errors for display
 */
export function formatAPIError(error: any): string {
  if (error.response?.data?.detail) {
    return error.response.data.detail;
  }
  if (error.message) {
    return error.message;
  }
  return 'An unexpected error occurred';
}

// Export the main API client for custom requests
export { apiClient };
export default {
  Layout: LayoutAPI,
  Envelope: EnvelopeAPI,
  Module: ModuleAPI,
  Health: HealthAPI,
};