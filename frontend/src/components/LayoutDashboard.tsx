import React, { useState, useCallback, useEffect } from 'react';
import { LayoutVisualization } from './LayoutVisualization';
import { LayoutSpec, EnvelopeSpec, MissionParameters, PerformanceMetrics } from '../types';
import { LayoutAPI, formatAPIError, checkAPIConnection } from '../services/api';
import { validateLayoutInEnvelope, getSafePlacementBounds } from '../utils/envelopeValidation';

// ============================================================================
// TYPES
// ============================================================================

interface LayoutDashboardProps {
  envelope: EnvelopeSpec;
  mission: MissionParameters;
  onGenerateLayouts?: (count: number) => Promise<LayoutSpec[]>;
  onLayoutSelect?: (layout: LayoutSpec) => void;
  onLayoutUpdate?: (layout: LayoutSpec) => Promise<LayoutSpec>;
}

interface ApiStatus {
  connected: boolean;
  checking: boolean;
  error?: string;
}

interface LayoutThumbnailProps {
  layout: LayoutSpec;
  envelope: EnvelopeSpec;
  isSelected?: boolean;
  onSelect?: () => void;
  onCompare?: () => void;
}

interface LayoutThumbnailWithActionsProps extends LayoutThumbnailProps {
  onDelete?: () => void;
  apiConnected?: boolean;
}

interface LayoutComparisonProps {
  layouts: LayoutSpec[];
  envelope: EnvelopeSpec;
  onClose?: () => void;
}

// ============================================================================
// LAYOUT THUMBNAIL COMPONENT
// ============================================================================

const LayoutThumbnail: React.FC<LayoutThumbnailProps> = ({
  layout,
  envelope,
  isSelected = false,
  onSelect,
  onCompare
}) => {
  const { kpis } = layout;

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-400';
    if (score >= 0.6) return 'text-yellow-400';
    return 'text-red-400';
  };

  const overallScore = kpis.safetyScore || 0.8; // Fallback calculation

  return (
    <div
      className={`bg-gray-800 rounded-lg p-4 cursor-pointer transition-all duration-200 ${
        isSelected ? 'ring-2 ring-blue-500 bg-gray-700' : 'hover:bg-gray-700'
      }`}
      onClick={onSelect}
    >
      {/* Thumbnail 3D view */}
      <div className="h-32 bg-gray-900 rounded mb-3 relative overflow-hidden">
        <div className="absolute inset-0 scale-75">
          <LayoutVisualization
            layout={layout}
            envelope={envelope}
            viewMode="inspect"
            showMetrics={false}
          />
        </div>
      </div>

      {/* Layout info */}
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <h4 className="font-semibold text-white truncate">
            {layout.metadata?.name || `Layout ${layout.layoutId.slice(-8)}`}
          </h4>
          <span className={`text-sm font-medium ${getScoreColor(overallScore)}`}>
            {(overallScore * 100).toFixed(0)}%
          </span>
        </div>

        {/* Key metrics */}
        <div className="grid grid-cols-2 gap-2 text-xs text-gray-300">
          <div>
            <span className="text-gray-400">Modules:</span> {layout.modules.length}
          </div>
          <div>
            <span className="text-gray-400">Transit:</span> {kpis.meanTransitTime.toFixed(1)}s
          </div>
          <div>
            <span className="text-gray-400">Egress:</span> {kpis.egressTime.toFixed(1)}s
          </div>
          <div>
            <span className="text-gray-400">Mass:</span> {(kpis.massTotal / 1000).toFixed(1)}t
          </div>
        </div>

        {/* Status indicators */}
        <div className="flex space-x-2">
          {kpis.thermalMargin < 0.1 && (
            <span className="px-2 py-1 bg-red-600 text-white text-xs rounded">
              Thermal Risk
            </span>
          )}
          {kpis.lssMargin < 0.2 && (
            <span className="px-2 py-1 bg-orange-600 text-white text-xs rounded">
              LSS Risk
            </span>
          )}
          {kpis.stowageUtilization > 1.0 && (
            <span className="px-2 py-1 bg-yellow-600 text-white text-xs rounded">
              Overcrowded
            </span>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex space-x-2 mt-3">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelect?.();
            }}
            className="flex-1 px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded"
          >
            View
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onCompare?.();
            }}
            className="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded"
          >
            Compare
          </button>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// ENHANCED LAYOUT THUMBNAIL WITH ACTIONS
