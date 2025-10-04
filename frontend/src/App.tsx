import React, { useState, useCallback } from 'react'
import { VolumeBuilder } from './components'
import { EnvelopeSpec } from './types'

function App() {
  const [currentEnvelope, setCurrentEnvelope] = useState<EnvelopeSpec | null>(null);

  const handleVolumeChange = useCallback((envelope: EnvelopeSpec) => {
    setCurrentEnvelope(envelope);
    console.log('Volume updated:', envelope);
  }, []);

  return (
    <div className="w-full h-screen bg-gray-900">
      <header className="bg-gray-800 text-white p-4">
        <h1 className="text-2xl font-bold">HabitatCanvas</h1>
        <p className="text-gray-300">Generative Layout Studio for Space Habitats</p>
      </header>
      
      <main className="h-[calc(100vh-80px)]">
        <VolumeBuilder 
          onVolumeChange={handleVolumeChange}
          initialVolume={currentEnvelope || undefined}
        />
      </main>
    </div>
  )
}

export default App