import React, { useState, useCallback } from 'react'
import { VolumeBuilder, MissionParametersComponent, LayoutDashboard, PlanetaryComputerPanel } from './components'
import { EnvelopeSpec, MissionParameters, LayoutSpec } from './types'
import { LayoutAPI } from './services/api'

function App() {
  const [currentEnvelope, setCurrentEnvelope] = useState<EnvelopeSpec | null>(null);
  const [currentMission, setCurrentMission] = useState<MissionParameters | null>(null);
  const [activeTab, setActiveTab] = useState<'volume' | 'mission' | 'layouts' | 'planetary'>('volume');

  const handleVolumeChange = useCallback((envelope: EnvelopeSpec) => {
    setCurrentEnvelope(envelope);
    console.log('Volume updated:', envelope);
  }, []);

  const handleMissionChange = useCallback((mission: MissionParameters) => {
    setCurrentMission(mission);
    console.log('Mission updated:', mission);
  }, []);

  const handleGenerateLayouts = useCallback(async (count: number): Promise<LayoutSpec[]> => {
    if (!currentEnvelope || !currentMission) {
      throw new Error('Please define both envelope and mission parameters first');
    }

    try {
      const layouts = await LayoutAPI.generateLayouts(currentEnvelope, currentMission, count);
      return layouts;
    } catch (error) {
      console.error('Failed to generate layouts:', error);
      throw error;
    }
  }, [currentEnvelope, currentMission]);

  const handleLayoutSelect = useCallback((layout: LayoutSpec) => {
    console.log('Layout selected:', layout);
  }, []);

  const canGenerateLayouts = currentEnvelope && currentMission;

  return (
    <div className="w-full h-screen bg-gray-900">
      <header className="bg-gray-800 text-white p-4">
        <h1 className="text-2xl font-bold">HabitatCanvas</h1>
        <p className="text-gray-300">Generative Layout Studio for Space Habitats</p>
        
        {/* Tab Navigation */}
        <div className="flex space-x-4 mt-4">
          <button
            data-testid="volume-tab"
            onClick={() => setActiveTab('volume')}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              activeTab === 'volume'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Volume Builder
          </button>
          <button
            data-testid="mission-tab"
            onClick={() => setActiveTab('mission')}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              activeTab === 'mission'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Mission Parameters
          </button>
          <button
            data-testid="layouts-tab"
            onClick={() => setActiveTab('layouts')}
            disabled={!canGenerateLayouts}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              activeTab === 'layouts'
                ? 'bg-blue-600 text-white'
                : canGenerateLayouts
                ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                : 'bg-gray-800 text-gray-500 cursor-not-allowed'
            }`}
          >
            Layout Generation
            {!canGenerateLayouts && (
              <span className="ml-2 text-xs">(Define envelope & mission first)</span>
            )}
          </button>
          <button
            data-testid="planetary-tab"
            onClick={() => setActiveTab('planetary')}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              activeTab === 'planetary'
                ? 'bg-green-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            🌍 Planetary Computer
          </button>
        </div>
      </header>
      
      <main className="h-[calc(100vh-140px)]">
        {activeTab === 'volume' && (
          <VolumeBuilder 
            onVolumeChange={handleVolumeChange}
            initialVolume={currentEnvelope || undefined}
          />
        )}
        {activeTab === 'mission' && (
          <div className="h-full overflow-y-auto p-6">
            <MissionParametersComponent 
              onMissionChange={handleMissionChange}
              initialMission={currentMission || undefined}
            />
          </div>
        )}
        {activeTab === 'layouts' && currentEnvelope && currentMission && (
          <LayoutDashboard
            envelope={currentEnvelope}
            mission={currentMission}
            onGenerateLayouts={handleGenerateLayouts}
            onLayoutSelect={handleLayoutSelect}
          />
        )}
        {activeTab === 'planetary' && (
          <PlanetaryComputerPanel />
        )}
      </main>
    </div>
  )
}

export default App