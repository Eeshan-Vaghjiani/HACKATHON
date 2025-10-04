import React, { useState, useCallback, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid } from '@react-three/drei';
import { EnvelopeSpec, EnvelopeType, CoordinateFrame, ValidationResult } from '../types';
import { validateEnvelopeSpec } from '../types/validation';
import { 
  calculateCylinderVolume, 
  calculateBoxVolume, 
  calculateTorusVolume 
} from '../types/geometry';
import { VolumePreview } from './VolumePreview';
import { ParameterControls } from './ParameterControls';

interface VolumeBuilderProps {
  onVolumeChange: (envelope: EnvelopeSpec) => void;
  initialVolume?: EnvelopeSpec;
}

export const VolumeBuilder: React.FC<VolumeBuilderProps> = ({
  onVolumeChange,
  initialVolume
}) => {
  // Initialize envelope state
  const [envelope, setEnvelope] = useState<EnvelopeSpec>(
    initialVolume || {
      id: crypto.randomUUID(),
      type: EnvelopeType.CYLINDER,
      params: {
        radius: 3.0,
        length: 12.0
      },
      coordinateFrame: CoordinateFrame.LOCAL,
      metadata: {
        name: 'New Habitat Volume',
        creator: 'User',
        created: new Date()
      }
    }
  );

  // Validation state
  const [validation, setValidation] = useState<ValidationResult>({
    isValid: true,
    errors: [],
    warnings: []
  });

  // Calculate volume based on envelope type and parameters
  const calculatedVolume = useMemo(() => {
    switch (envelope.type) {
      case EnvelopeType.CYLINDER:
        return calculateCylinderVolume(
          envelope.params.radius || 0,
          envelope.params.length || 0
        );
      case EnvelopeType.BOX:
        return calculateBoxVolume(
          envelope.params.width || 0,
          envelope.params.height || 0,
          envelope.params.depth || 0
        );
      case EnvelopeType.TORUS:
        return calculateTorusVolume(
          envelope.params.majorRadius || 0,
          envelope.params.minorRadius || 0
        );
      default:
        return 0;
    }
  }, [envelope.type, envelope.params]);

  // Handle parameter changes
  const handleParameterChange = useCallback((paramName: string, value: number) => {
    const updatedEnvelope = {
      ...envelope,
      params: {
        ...envelope.params,
        [paramName]: value
      }
    };

    // Validate the updated envelope
    const validationResult = validateEnvelopeSpec(updatedEnvelope);
    setValidation(validationResult);

    setEnvelope(updatedEnvelope);
    
    // Only call onVolumeChange if validation passes
    if (validationResult.isValid) {
      onVolumeChange(updatedEnvelope);
    }
  }, [envelope, onVolumeChange]);

  // Handle envelope type change
  const handleTypeChange = useCallback((newType: EnvelopeType) => {
    let defaultParams: Record<string, number> = {};
    
    switch (newType) {
      case EnvelopeType.CYLINDER:
        defaultParams = { radius: 3.0, length: 12.0 };
        break;
      case EnvelopeType.BOX:
        defaultParams = { width: 6.0, height: 6.0, depth: 12.0 };
        break;
      case EnvelopeType.TORUS:
        defaultParams = { majorRadius: 5.0, minorRadius: 2.0 };
        break;
      case EnvelopeType.FREEFORM:
        defaultParams = { complexity: 1.0 };
        break;
    }

    const updatedEnvelope = {
      ...envelope,
      type: newType,
      params: defaultParams
    };

    const validationResult = validateEnvelopeSpec(updatedEnvelope);
    setValidation(validationResult);

    setEnvelope(updatedEnvelope);
    
    if (validationResult.isValid) {
      onVolumeChange(updatedEnvelope);
    }
  }, [envelope, onVolumeChange]);

  // Handle metadata changes
  const handleMetadataChange = useCallback((field: string, value: string) => {
    const updatedEnvelope = {
      ...envelope,
      metadata: {
        ...envelope.metadata,
        [field]: value
      }
    };

    setEnvelope(updatedEnvelope);
    onVolumeChange(updatedEnvelope);
  }, [envelope, onVolumeChange]);

  // Export envelope to JSON
  const handleExport = useCallback(() => {
    const dataStr = JSON.stringify(envelope, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `${envelope.metadata.name.replace(/\s+/g, '_')}_envelope.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  }, [envelope]);

  // Import envelope from JSON file
  const handleImport = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const importedEnvelope = JSON.parse(e.target?.result as string) as EnvelopeSpec;
        
        // Validate imported envelope
        const validationResult = validateEnvelopeSpec(importedEnvelope);
        setValidation(validationResult);

        if (validationResult.isValid) {
          setEnvelope(importedEnvelope);
          onVolumeChange(importedEnvelope);
        }
      } catch (error) {
        console.error('Failed to import envelope:', error);
        setValidation({
          isValid: false,
          errors: [{
            field: 'import',
            message: 'Invalid JSON file format',
            code: 'INVALID_FORMAT'
          }],
          warnings: []
        });
      }
    };
    reader.readAsText(file);
  }, [onVolumeChange]);

  return (
    <div className="flex h-full bg-gray-900">
      {/* Left Panel - Controls */}
      <div className="w-80 bg-gray-800 p-4 overflow-y-auto">
        <div className="space-y-6">
          {/* Header */}
          <div>
            <h2 className="text-xl font-bold text-white mb-2">Volume Builder</h2>
            <p className="text-gray-400 text-sm">
              Define your habitat envelope using parametric primitives
            </p>
          </div>

          {/* Metadata */}
          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-white">Metadata</h3>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Name
              </label>
              <input
                type="text"
                value={envelope.metadata.name}
                onChange={(e) => handleMetadataChange('name', e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Shape Type Selection */}
          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-white">Shape Type</h3>
            <div className="grid grid-cols-2 gap-2">
              {Object.values(EnvelopeType).map((type) => (
                <button
                  key={type}
                  onClick={() => handleTypeChange(type)}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    envelope.type === type
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                  disabled={type === EnvelopeType.FREEFORM} // Disable freeform for now
                >
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Parameter Controls */}
          <ParameterControls
            envelopeType={envelope.type}
            params={envelope.params}
            onParameterChange={handleParameterChange}
            validation={validation}
          />

          {/* Volume Display */}
          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-white">Volume Info</h3>
            <div className="bg-gray-700 p-3 rounded-md">
              <div className="text-sm text-gray-300">
                <div className="flex justify-between">
                  <span>Volume:</span>
                  <span className="font-mono">{calculatedVolume.toFixed(2)} m³</span>
                </div>
                <div className="flex justify-between mt-1">
                  <span>Type:</span>
                  <span className="capitalize">{envelope.type}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Validation Messages */}
          {(!validation.isValid || validation.warnings.length > 0) && (
            <div className="space-y-2">
              {validation.errors.map((error, index) => (
                <div key={index} className="bg-red-900/50 border border-red-500 rounded-md p-2">
                  <p className="text-red-200 text-sm font-medium">{error.message}</p>
                </div>
              ))}
              {validation.warnings.map((warning, index) => (
                <div key={index} className="bg-yellow-900/50 border border-yellow-500 rounded-md p-2">
                  <p className="text-yellow-200 text-sm font-medium">{warning.message}</p>
                </div>
              ))}
            </div>
          )}

          {/* Export/Import */}
          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-white">Export/Import</h3>
            <div className="space-y-2">
              <button
                onClick={handleExport}
                disabled={!validation.isValid}
                className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
              >
                Export JSON
              </button>
              <label className="block">
                <input
                  type="file"
                  accept=".json"
                  onChange={handleImport}
                  className="hidden"
                />
                <div className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 cursor-pointer text-center transition-colors">
                  Import JSON
                </div>
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel - 3D Preview */}
      <div className="flex-1 relative">
        <Canvas camera={{ position: [8, 8, 8], fov: 60 }}>
          <ambientLight intensity={0.4} />
          <pointLight position={[10, 10, 10]} intensity={0.8} />
          <pointLight position={[-10, -10, -10]} intensity={0.3} />
          
          {/* Grid */}
          <Grid 
            args={[20, 20]} 
            cellSize={1} 
            cellThickness={0.5} 
            cellColor="#374151" 
            sectionSize={5} 
            sectionThickness={1} 
            sectionColor="#4b5563" 
          />
          
          {/* Volume Preview */}
          <VolumePreview envelope={envelope} />
          
          <OrbitControls 
            enablePan={true} 
            enableZoom={true} 
            enableRotate={true}
            maxDistance={50}
            minDistance={2}
          />
        </Canvas>
        
        {/* Overlay Info */}
        <div className="absolute top-4 right-4 bg-black/50 backdrop-blur-sm rounded-lg p-3 text-white">
          <div className="text-sm space-y-1">
            <div>Volume: {calculatedVolume.toFixed(2)} m³</div>
            <div className="capitalize">Type: {envelope.type}</div>
            {validation.isValid ? (
              <div className="text-green-400">✓ Valid</div>
            ) : (
              <div className="text-red-400">✗ Invalid</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};