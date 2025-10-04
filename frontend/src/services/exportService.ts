/**
 * Export Service for HabitatCanvas Frontend
 * 
 * Handles exporting layouts and models in various formats
 */

import { api } from './api';

export interface ExportFormat {
  format: string;
  description: string;
  extension: string;
  mime_type: string;
}

export interface SupportedFormats {
  '3d_formats': ExportFormat[];
  'cad_formats': ExportFormat[];
  'data_formats': ExportFormat[];
  'archive_formats': ExportFormat[];
}

export interface ExportPreview {
  layout_id: string;
  format: string;
  estimated_size: string;
  module_count: number;
  envelope_type: string;
  export_timestamp: string;
  includes: string[];
}

export interface BatchExportRequest {
  layout_ids: string[];
  format?: string;
  include_json?: boolean;
}

export class ExportService {
  
  /**
   * Get supported export formats
   */
  async getSupportedFormats(): Promise<SupportedFormats> {
    try {
      const response = await api.get('/export/formats');
      return response.data;
    } catch (error) {
      console.error('Failed to get supported formats:', error);
      throw new Error('Failed to retrieve supported export formats');
    }
  }

  /**
   * Export layout as GLTF/GLB format
   */
  async exportLayoutGLTF(
    layoutId: string,
    options: {
      includeEnvelope?: boolean;
      includeMaterials?: boolean;
    } = {}
  ): Promise<Blob> {
    try {
      const params = new URLSearchParams();
      if (options.includeEnvelope !== undefined) {
        params.append('include_envelope', options.includeEnvelope.toString());
      }
      if (options.includeMaterials !== undefined) {
        params.append('include_materials', options.includeMaterials.toString());
      }

      const response = await api.get(`/export/${layoutId}/gltf?${params.toString()}`, {
        responseType: 'blob'
      });

      return new Blob([response.data], { type: 'model/gltf-binary' });
    } catch (error) {
      console.error('Failed to export layout as GLTF:', error);
      throw new Error('Failed to export layout as GLTF format');
    }
  }

  /**
   * Export layout as JSON specification
   */
  async exportLayoutJSON(layoutId: string): Promise<Blob> {
    try {
      const response = await api.get(`/export/${layoutId}/json`, {
        responseType: 'blob'
      });

      return new Blob([response.data], { type: 'application/json' });
    } catch (error) {
      console.error('Failed to export layout as JSON:', error);
      throw new Error('Failed to export layout as JSON format');
    }
  }

  /**
   * Export layout as STEP CAD format
   */
  async exportLayoutSTEP(layoutId: string): Promise<Blob> {
    try {
      const response = await api.get(`/export/${layoutId}/step`, {
        responseType: 'blob'
      });

      return new Blob([response.data], { type: 'application/step' });
    } catch (error) {
      console.error('Failed to export layout as STEP:', error);
      throw new Error('Failed to export layout as STEP format');
    }
  }

  /**
   * Export layout as IGES CAD format
   */
  async exportLayoutIGES(layoutId: string): Promise<Blob> {
    try {
      const response = await api.get(`/export/${layoutId}/iges`, {
        responseType: 'blob'
      });

      return new Blob([response.data], { type: 'application/iges' });
    } catch (error) {
      console.error('Failed to export layout as IGES:', error);
      throw new Error('Failed to export layout as IGES format');
    }
  }

  /**
   * Export multiple layouts as ZIP archive
   */
  async exportBatchLayouts(request: BatchExportRequest): Promise<Blob> {
    try {
      const params = new URLSearchParams();
      if (request.format) {
        params.append('format', request.format);
      }
      if (request.include_json !== undefined) {
        params.append('include_json', request.include_json.toString());
      }

      const response = await api.post(`/export/batch?${params.toString()}`, request.layout_ids, {
        responseType: 'blob'
      });

      return new Blob([response.data], { type: 'application/zip' });
    } catch (error) {
      console.error('Failed to export batch layouts:', error);
      throw new Error('Failed to export multiple layouts');
    }
  }

  /**
   * Get export preview information
   */
  async getExportPreview(layoutId: string, format: string): Promise<ExportPreview> {
    try {
      const response = await api.get(`/export/${layoutId}/preview`, {
        params: { format }
      });
      return response.data;
    } catch (error) {
      console.error('Failed to get export preview:', error);
      throw new Error('Failed to get export preview');
    }
  }

  /**
   * Download blob as file
   */
  downloadBlob(blob: Blob, filename: string): void {
    try {
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download file:', error);
      throw new Error('Failed to download file');
    }
  }

  /**
   * Export layout with automatic filename generation
   */
  async exportLayoutWithDownload(
    layoutId: string,
    format: string,
    options: {
      includeEnvelope?: boolean;
      includeMaterials?: boolean;
    } = {}
  ): Promise<void> {
    try {
      let blob: Blob;
      let extension: string;

      switch (format.toLowerCase()) {
        case 'gltf':
        case 'glb':
          blob = await this.exportLayoutGLTF(layoutId, options);
          extension = '.glb';
          break;
        case 'json':
          blob = await this.exportLayoutJSON(layoutId);
          extension = '.json';
          break;
        case 'step':
          blob = await this.exportLayoutSTEP(layoutId);
          extension = '.step';
          break;
        case 'iges':
          blob = await this.exportLayoutIGES(layoutId);
          extension = '.iges';
          break;
        default:
          throw new Error(`Unsupported export format: ${format}`);
      }

      const filename = `${layoutId}${extension}`;
      this.downloadBlob(blob, filename);
    } catch (error) {
      console.error('Failed to export and download layout:', error);
      throw error;
    }
  }

  /**
   * Export multiple layouts with automatic filename generation
   */
  async exportBatchLayoutsWithDownload(
    layoutIds: string[],
    format: string = 'glb',
    includeJson: boolean = true
  ): Promise<void> {
    try {
      const blob = await this.exportBatchLayouts({
        layout_ids: layoutIds,
        format,
        include_json: includeJson
      });

      const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
      const filename = `habitat_layouts_${timestamp}.zip`;
      
      this.downloadBlob(blob, filename);
    } catch (error) {
      console.error('Failed to export and download batch layouts:', error);
      throw error;
    }
  }

  /**
   * Validate export request
   */
  validateExportRequest(layoutIds: string[], format?: string): { valid: boolean; errors: string[] } {
    const errors: string[] = [];

    if (!layoutIds || layoutIds.length === 0) {
      errors.push('No layouts selected for export');
    }

    if (layoutIds.length > 50) {
      errors.push('Too many layouts selected (maximum 50)');
    }

    if (format && !['gltf', 'glb', 'json', 'step', 'iges'].includes(format.toLowerCase())) {
      errors.push(`Unsupported export format: ${format}`);
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }

  /**
   * Get file size estimate for export
   */
  async getExportSizeEstimate(layoutIds: string[], format: string): Promise<string> {
    try {
      if (layoutIds.length === 1) {
        const preview = await this.getExportPreview(layoutIds[0], format);
        return preview.estimated_size;
      } else {
        // Estimate for batch export
        const avgSizePerLayout = format === 'json' ? 10 : 50; // KB
        const totalSize = layoutIds.length * avgSizePerLayout;
        
        if (totalSize < 1024) {
          return `${totalSize}KB`;
        } else {
          return `${(totalSize / 1024).toFixed(1)}MB`;
        }
      }
    } catch (error) {
      console.error('Failed to get size estimate:', error);
      return 'Unknown';
    }
  }
}

// Export singleton instance
export const exportService = new ExportService();