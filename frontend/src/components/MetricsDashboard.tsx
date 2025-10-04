import React, { useState, useMemo, useCallback } from 'react';
import { LayoutSpec, PerformanceMetrics } from '../types';

// ============================================================================
// TYPES
// ============================================================================

interface MetricsDashboardProps {
  layouts: LayoutSpec[];
  selectedLayout?: LayoutSpec | null;
  onLayoutSelect?: (layout: LayoutSpec) => void;
  showComparison?: boolean;
  compactMode?: boolean;
}

interface MetricCardProps {
  title: string;
  value: number;
  unit: string;
  format?: (value: number) => string;
  threshold?: {
    good: number;
    warning: number;
  };
  description?: string;
  trend?: 'up' | 'down' | 'stable';
}

interface MetricComparisonProps {
  layouts: LayoutSpec[];
  metric: keyof PerformanceMetrics;
  onLayoutSelect?: (layout: LayoutSpec) => void;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

const formatters = {
  time: (value: number) => `${value.toFixed(1)}s`,
  mass: (value: number) => `${(value / 1000).toFixed(1)}t`,
  power: (value: number) => `${(value / 1000).toFixed(1)}kW`,
  percentage: (value: number) => `${(value * 100).toFixed(1)}%`,
  ratio: (value: number) => `${(value * 100).toFixed(1)}%`,
  count: (value: number) => value.toString(),
  score: (value: number) => `${(value * 100).toFixed(0)}%`,
};

const getMetricColor = (value: number, threshold?: { good: number; warning: number }) => {
  if (!threshold) return 'text-gray-300';
  
  if (value >= threshold.good) return 'text-green-400';
  if (value >= threshold.warning) return 'text-yellow-400';
  return 'text-red-400';
};

const getMetricBgColor = (value: number, threshold?: { good: number; warning: number }) => {
  if (!threshold) return 'bg-gray-700';
  
  if (value >= threshold.good) return 'bg-green-900/30';
  if (value >= threshold.warning) return 'bg-yellow-900/30';
  return 'bg-red-900/30';
};

// ============================================================================
// METRIC CARD COMPONENT
// ============================================================================

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  format = (v) => v.toFixed(1),
  threshold,
  description,
  trend
}) => {
  const colorClass = getMetricColor(value, threshold);
  const bgColorClass = getMetricBgColor(value, threshold);

  const trendIcon = {
    up: '↗',
    down: '↘',
    stable: '→'
  };

  return (
    <div className={`p-4 rounded-lg border border-gray-600 ${bgColorClass}`}>
      <div className="flex justify-between items-start mb-2">
        <h4 className="text-sm font-medium text-gray-300">{title}</h4>
        {trend && (
          <span className={`text-sm ${
            trend === 'up' ? 'text-green-400' : 
            trend === 'down' ? 'text-red-400' : 
            'text-gray-400'
          }`}>
            {trendIcon[trend]}
          </span>
        )}
      </div>
      
      <div className="flex items-baseline space-x-2">
        <span className={`text-2xl font-bold ${colorClass}`}>
          {format(value)}
        </span>
        <span className="text-sm text-gray-400">{unit}</span>
      </div>
      
      {description && (
        <p className="text-xs text-gray-400 mt-2">{description}</p>
      )}
      
      {threshold && (
        <div className="mt-3">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Poor</span>
            <span>Good</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-1">
            <div 
              className={`h-1 rounded-full transition-all duration-300 ${
                value >= threshold.good ? 'bg-green-400' :
                value >= threshold.warning ? 'bg-yellow-400' :
                'bg-red-400'
              }`}
              style={{ 
                width: `${Math.min(100, Math.max(0, (value / (threshold.good * 1.2)) * 100))}%` 
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// METRIC COMPARISON COMPONENT
// ============================================================================

const MetricComparison: React.FC<MetricComparisonProps> = ({
  layouts,
  metric,
  onLayoutSelect
}) => {
  const metricData = useMemo(() => {
    return layouts.map((layout, index) => ({
      layout,
      value: layout.kpis[metric] as number,
      index
    })).filter(item => item.value !== undefined);
  }, [layouts, metric]);

  const sortedData = useMemo(() => {
    // Sort based on metric type (higher is better for scores/margins, lower for times/utilization)
    const isHigherBetter = ['thermalMargin', 'lssMargin', 'connectivityScore', 'safetyScore', 'efficiencyScore'].includes(metric);
    
    return [...metricData].sort((a, b) => 
      isHigherBetter ? b.value - a.value : a.value - b.value
    );
  }, [metricData, metric]);

  const getMetricInfo = (metric: keyof PerformanceMetrics) => {
    const metricConfig = {
      meanTransitTime: { label: 'Transit Time', unit: 's', format: formatters.time },
      egressTime: { label: 'Egress Time', unit: 's', format: formatters.time },
      massTotal: { label: 'Total Mass', unit: 't', format: formatters.mass },
      powerBudget: { label: 'Power Budget', unit: 'kW', format: formatters.power },
      thermalMargin: { label: 'Thermal Margin', unit: '%', format: formatters.percentage },
      lssMargin: { label: 'LSS Margin', unit: '%', format: formatters.percentage },
      stowageUtilization: { label: 'Stowage Util', unit: '%', format: formatters.ratio },
      connectivityScore: { label: 'Connectivity', unit: '%', format: formatters.score },
      safetyScore: { label: 'Safety Score', unit: '%', format: formatters.score },
      efficiencyScore: { label: 'Efficiency', unit: '%', format: formatters.score },
      volumeUtilization: { label: 'Volume Util', unit: '%', format: formatters.ratio },
    };
    
    return metricConfig[metric] || { label: metric, unit: '', format: formatters.count };
  };

  const metricInfo = getMetricInfo(metric);

  if (sortedData.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8">
        No data available for {metricInfo.label}
      </div>
    );
  }

  const bestValue = sortedData[0].value;
  const worstValue = sortedData[sortedData.length - 1].value;

  return (
    <div className="space-y-3">
      <h4 className="text-lg font-semibold text-white mb-4">{metricInfo.label} Comparison</h4>
      
      {sortedData.map((item, index) => {
        const isFirst = index === 0;
        const isLast = index === sortedData.length - 1;
        const percentage = worstValue === bestValue ? 100 : 
          ((item.value - worstValue) / (bestValue - worstValue)) * 100;

        return (
          <div
            key={item.layout.layoutId}
            className={`p-3 rounded-lg border cursor-pointer transition-all duration-200 ${
              isFirst ? 'border-green-500 bg-green-900/20' :
              isLast ? 'border-red-500 bg-red-900/20' :
              'border-gray-600 bg-gray-800 hover:bg-gray-700'
            }`}
            onClick={() => onLayoutSelect?.(item.layout)}
          >
            <div className="flex justify-between items-center">
              <div className="flex items-center space-x-3">
                <div className={`w-3 h-3 rounded-full ${
                  isFirst ? 'bg-green-400' :
                  isLast ? 'bg-red-400' :
                  'bg-gray-400'
                }`} />
                <span className="text-white font-medium">
                  Layout {item.index + 1}
                </span>
                {isFirst && <span className="text-xs text-green-400 font-medium">BEST</span>}
                {isLast && <span className="text-xs text-red-400 font-medium">WORST</span>}
              </div>
              
              <div className="text-right">
                <div className={`text-lg font-bold ${
                  isFirst ? 'text-green-400' :
                  isLast ? 'text-red-400' :
                  'text-gray-300'
                }`}>
                  {metricInfo.format(item.value)}
                </div>
                <div className="text-xs text-gray-400">{metricInfo.unit}</div>
              </div>
            </div>
            
            {/* Progress bar */}
            <div className="mt-2">
              <div className="w-full bg-gray-700 rounded-full h-1">
                <div 
                  className={`h-1 rounded-full transition-all duration-300 ${
                    isFirst ? 'bg-green-400' :
                    isLast ? 'bg-red-400' :
                    'bg-gray-400'
                  }`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ============================================================================
// MAIN METRICS DASHBOARD COMPONENT
// ============================================================================

export const MetricsDashboard: React.FC<MetricsDashboardProps> = ({
  layouts,
  selectedLayout,
  onLayoutSelect,
  showComparison = false,
  compactMode = false
}) => {
  const [selectedMetric, setSelectedMetric] = useState<keyof PerformanceMetrics>('meanTransitTime');
  const [viewMode, setViewMode] = useState<'overview' | 'comparison' | 'details'>('overview');

  const metrics = useMemo(() => {
    if (!selectedLayout) return null;
    
    const kpis = selectedLayout.kpis;
    
    return [
      {
        key: 'meanTransitTime',
        title: 'Mean Transit Time',
        value: kpis.meanTransitTime,
        unit: 'seconds',
        format: formatters.time,
        threshold: { good: 60, warning: 120 },
        description: 'Average time to travel between modules'
      },
      {
        key: 'egressTime',
        title: 'Emergency Egress Time',
        value: kpis.egressTime,
        unit: 'seconds',
        format: formatters.time,
        threshold: { good: 180, warning: 300 },
        description: 'Maximum time to reach nearest airlock'
      },
      {
        key: 'massTotal',
        title: 'Total Mass',
        value: kpis.massTotal,
        unit: 'tonnes',
        format: formatters.mass,
        description: 'Combined mass of all modules'
      },
      {
        key: 'powerBudget',
        title: 'Power Budget',
        value: kpis.powerBudget,
        unit: 'kilowatts',
        format: formatters.power,
        description: 'Total power consumption'
      },
      {
        key: 'thermalMargin',
        title: 'Thermal Margin',
        value: kpis.thermalMargin,
        unit: 'percentage',
        format: formatters.percentage,
        threshold: { good: 0.2, warning: 0.1 },
        description: 'Available thermal management capacity'
      },
      {
        key: 'lssMargin',
        title: 'Life Support Margin',
        value: kpis.lssMargin,
        unit: 'percentage',
        format: formatters.percentage,
        threshold: { good: 0.3, warning: 0.2 },
        description: 'Life support system capacity margin'
      },
      {
        key: 'stowageUtilization',
        title: 'Stowage Utilization',
        value: kpis.stowageUtilization,
        unit: 'percentage',
        format: formatters.ratio,
        threshold: { good: 0.8, warning: 0.9 },
        description: 'Storage space utilization'
      }
    ];
  }, [selectedLayout]);

  const overallScore = useMemo(() => {
    if (!selectedLayout) return 0;
    
    // Calculate a weighted overall score
    const kpis = selectedLayout.kpis;
    const scores = [
      kpis.safetyScore || 0.8,
      kpis.efficiencyScore || 0.7,
      kpis.connectivityScore || 0.8
    ];
    
    return scores.reduce((sum, score) => sum + score, 0) / scores.length;
  }, [selectedLayout]);

  const criticalIssues = useMemo(() => {
    if (!selectedLayout) return [];
    
    const issues = [];
    const kpis = selectedLayout.kpis;
    
    if (kpis.thermalMargin < 0.1) {
      issues.push('Low thermal margin - cooling system may be inadequate');
    }
    if (kpis.lssMargin < 0.2) {
      issues.push('Low LSS margin - life support capacity may be insufficient');
    }
    if (kpis.stowageUtilization > 1.0) {
      issues.push('Stowage overcrowding - insufficient storage capacity');
    }
    if (kpis.egressTime > 300) {
      issues.push('Excessive egress time - emergency evacuation may be compromised');
    }
    if (kpis.meanTransitTime > 180) {
      issues.push('High transit times - operational efficiency may be impacted');
    }
    
    return issues;
  }, [selectedLayout]);

  const availableMetrics: Array<{ key: keyof PerformanceMetrics; label: string }> = [
    { key: 'meanTransitTime', label: 'Transit Time' },
    { key: 'egressTime', label: 'Egress Time' },
    { key: 'massTotal', label: 'Total Mass' },
    { key: 'powerBudget', label: 'Power Budget' },
    { key: 'thermalMargin', label: 'Thermal Margin' },
    { key: 'lssMargin', label: 'LSS Margin' },
    { key: 'stowageUtilization', label: 'Stowage Utilization' },
  ];

  if (compactMode && selectedLayout) {
    return (
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-white">Performance Metrics</h3>
          <div className={`text-2xl font-bold ${
            overallScore >= 0.8 ? 'text-green-400' :
            overallScore >= 0.6 ? 'text-yellow-400' :
            'text-red-400'
          }`}>
            {(overallScore * 100).toFixed(0)}%
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-3">
          {metrics?.slice(0, 4).map((metric) => (
            <div key={metric.key} className="text-sm">
              <div className="text-gray-400">{metric.title}</div>
              <div className={`font-medium ${getMetricColor(metric.value, metric.threshold)}`}>
                {metric.format(metric.value)}
              </div>
            </div>
          ))}
        </div>
        
        {criticalIssues.length > 0 && (
          <div className="mt-4 p-2 bg-red-900/30 border border-red-500 rounded">
            <div className="text-red-400 text-sm font-medium mb-1">Critical Issues:</div>
            <ul className="text-xs text-red-300 space-y-1">
              {criticalIssues.slice(0, 2).map((issue, index) => (
                <li key={index}>• {issue}</li>
              ))}
              {criticalIssues.length > 2 && (
                <li>• +{criticalIssues.length - 2} more issues</li>
              )}
            </ul>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">Performance Dashboard</h2>
        
        {layouts.length > 1 && (
          <div className="flex space-x-2">
            <button
              onClick={() => setViewMode('overview')}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                viewMode === 'overview'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setViewMode('comparison')}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                viewMode === 'comparison'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Compare
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      {viewMode === 'overview' && selectedLayout && (
        <div className="space-y-6">
          {/* Overall Score */}
          <div className="text-center">
            <div className="text-4xl font-bold text-white mb-2">
              Overall Score
            </div>
            <div className={`text-6xl font-bold ${
              overallScore >= 0.8 ? 'text-green-400' :
              overallScore >= 0.6 ? 'text-yellow-400' :
              'text-red-400'
            }`}>
              {(overallScore * 100).toFixed(0)}%
            </div>
            <div className="text-gray-400 mt-2">
              Layout {selectedLayout.layoutId.slice(-8)}
            </div>
          </div>

          {/* Metrics Grid */}
          {metrics && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {metrics.map((metric) => (
                <MetricCard
                  key={metric.key}
                  title={metric.title}
                  value={metric.value}
                  unit={metric.unit}
                  format={metric.format}
                  threshold={metric.threshold}
                  description={metric.description}
                />
              ))}
            </div>
          )}

          {/* Critical Issues */}
          {criticalIssues.length > 0 && (
            <div className="bg-red-900/30 border border-red-500 rounded-lg p-4">
              <h4 className="text-red-400 font-semibold mb-3">Critical Issues</h4>
              <ul className="space-y-2">
                {criticalIssues.map((issue, index) => (
                  <li key={index} className="text-red-300 text-sm flex items-start">
                    <span className="text-red-400 mr-2">•</span>
                    {issue}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {viewMode === 'comparison' && layouts.length > 1 && (
        <div className="space-y-6">
          {/* Metric Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Compare by Metric:
            </label>
            <select
              value={selectedMetric}
              onChange={(e) => setSelectedMetric(e.target.value as keyof PerformanceMetrics)}
              className="bg-gray-700 text-white rounded px-3 py-2"
            >
              {availableMetrics.map(metric => (
                <option key={metric.key} value={metric.key}>
                  {metric.label}
                </option>
              ))}
            </select>
          </div>

          {/* Comparison View */}
          <MetricComparison
            layouts={layouts}
            metric={selectedMetric}
            onLayoutSelect={onLayoutSelect}
          />
        </div>
      )}

      {!selectedLayout && (
        <div className="text-center text-gray-400 py-12">
          <p className="text-xl mb-2">No layout selected</p>
          <p>Select a layout to view performance metrics</p>
        </div>
      )}
    </div>
  );
};

export default MetricsDashboard;