// ============================================================================

const LayoutThumbnailWithActions: React.FC<LayoutThumbnailWithActionsProps> = ({
  layout,
  envelope,
  isSelected = false,
  onSelect,
  onCompare,
  onDelete,
  apiConnected = false
}) => {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const { kpis } = layout;

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-400';
    if (score >= 0.6) return 'text-yellow-400';
    return 'text-red-400';
  };

  const overallScore = kpis.safetyScore || 0.8; // Fallback calculation

  const handleDelete = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    if (showDeleteConfirm) {
      onDelete?.();
      setShowDeleteConfirm(false);
    } else {
      setShowDeleteConfirm(true);
      // Auto-cancel after 3 seconds
      setTimeout(() => setShowDeleteConfirm(false), 3000);
    }
  }, [showDeleteConfirm, onDelete]);

  return (
    <div
      className={`bg-gray-800 rounded-lg p-4 cursor-pointer transition-all duration-200 ${
        isSelected ? 'ring-2 ring-blue-500 bg-gray-700' : 'hover:bg-gray-700'
      }`}
      onClick={onSelect}
    >
      {/* Thumbnail 3D view */}
      <div className="h-32 bg-gray-900 rounded mb-3 relative overflow-hidden">
        <div className="absolute inset-0 scale-75">
          <LayoutVisualization
            layout={layout}
            envelope={envelope}
            viewMode="inspect"
            showMetrics={false}
          />
        </div>
        
        {/* API status indicator */}
        {!apiConnected && (
          <div className="absolute top-2 right-2 bg-red-600 text-white text-xs px-2 py-1 rounded">
            Offline
          </div>
        )}
      </div>

      {/* Layout info */}
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <h4 className="font-semibold text-white truncate">
            {layout.metadata?.name || `Layout ${layout.layoutId.slice(-8)}`}
          </h4>
          <span className={`text-sm font-medium ${getScoreColor(overallScore)}`}>
            {(overallScore * 100).toFixed(0)}%
          </span>
        </div>

        {/* Key metrics */}
        <div className="grid grid-cols-2 gap-2 text-xs text-gray-300">
          <div>
            <span className="text-gray-400">Modules:</span> {layout.modules.length}
          </div>
          <div>
            <span className="text-gray-400">Transit:</span> {kpis.meanTransitTime.toFixed(1)}s
          </div>
          <div>
            <span className="text-gray-400">Egress:</span> {kpis.egressTime.toFixed(1)}s
          </div>
          <div>
            <span className="text-gray-400">Mass:</span> {(kpis.massTotal / 1000).toFixed(1)}t
          </div>
        </div>

        {/* Status indicators */}
        <div className="flex flex-wrap gap-1">
          {kpis.thermalMargin < 0.1 && (
            <span className="px-2 py-1 bg-red-600 text-white text-xs rounded">
              Thermal Risk
            </span>
          )}
          {kpis.lssMargin < 0.2 && (
            <span className="px-2 py-1 bg-orange-600 text-white text-xs rounded">
              LSS Risk
            </span>
          )}
          {kpis.stowageUtilization > 1.0 && (
            <span className="px-2 py-1 bg-yellow-600 text-white text-xs rounded">
              Overcrowded
            </span>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex space-x-2 mt-3">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelect?.();
            }}
            className="flex-1 px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded"
          >
            View
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onCompare?.();
            }}
            className="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded"
          >
            Compare
          </button>
          {apiConnected && (
            <button
              onClick={handleDelete}
              className={`px-3 py-1 text-white text-sm rounded transition-colors ${
                showDeleteConfirm 
                  ? 'bg-red-600 hover:bg-red-700' 
                  : 'bg-red-800 hover:bg-red-700'
              }`}
              title={showDeleteConfirm ? 'Click again to confirm deletion' : 'Delete layout'}
            >
              {showDeleteConfirm ? '✓ Delete' : '🗑'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// LAYOUT COMPARISON COMPONENT
// ============================================================================

const LayoutComparison: React.FC<LayoutComparisonProps> = ({
  layouts,
  envelope,
  onClose
}) => {
  const [selectedMetric, setSelectedMetric] = useState<keyof PerformanceMetrics>('meanTransitTime');

  const metrics: Array<{ key: keyof PerformanceMetrics; label: string; unit: string; format: (val: number) => string }> = [
    { key: 'meanTransitTime', label: 'Transit Time', unit: 's', format: (val) => val.toFixed(1) },
    { key: 'egressTime', label: 'Egress Time', unit: 's', format: (val) => val.toFixed(1) },
    { key: 'massTotal', label: 'Total Mass', unit: 't', format: (val) => (val / 1000).toFixed(1) },
    { key: 'powerBudget', label: 'Power Budget', unit: 'kW', format: (val) => (val / 1000).toFixed(1) },
    { key: 'thermalMargin', label: 'Thermal Margin', unit: '%', format: (val) => (val * 100).toFixed(1) },
    { key: 'lssMargin', label: 'LSS Margin', unit: '%', format: (val) => (val * 100).toFixed(1) },
    { key: 'stowageUtilization', label: 'Stowage Util', unit: '%', format: (val) => (val * 100).toFixed(1) },
  ];

  const getBestWorstForMetric = (metric: keyof PerformanceMetrics) => {
    const values = layouts.map(layout => layout.kpis[metric] as number).filter(val => val !== undefined);
    if (values.length === 0) return { best: undefined, worst: undefined };

    // For margins, higher is better. For times and utilization, lower is better (except stowage should be around 80%)
    const isHigherBetter = ['thermalMargin', 'lssMargin', 'connectivityScore', 'safetyScore', 'efficiencyScore'].includes(metric);
    
    if (isHigherBetter) {
      return { best: Math.max(...values), worst: Math.min(...values) };
    } else {
      return { best: Math.min(...values), worst: Math.max(...values) };
    }
  };

  const getMetricColor = (layout: LayoutSpec, metric: keyof PerformanceMetrics) => {
    const value = layout.kpis[metric] as number;
    if (value === undefined) return 'text-gray-400';

    const { best, worst } = getBestWorstForMetric(metric);
    if (best === undefined || worst === undefined) return 'text-gray-300';

    if (value === best) return 'text-green-400';
    if (value === worst) return 'text-red-400';
    return 'text-gray-300';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-6 max-w-6xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-white">Layout Comparison</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl"
          >
            ×
          </button>
        </div>

        {/* Metric selector */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Compare by Metric:
          </label>
          <select
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(e.target.value as keyof PerformanceMetrics)}
            className="bg-gray-700 text-white rounded px-3 py-2"
          >
            {metrics.map(metric => (
              <option key={metric.key} value={metric.key}>
                {metric.label}
              </option>
            ))}
          </select>
        </div>

        {/* Comparison table */}
        <div className="overflow-x-auto mb-6">
          <table className="w-full text-sm text-gray-300">
            <thead>
              <tr className="border-b border-gray-600">
                <th className="text-left py-2">Layout</th>
                {metrics.map(metric => (
                  <th key={metric.key} className="text-center py-2">
                    {metric.label}
                    <br />
                    <span className="text-xs text-gray-400">({metric.unit})</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {layouts.map((layout, index) => (
                <tr key={layout.layoutId} className="border-b border-gray-700">
                  <td className="py-2 font-medium">
                    Layout {index + 1}
                    <br />
                    <span className="text-xs text-gray-400">
                      {layout.layoutId.slice(-8)}
                    </span>
                  </td>
                  {metrics.map(metric => {
                    const value = layout.kpis[metric.key] as number;
                    return (
                      <td
                        key={metric.key}
                        className={`text-center py-2 ${getMetricColor(layout, metric.key)}`}
                      >
                        {value !== undefined ? metric.format(value) : 'N/A'}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Visual comparison */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {layouts.map((layout, index) => (
            <div key={layout.layoutId} className="bg-gray-900 rounded-lg p-4">
              <h4 className="text-white font-medium mb-2">Layout {index + 1}</h4>
              <div className="h-48">
                <LayoutVisualization
                  layout={layout}
                  envelope={envelope}
                  viewMode="inspect"
                  showMetrics={false}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// MAIN LAYOUT DASHBOARD COMPONENT
// ============================================================================

export const LayoutDashboard: React.FC<LayoutDashboardProps> = ({
  envelope,
  mission,
  onGenerateLayouts,
  onLayoutSelect,
  onLayoutUpdate
}) => {
  const [layouts, setLayouts] = useState<LayoutSpec[]>([]);
  const [selectedLayout, setSelectedLayout] = useState<LayoutSpec | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [compareLayouts, setCompareLayouts] = useState<LayoutSpec[]>([]);
  const [showComparison, setShowComparison] = useState(false);
  const [generationCount, setGenerationCount] = useState(5);
  const [apiStatus, setApiStatus] = useState<ApiStatus>({ connected: false, checking: true });
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Check API connection on mount
  useEffect(() => {
    const checkConnection = async () => {
      setApiStatus({ connected: false, checking: true });
      try {
        const connected = await checkAPIConnection();
        setApiStatus({ connected, checking: false });
        if (!connected) {
          setError('Cannot connect to backend API. Please check if the server is running.');
        }
      } catch (err) {
        setApiStatus({ connected: false, checking: false, error: 'Connection check failed' });
        setError('Failed to check API connection');
      }
    };

    checkConnection();
  }, []);

  // Load existing layouts for the envelope
  useEffect(() => {
    const loadExistingLayouts = async () => {
      if (!apiStatus.connected) return;
      
      setIsLoading(true);
      try {
        const existingLayouts = await LayoutAPI.getLayouts(envelope.id);
        setLayouts(existingLayouts);
        if (existingLayouts.length > 0 && !selectedLayout) {
          setSelectedLayout(existingLayouts[0]);
          onLayoutSelect?.(existingLayouts[0]);
        }
      } catch (err) {
        console.error('Failed to load existing layouts:', err);
        setError(formatAPIError(err));
      } finally {
        setIsLoading(false);
      }
    };

    loadExistingLayouts();
  }, [envelope.id, apiStatus.connected, selectedLayout, onLayoutSelect]);

  const handleGenerateLayouts = useCallback(async () => {
    if (!apiStatus.connected) {
      setError('Cannot generate layouts: API not connected');
      return;
    }

    setIsGenerating(true);
    setError(null);
    
    try {
      let newLayouts: LayoutSpec[];
      
      if (onGenerateLayouts) {
        // Use custom generation function if provided
        newLayouts = await onGenerateLayouts(generationCount);
      } else {
        // Use API directly
        newLayouts = await LayoutAPI.generateLayouts(envelope, mission, generationCount);
      }
      
      // Validate layouts against envelope
      const validationWarnings: string[] = [];
      for (const layout of newLayouts) {
        const validation = validateLayoutInEnvelope(layout.modules, envelope);
        if (!validation.isValid) {
          validationWarnings.push(`Layout ${layout.layoutId}: ${validation.errors.join(', ')}`);
        }
      }
      
      // Show validation warnings if any
      if (validationWarnings.length > 0) {
        console.warn('Layout validation warnings:', validationWarnings);
        setError(`⚠️ Some modules may extend outside envelope. Try increasing envelope size or regenerating layouts.`);
      }
      
      setLayouts(newLayouts);
      if (newLayouts.length > 0) {
        setSelectedLayout(newLayouts[0]);
        onLayoutSelect?.(newLayouts[0]);
      }
    } catch (err) {
      console.error('Failed to generate layouts:', err);
      setError(formatAPIError(err));
    } finally {
      setIsGenerating(false);
    }
  }, [apiStatus.connected, onGenerateLayouts, generationCount, envelope, mission, onLayoutSelect]);

  const handleLayoutSelect = useCallback((layout: LayoutSpec) => {
    setSelectedLayout(layout);
    onLayoutSelect?.(layout);
  }, [onLayoutSelect]);

  const handleLayoutUpdate = useCallback(async (updatedLayout: LayoutSpec) => {
    if (!apiStatus.connected) {
      setError('Cannot update layout: API not connected');
      return;
    }

    try {
      let savedLayout: LayoutSpec;
      
      if (onLayoutUpdate) {
        // Use custom update function if provided
        savedLayout = await onLayoutUpdate(updatedLayout);
      } else {
        // Use API directly
        savedLayout = await LayoutAPI.updateLayout(updatedLayout);
      }
      
      // Update the layout in the local state
      setLayouts(prev => prev.map(layout => 
        layout.layoutId === savedLayout.layoutId ? savedLayout : layout
      ));
      
      // Update selected layout if it's the one being updated
      if (selectedLayout?.layoutId === savedLayout.layoutId) {
        setSelectedLayout(savedLayout);
      }
      
    } catch (err) {
      console.error('Failed to update layout:', err);
      setError(formatAPIError(err));
    }
  }, [apiStatus.connected, onLayoutUpdate, selectedLayout, setLayouts]);

  const handleDeleteLayout = useCallback(async (layoutId: string) => {
    if (!apiStatus.connected) {
      setError('Cannot delete layout: API not connected');
      return;
    }

    try {
      await LayoutAPI.deleteLayout(layoutId);
      
      // Remove from local state
      setLayouts(prev => prev.filter(layout => layout.layoutId !== layoutId));
      
      // Clear selection if deleted layout was selected
      if (selectedLayout?.layoutId === layoutId) {
        const remainingLayouts = layouts.filter(layout => layout.layoutId !== layoutId);
        setSelectedLayout(remainingLayouts.length > 0 ? remainingLayouts[0] : null);
      }
      
    } catch (err) {
      console.error('Failed to delete layout:', err);
      setError(formatAPIError(err));
    }
  }, [apiStatus.connected, selectedLayout, layouts]);

  const handleAddToComparison = useCallback((layout: LayoutSpec) => {
    setCompareLayouts(prev => {
      if (prev.find(l => l.layoutId === layout.layoutId)) {
        return prev; // Already in comparison
      }
      return [...prev, layout];
    });
  }, []);

  const handleShowComparison = useCallback(() => {
    if (compareLayouts.length > 0) {
      setShowComparison(true);
    }
  }, [compareLayouts]);

  const handleCloseComparison = useCallback(() => {
    setShowComparison(false);
  }, []);

  const sortedLayouts = [...layouts].sort((a, b) => {
    const scoreA = a.kpis.safetyScore || 0.8;
    const scoreB = b.kpis.safetyScore || 0.8;
    return scoreB - scoreA; // Sort by score descending
  });

  return (
    <div className="flex h-full bg-gray-900">
      {/* Sidebar with layout thumbnails */}
      <div className="w-80 bg-gray-800 p-4 overflow-y-auto">
        <div className="mb-6">
          <h2 className="text-xl font-bold text-white mb-4">Generated Layouts</h2>
          
          {/* API Status indicator */}
          <div className="mb-4 p-2 rounded text-sm">
            {apiStatus.checking ? (
              <div className="text-yellow-400">🔄 Checking API connection...</div>
            ) : apiStatus.connected ? (
              <div className="text-green-400">✅ Connected to API</div>
            ) : (
              <div className="text-red-400">❌ API Disconnected</div>
            )}
          </div>

          {/* Envelope Info */}
          <div className="mb-4 p-3 bg-blue-900/30 border border-blue-600/50 rounded text-blue-200 text-sm">
            <div className="font-medium mb-1">📐 Envelope Dimensions:</div>
            <div className="text-xs space-y-1">
              {envelope.type === 'cylinder' && (
                <>
                  <div>Radius: {envelope.params.radius?.toFixed(1) || 5}m</div>
                  <div>Height: {envelope.params.height?.toFixed(1) || 10}m</div>
                </>
              )}
              {envelope.type === 'box' && (
                <>
                  <div>Width: {envelope.params.width?.toFixed(1) || 10}m</div>
                  <div>Depth: {envelope.params.depth?.toFixed(1) || 10}m</div>
                  <div>Height: {envelope.params.height?.toFixed(1) || 10}m</div>
                </>
              )}
              {envelope.type === 'torus' && (
                <>
                  <div>Major Radius: {envelope.params.majorRadius?.toFixed(1) || 10}m</div>
                  <div>Minor Radius: {envelope.params.minorRadius?.toFixed(1) || 2}m</div>
                </>
              )}
              <div className="mt-2 pt-2 border-t border-blue-600/30">
                {getSafePlacementBounds(envelope).description}
              </div>
            </div>
          </div>

          {/* Error display */}
          {error && (
            <div className="mb-4 p-3 bg-red-900 border border-red-600 rounded text-red-200">
              <div className="flex justify-between items-start">
                <div>
                  <strong>Error:</strong> {error}
                </div>
                <button
                  onClick={() => setError(null)}
                  className="text-red-400 hover:text-red-200 ml-2"
                >
                  ×
                </button>
              </div>
            </div>
          )}
          
          {/* Generation controls */}
          <div className="space-y-3 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Number of layouts:
              </label>
              <select
                value={generationCount}
                onChange={(e) => setGenerationCount(Number(e.target.value))}
                className="w-full bg-gray-700 text-white rounded px-3 py-2"
                disabled={isGenerating}
              >
                <option value={3}>3 layouts</option>
                <option value={5}>5 layouts</option>
                <option value={8}>8 layouts</option>
              </select>
            </div>
            
            <button
              onClick={handleGenerateLayouts}
              disabled={isGenerating || !apiStatus.connected}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded font-medium"
            >
              {isGenerating ? 'Generating...' : 
               !apiStatus.connected ? 'API Disconnected' : 
               'Generate Layouts'}
            </button>
          </div>

          {/* Comparison controls */}
          {compareLayouts.length > 0 && (
            <div className="mb-4 p-3 bg-gray-700 rounded">
              <div className="text-sm text-gray-300 mb-2">
                {compareLayouts.length} layout(s) selected for comparison
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={handleShowComparison}
                  className="flex-1 px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded"
                >
                  Compare
                </button>
                <button
                  onClick={() => setCompareLayouts([])}
                  className="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded"
                >
                  Clear
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Layout thumbnails */}
        <div className="space-y-4">
          {isLoading && (
            <div className="text-center text-gray-400 py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
              <p>Loading layouts...</p>
            </div>
          )}
          
          {!isLoading && sortedLayouts.map((layout) => (
            <LayoutThumbnailWithActions
              key={layout.layoutId}
              layout={layout}
              envelope={envelope}
              isSelected={selectedLayout?.layoutId === layout.layoutId}
              onSelect={() => handleLayoutSelect(layout)}
              onCompare={() => handleAddToComparison(layout)}
              onDelete={() => handleDeleteLayout(layout.layoutId)}
              apiConnected={apiStatus.connected}
            />
          ))}
          
          {!isLoading && layouts.length === 0 && !isGenerating && (
            <div className="text-center text-gray-400 py-8">
              <p>No layouts available.</p>
              <p className="text-sm mt-2">
                {apiStatus.connected ? 
                  'Click "Generate Layouts" to start.' : 
                  'Connect to API to load or generate layouts.'
                }
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Main visualization area */}
      <div className="flex-1 relative">
        {selectedLayout ? (
          <LayoutVisualization
            layout={selectedLayout}
            envelope={envelope}
            viewMode="edit"
            showMetrics={true}
            onLayoutChange={handleLayoutUpdate}
            snapToGrid={true}
            gridSize={0.5}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <p className="text-xl mb-2">No layout selected</p>
              <p>
                {apiStatus.connected ? 
                  'Generate layouts and select one to view' : 
                  'Connect to API to load layouts'
                }
              </p>
              {!apiStatus.connected && (
                <button
                  onClick={() => window.location.reload()}
                  className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
                >
                  Retry Connection
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Comparison modal */}
      {showComparison && (
        <LayoutComparison
          layouts={compareLayouts}
          envelope={envelope}
          onClose={handleCloseComparison}
        />
      )}
    </div>
  );
};

export default LayoutDashboard;