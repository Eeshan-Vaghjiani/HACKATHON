/**
 * Export Dialog Component
 * 
 * Provides UI for exporting layouts in various formats
 */

import React, { useState, useEffect } from 'react';
import { exportService, ExportFormat, SupportedFormats, ExportPreview } from '../services/exportService';

interface ExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  layoutIds: string[];
  layoutNames?: Record<string, string>;
}

interface ExportOptions {
  format: string;
  includeEnvelope: boolean;
  includeMaterials: boolean;
  includeJson: boolean;
}

export const ExportDialog: React.FC<ExportDialogProps> = ({
  isOpen,
  onClose,
  layoutIds,
  layoutNames = {}
}) => {
  const [supportedFormats, setSupportedFormats] = useState<SupportedFormats | null>(null);
  const [selectedFormat, setSelectedFormat] = useState<string>('glb');
  const [exportOptions, setExportOptions] = useState<ExportOptions>({
    format: 'glb',
    includeEnvelope: true,
    includeMaterials: true,
    includeJson: true
  });
  const [isExporting, setIsExporting] = useState(false);
  const [exportPreview, setExportPreview] = useState<ExportPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sizeEstimate, setSizeEstimate] = useState<string>('Calculating...');

  // Load supported formats on mount
  useEffect(() => {
    const loadFormats = async () => {
      try {
        const formats = await exportService.getSupportedFormats();
        setSupportedFormats(formats);
      } catch (err) {
        setError('Failed to load export formats');
        console.error('Failed to load formats:', err);
      }
    };

    if (isOpen) {
      loadFormats();
    }
  }, [isOpen]);

  // Update preview when format or layouts change
  useEffect(() => {
    const updatePreview = async () => {
      if (!layoutIds.length || !selectedFormat) return;

      try {
        if (layoutIds.length === 1) {
          const preview = await exportService.getExportPreview(layoutIds[0], selectedFormat);
          setExportPreview(preview);
        } else {
          setExportPreview(null);
        }

        const estimate = await exportService.getExportSizeEstimate(layoutIds, selectedFormat);
        setSizeEstimate(estimate);
      } catch (err) {
        console.error('Failed to update preview:', err);
        setSizeEstimate('Unknown');
      }
    };

    if (isOpen) {
      updatePreview();
    }
  }, [isOpen, layoutIds, selectedFormat]);

  const handleFormatChange = (format: string) => {
    setSelectedFormat(format);
    setExportOptions(prev => ({ ...prev, format }));
  };

  const handleExport = async () => {
    if (!layoutIds.length) {
      setError('No layouts selected');
      return;
    }

    // Validate export request
    const validation = exportService.validateExportRequest(layoutIds, selectedFormat);
    if (!validation.valid) {
      setError(validation.errors.join(', '));
      return;
    }

    setIsExporting(true);
    setError(null);

    try {
      if (layoutIds.length === 1) {
        // Single layout export
        await exportService.exportLayoutWithDownload(
          layoutIds[0],
          selectedFormat,
          {
            includeEnvelope: exportOptions.includeEnvelope,
            includeMaterials: exportOptions.includeMaterials
          }
        );
      } else {
        // Batch export
        await exportService.exportBatchLayoutsWithDownload(
          layoutIds,
          selectedFormat,
          exportOptions.includeJson
        );
      }

      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
      console.error('Export failed:', err);
    } finally {
      setIsExporting(false);
    }
  };

  const renderFormatOptions = () => {
    if (!supportedFormats) return null;

    const allFormats = [
      ...supportedFormats['3d_formats'],
      ...supportedFormats.cad_formats,
      ...supportedFormats.data_formats
    ];

    return (
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">Export Format</label>
        <select
          value={selectedFormat}
          onChange={(e) => handleFormatChange(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={isExporting}
        >
          {allFormats.map((format) => (
            <option key={format.format} value={format.format}>
              {format.format.toUpperCase()} - {format.description}
            </option>
          ))}
        </select>
      </div>
    );
  };

  const renderExportOptions = () => {
    const is3DFormat = ['gltf', 'glb'].includes(selectedFormat);
    const isBatchExport = layoutIds.length > 1;

    return (
      <div className="space-y-3">
        <label className="block text-sm font-medium text-gray-700">Export Options</label>
        
        {is3DFormat && (
          <>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportOptions.includeEnvelope}
                onChange={(e) => setExportOptions(prev => ({ 
                  ...prev, 
                  includeEnvelope: e.target.checked 
                }))}
                disabled={isExporting}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Include habitat envelope</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportOptions.includeMaterials}
                onChange={(e) => setExportOptions(prev => ({ 
                  ...prev, 
                  includeMaterials: e.target.checked 
                }))}
                disabled={isExporting}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Include material definitions</span>
            </label>
          </>
        )}

        {isBatchExport && (
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={exportOptions.includeJson}
              onChange={(e) => setExportOptions(prev => ({ 
                ...prev, 
                includeJson: e.target.checked 
              }))}
              disabled={isExporting}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Include JSON specifications</span>
          </label>
        )}
      </div>
    );
  };

  const renderPreviewInfo = () => {
    if (layoutIds.length === 1 && exportPreview) {
      return (
        <div className="bg-gray-50 p-3 rounded-md">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Export Preview</h4>
          <div className="text-sm text-gray-600 space-y-1">
            <div>Modules: {exportPreview.module_count}</div>
            <div>Envelope: {exportPreview.envelope_type}</div>
            <div>Estimated size: {exportPreview.estimated_size}</div>
            <div className="mt-2">
              <div className="font-medium">Includes:</div>
              <ul className="list-disc list-inside ml-2">
                {exportPreview.includes.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      );
    }

    if (layoutIds.length > 1) {
      return (
        <div className="bg-gray-50 p-3 rounded-md">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Batch Export Info</h4>
          <div className="text-sm text-gray-600 space-y-1">
            <div>Layouts: {layoutIds.length}</div>
            <div>Estimated size: {sizeEstimate}</div>
            <div>Format: ZIP archive</div>
          </div>
        </div>
      );
    }

    return null;
  };

  const renderLayoutList = () => {
    if (layoutIds.length <= 3) {
      return (
        <div className="text-sm text-gray-600">
          <div className="font-medium mb-1">Selected layouts:</div>
          {layoutIds.map(id => (
            <div key={id} className="ml-2">
              • {layoutNames[id] || id}
            </div>
          ))}
        </div>
      );
    }

    return (
      <div className="text-sm text-gray-600">
        <div className="font-medium mb-1">
          Selected layouts: {layoutIds.length}
        </div>
        <div className="ml-2">
          • {layoutNames[layoutIds[0]] || layoutIds[0]}
          • {layoutNames[layoutIds[1]] || layoutIds[1]}
          {layoutIds.length > 2 && (
            <div>• ... and {layoutIds.length - 2} more</div>
          )}
        </div>
      </div>
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Export Layouts</h2>
            <button
              onClick={onClose}
              disabled={isExporting}
              className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-4">
            {renderLayoutList()}
            {renderFormatOptions()}
            {renderExportOptions()}
            {renderPreviewInfo()}

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                <div className="text-sm text-red-600">{error}</div>
              </div>
            )}

            <div className="flex justify-end space-x-3 pt-4 border-t">
              <button
                onClick={onClose}
                disabled={isExporting}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleExport}
                disabled={isExporting || !layoutIds.length}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
              >
                {isExporting && (
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                )}
                <span>{isExporting ? 'Exporting...' : 'Export'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};