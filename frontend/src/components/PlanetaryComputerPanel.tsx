import React, { useState, useCallback } from 'react';
import { apiClient } from '../services/api';

interface SiteAnalysis {
  location: [number, number];
  elevation_m: number;
  slope_degrees: number;
  temperature_range_c: [number, number];
  precipitation_mm_year: number;
  vegetation_index: number;
  terrain_roughness: number;
  solar_irradiance_kwh_m2_day: number;
  accessibility_score: number;
  environmental_hazards: string[];
  suitability_score: number;
  analysis_timestamp: string;
  data_sources: string[];
}

interface OptimalSite {
  site_id: string;
  name: string;
  coordinates: [number, number];
  site_analysis: SiteAnalysis;
  mission_suitability: Record<string, number>;
  risk_assessment: Record<string, number>;
  recommended_habitat_config: Record<string, string>;
  ranking: number;
}

interface EnvironmentalOptimization {
  site_coordinates: [number, number];
  mission_duration_days: number;
  seasonal_data: Record<string, any>;
  lss_optimization: Record<string, any>;
  environmental_constraints: Record<string, number>;
  recommended_systems: Record<string, any>;
  optimization_confidence: number;
}

export const PlanetaryComputerPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'analyze' | 'find-sites' | 'optimize'>('analyze');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Site Analysis State
  const [siteCoords, setSiteCoords] = useState({ latitude: 34.5, longitude: -118.2 });
  const [analysisRadius, setAnalysisRadius] = useState(10);
  const [missionType, setMissionType] = useState('mars_analog');
  const [siteAnalysis, setSiteAnalysis] = useState<SiteAnalysis | null>(null);
  
  // Optimal Sites State
  const [regionBounds, setRegionBounds] = useState({
    min_lat: 34.0, min_lon: -119.0, max_lat: 35.0, max_lon: -117.0
  });
  const [numSites, setNumSites] = useState(5);
  const [optimalSites, setOptimalSites] = useState<OptimalSite[]>([]);
  
  // Environmental Optimization State
  const [optimizationCoords, setOptimizationCoords] = useState({ latitude: 34.5, longitude: -118.2 });
  const [missionDuration, setMissionDuration] = useState(500);
  const [environmentalData, setEnvironmentalData] = useState<EnvironmentalOptimization | null>(null);

  const analyzeSite = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.post('/planetary-computer/analyze-site', {
        latitude: siteCoords.latitude,
        longitude: siteCoords.longitude,
        radius_km: analysisRadius,
        mission_type: missionType
      });
      
      setSiteAnalysis(response.data);
    } catch (err: any) {
      setError(`Site analysis failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  }, [siteCoords, analysisRadius, missionType]);

  const findOptimalSites = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.post('/planetary-computer/find-optimal-sites', {
        region_bounds: [regionBounds.min_lat, regionBounds.min_lon, regionBounds.max_lat, regionBounds.max_lon],
        mission_type: missionType,
        num_sites: numSites
      });
      
      setOptimalSites(response.data);
    } catch (err: any) {
      setError(`Optimal site finding failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  }, [regionBounds, missionType, numSites]);

  const getEnvironmentalOptimization = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.post('/planetary-computer/environmental-optimization', {
        latitude: optimizationCoords.latitude,
        longitude: optimizationCoords.longitude,
        mission_duration_days: missionDuration,
        habitat_type: 'standard'
      });
      
      setEnvironmentalData(response.data);
    } catch (err: any) {
      setError(`Environmental optimization failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  }, [optimizationCoords, missionDuration]);

  const renderSiteAnalysisTab = () => (
    <div className="space-y-6">
      <div className="bg-gray-800 p-4 rounded-lg">
        <h3 className="text-lg font-semibold text-white mb-4">Site Analysis Parameters</h3>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Latitude</label>
            <input
              type="number"
              value={siteCoords.latitude}
              onChange={(e) => setSiteCoords(prev => ({ ...prev, latitude: parseFloat(e.target.value) }))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
              step="0.001"
              min="-90"
              max="90"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Longitude</label>
            <input
              type="number"
              value={siteCoords.longitude}
              onChange={(e) => setSiteCoords(prev => ({ ...prev, longitude: parseFloat(e.target.value) }))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
              step="0.001"
              min="-180"
              max="180"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Analysis Radius (km)</label>
            <input
              type="number"
              value={analysisRadius}
              onChange={(e) => setAnalysisRadius(parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
              min="1"
              max="100"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Mission Type</label>
            <select
              value={missionType}
              onChange={(e) => setMissionType(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
            >
              <option value="mars_analog">Mars Analog</option>
              <option value="lunar_analog">Lunar Analog</option>
              <option value="earth_base">Earth Base</option>
            </select>
          </div>
        </div>
        
        <button
          onClick={analyzeSite}
          disabled={loading}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Analyzing...' : 'Analyze Site'}
        </button>
      </div>

      {siteAnalysis && (
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-lg font-semibold text-white mb-4">Site Analysis Results</h3>
          
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-300">Elevation:</span>
                <span className="text-white">{siteAnalysis.elevation_m.toFixed(1)} m</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Slope:</span>
                <span className="text-white">{siteAnalysis.slope_degrees.toFixed(1)}°</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Temperature Range:</span>
                <span className="text-white">{siteAnalysis.temperature_range_c[0]}°C to {siteAnalysis.temperature_range_c[1]}°C</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Solar Irradiance:</span>
                <span className="text-white">{siteAnalysis.solar_irradiance_kwh_m2_day.toFixed(1)} kWh/m²/day</span>
              </div>
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-300">Precipitation:</span>
                <span className="text-white">{siteAnalysis.precipitation_mm_year} mm/year</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Vegetation Index:</span>
                <span className="text-white">{siteAnalysis.vegetation_index.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Accessibility:</span>
                <span className="text-white">{(siteAnalysis.accessibility_score * 100).toFixed(0)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Suitability Score:</span>
                <span className={`font-semibold ${siteAnalysis.suitability_score > 0.7 ? 'text-green-400' : siteAnalysis.suitability_score > 0.4 ? 'text-yellow-400' : 'text-red-400'}`}>
                  {(siteAnalysis.suitability_score * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
          
          {siteAnalysis.environmental_hazards.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Environmental Hazards:</h4>
              <div className="flex flex-wrap gap-2">
                {siteAnalysis.environmental_hazards.map((hazard, index) => (
                  <span key={index} className="px-2 py-1 bg-red-900/50 text-red-300 text-xs rounded">
                    {hazard.replace('_', ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );

  const renderOptimalSitesTab = () => (
    <div className="space-y-6">
      <div className="bg-gray-800 p-4 rounded-lg">
        <h3 className="text-lg font-semibold text-white mb-4">Find Optimal Sites</h3>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Min Latitude</label>
            <input
              type="number"
              value={regionBounds.min_lat}
              onChange={(e) => setRegionBounds(prev => ({ ...prev, min_lat: parseFloat(e.target.value) }))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
              step="0.1"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Max Latitude</label>
            <input
              type="number"
              value={regionBounds.max_lat}
              onChange={(e) => setRegionBounds(prev => ({ ...prev, max_lat: parseFloat(e.target.value) }))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
              step="0.1"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Min Longitude</label>
            <input
              type="number"
              value={regionBounds.min_lon}
              onChange={(e) => setRegionBounds(prev => ({ ...prev, min_lon: parseFloat(e.target.value) }))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
              step="0.1"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Max Longitude</label>
            <input
              type="number"
              value={regionBounds.max_lon}
              onChange={(e) => setRegionBounds(prev => ({ ...prev, max_lon: parseFloat(e.target.value) }))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
              step="0.1"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Number of Sites</label>
            <input
              type="number"
              value={numSites}
              onChange={(e) => setNumSites(parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
              min="1"
              max="20"
            />
          </div>
        </div>
        
        <button
          onClick={findOptimalSites}
          disabled={loading}
          className="mt-4 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
        >
          {loading ? 'Finding Sites...' : 'Find Optimal Sites'}
        </button>
      </div>

      {optimalSites.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-white">Optimal Landing Sites</h3>
          {optimalSites.map((site) => (
            <div key={site.site_id} className="bg-gray-800 p-4 rounded-lg">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h4 className="text-white font-medium">{site.name}</h4>
                  <p className="text-gray-400 text-sm">
                    {site.coordinates[0].toFixed(3)}, {site.coordinates[1].toFixed(3)}
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-lg font-semibold text-green-400">#{site.ranking}</div>
                  <div className="text-sm text-gray-400">
                    {(site.site_analysis.suitability_score * 100).toFixed(0)}% suitable
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="text-gray-300">Mission Suitability</div>
                  <div className="space-y-1 mt-1">
                    {Object.entries(site.mission_suitability).slice(0, 3).map(([key, value]) => (
                      <div key={key} className="flex justify-between">
                        <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                        <span className="text-white">{(value * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div>
                  <div className="text-gray-300">Risk Assessment</div>
                  <div className="space-y-1 mt-1">
                    {Object.entries(site.risk_assessment).slice(0, 3).map(([key, value]) => (
                      <div key={key} className="flex justify-between">
                        <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                        <span className={`${value < 0.3 ? 'text-green-400' : value < 0.6 ? 'text-yellow-400' : 'text-red-400'}`}>
                          {(value * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div>
                  <div className="text-gray-300">Recommended Config</div>
                  <div className="space-y-1 mt-1">
                    {Object.entries(site.recommended_habitat_config).slice(0, 3).map(([key, value]) => (
                      <div key={key} className="text-xs">
                        <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                        <div className="text-white">{value.replace('_', ' ')}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderEnvironmentalOptimizationTab = () => (
    <div className="space-y-6">
      <div className="bg-gray-800 p-4 rounded-lg">
        <h3 className="text-lg font-semibold text-white mb-4">Environmental Optimization</h3>
        
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Latitude</label>
            <input
              type="number"
              value={optimizationCoords.latitude}
              onChange={(e) => setOptimizationCoords(prev => ({ ...prev, latitude: parseFloat(e.target.value) }))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
              step="0.001"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Longitude</label>
            <input
              type="number"
              value={optimizationCoords.longitude}
              onChange={(e) => setOptimizationCoords(prev => ({ ...prev, longitude: parseFloat(e.target.value) }))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
              step="0.001"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Mission Duration (days)</label>
            <input
              type="number"
              value={missionDuration}
              onChange={(e) => setMissionDuration(parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
              min="30"
              max="2000"
            />
          </div>
        </div>
        
        <button
          onClick={getEnvironmentalOptimization}
          disabled={loading}
          className="mt-4 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50"
        >
          {loading ? 'Optimizing...' : 'Get Environmental Data'}
        </button>
      </div>

      {environmentalData && (
        <div className="space-y-4">
          <div className="bg-gray-800 p-4 rounded-lg">
            <h4 className="text-white font-medium mb-3">Life Support System Optimization</h4>
            
            <div className="grid grid-cols-2 gap-6">
              <div>
                <h5 className="text-gray-300 text-sm font-medium mb-2">Atmospheric Control</h5>
                <div className="space-y-1 text-sm">
                  {Object.entries(environmentalData.lss_optimization.atmospheric_processing).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                      <span className="text-white">{Array.isArray(value) ? `${value[0]} - ${value[1]}` : value}</span>
                    </div>
                  ))}
                </div>
              </div>
              
              <div>
                <h5 className="text-gray-300 text-sm font-medium mb-2">Thermal Management</h5>
                <div className="space-y-1 text-sm">
                  {Object.entries(environmentalData.lss_optimization.thermal_management).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                      <span className="text-white">{Array.isArray(value) ? `${value[0]} - ${value[1]}` : value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
          
          <div className="bg-gray-800 p-4 rounded-lg">
            <h4 className="text-white font-medium mb-3">Recommended Systems</h4>
            
            <div className="grid grid-cols-3 gap-4">
              {Object.entries(environmentalData.recommended_systems).map(([category, systems]) => (
                <div key={category}>
                  <h5 className="text-gray-300 text-sm font-medium mb-2 capitalize">{category.replace('_', ' ')}</h5>
                  <div className="space-y-1 text-sm">
                    {Object.entries(systems as Record<string, any>).map(([key, value]) => (
                      <div key={key}>
                        <span className="text-gray-400 capitalize">{key.replace('_', ' ')}:</span>
                        <div className="text-white">{value.toString().replace('_', ' ')}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            
            <div className="mt-4 pt-4 border-t border-gray-700">
              <div className="flex justify-between items-center">
                <span className="text-gray-300">Optimization Confidence:</span>
                <span className="text-green-400 font-semibold">
                  {(environmentalData.optimization_confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="w-full h-full bg-gray-900 text-white">
      <div className="p-4">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold">Microsoft Planetary Computer</h2>
            <p className="text-gray-400">Earth observation data for habitat site analysis</p>
          </div>
          
          <div className="flex items-center space-x-2 text-sm">
            <div className="w-2 h-2 bg-green-400 rounded-full"></div>
            <span className="text-gray-300">Connected to Planetary Computer</span>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex space-x-4 mb-6">
          <button
            onClick={() => setActiveTab('analyze')}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              activeTab === 'analyze'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Site Analysis
          </button>
          <button
            onClick={() => setActiveTab('find-sites')}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              activeTab === 'find-sites'
                ? 'bg-green-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Find Optimal Sites
          </button>
          <button
            onClick={() => setActiveTab('optimize')}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              activeTab === 'optimize'
                ? 'bg-purple-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Environmental Optimization
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-500 rounded-md text-red-300">
            {error}
          </div>
        )}

        {/* Tab Content */}
        <div className="overflow-y-auto max-h-[calc(100vh-200px)]">
          {activeTab === 'analyze' && renderSiteAnalysisTab()}
          {activeTab === 'find-sites' && renderOptimalSitesTab()}
          {activeTab === 'optimize' && renderEnvironmentalOptimizationTab()}
        </div>
      </div>
    </div>
  );
};