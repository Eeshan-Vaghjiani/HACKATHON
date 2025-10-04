/**
 * Integration test for export functionality
 * This would normally be run with a test runner like Jest or Vitest
 */

import { exportService } from './src/services/exportService';

// Mock API for testing
const mockApi = {
  get: jest.fn(),
  post: jest.fn()
};

// Mock the api import
jest.mock('./src/services/api', () => ({
  api: mockApi
}));

describe('Export Service Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('should get supported formats', async () => {
    const mockFormats = {
      '3d_formats': [
        {
          format: 'glb',
          description: 'GL Transmission Format (binary)',
          extension: '.glb',
          mime_type: 'model/gltf-binary'
        }
      ],
      'cad_formats': [
        {
          format: 'step',
          description: 'Standard for Exchange of Product Data',
          extension: '.step',
          mime_type: 'application/step'
        }
      ],
      'data_formats': [
        {
          format: 'json',
          description: 'Layout specification in JSON format',
          extension: '.json',
          mime_type: 'application/json'
        }
      ],
      'archive_formats': [
        {
          format: 'zip',
          description: 'ZIP archive for batch exports',
          extension: '.zip',
          mime_type: 'application/zip'
        }
      ]
    };

    mockApi.get.mockResolvedValue({ data: mockFormats });

    const formats = await exportService.getSupportedFormats();
    
    expect(mockApi.get).toHaveBeenCalledWith('/export/formats');
    expect(formats).toEqual(mockFormats);
  });

  test('should export layout as GLTF', async () => {
    const mockBlob = new Blob(['mock gltf data'], { type: 'model/gltf-binary' });
    mockApi.get.mockResolvedValue({ data: mockBlob });

    const result = await exportService.exportLayoutGLTF('test-layout-1', {
      includeEnvelope: true,
      includeMaterials: true
    });

    expect(mockApi.get).toHaveBeenCalledWith(
      '/export/test-layout-1/gltf?include_envelope=true&include_materials=true',
      { responseType: 'blob' }
    );
    expect(result).toBeInstanceOf(Blob);
  });

  test('should export batch layouts', async () => {
    const mockBlob = new Blob(['mock zip data'], { type: 'application/zip' });
    mockApi.post.mockResolvedValue({ data: mockBlob });

    const result = await exportService.exportBatchLayouts({
      layout_ids: ['layout-1', 'layout-2'],
      format: 'glb',
      include_json: true
    });

    expect(mockApi.post).toHaveBeenCalledWith(
      '/export/batch?format=glb&include_json=true',
      ['layout-1', 'layout-2'],
      { responseType: 'blob' }
    );
    expect(result).toBeInstanceOf(Blob);
  });

  test('should validate export request', () => {
    // Valid request
    const validResult = exportService.validateExportRequest(['layout-1'], 'glb');
    expect(validResult.valid).toBe(true);
    expect(validResult.errors).toHaveLength(0);

    // Invalid request - no layouts
    const invalidResult1 = exportService.validateExportRequest([], 'glb');
    expect(invalidResult1.valid).toBe(false);
    expect(invalidResult1.errors).toContain('No layouts selected for export');

    // Invalid request - too many layouts
    const tooManyLayouts = Array.from({ length: 51 }, (_, i) => `layout-${i}`);
    const invalidResult2 = exportService.validateExportRequest(tooManyLayouts, 'glb');
    expect(invalidResult2.valid).toBe(false);
    expect(invalidResult2.errors).toContain('Too many layouts selected (maximum 50)');

    // Invalid request - unsupported format
    const invalidResult3 = exportService.validateExportRequest(['layout-1'], 'invalid');
    expect(invalidResult3.valid).toBe(false);
    expect(invalidResult3.errors).toContain('Unsupported export format: invalid');
  });

  test('should get export preview', async () => {
    const mockPreview = {
      layout_id: 'test-layout-1',
      format: 'glb',
      estimated_size: '150KB',
      module_count: 5,
      envelope_type: 'cylinder',
      export_timestamp: '2024-01-01T00:00:00Z',
      includes: [
        '3D geometry for all modules',
        'Habitat envelope geometry',
        'Material definitions',
        'Scene hierarchy'
      ]
    };

    mockApi.get.mockResolvedValue({ data: mockPreview });

    const result = await exportService.getExportPreview('test-layout-1', 'glb');

    expect(mockApi.get).toHaveBeenCalledWith('/export/test-layout-1/preview', {
      params: { format: 'glb' }
    });
    expect(result).toEqual(mockPreview);
  });
});

console.log('Export integration tests defined successfully');