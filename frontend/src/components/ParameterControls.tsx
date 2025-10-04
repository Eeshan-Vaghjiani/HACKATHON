import React from 'react';
import { EnvelopeType, ValidationResult } from '../types';

interface ParameterControlsProps {
  envelopeType: EnvelopeType;
  params: Record<string, number>;
  onParameterChange: (paramName: string, value: number) => void;
  validation: ValidationResult;
}

interface ParameterConfig {
  name: string;
  label: string;
  min: number;
  max: number;
  step: number;
  unit: string;
  description?: string;
}

const PARAMETER_CONFIGS: Record<EnvelopeType, ParameterConfig[]> = {
  [EnvelopeType.CYLINDER]: [
    {
      name: 'radius',
      label: 'Radius',
      min: 0.5,
      max: 10.0,
      step: 0.1,
      unit: 'm',
      description: 'Radius of the cylindrical habitat'
    },
    {
      name: 'length',
      label: 'Length',
      min: 1.0,
      max: 50.0,
      step: 0.5,
      unit: 'm',
      description: 'Length of the cylindrical habitat'
    }
  ],
  [EnvelopeType.BOX]: [
    {
      name: 'width',
      label: 'Width',
      min: 1.0,
      max: 20.0,
      step: 0.5,
      unit: 'm',
      description: 'Width of the box habitat (X-axis)'
    },
    {
      name: 'height',
      label: 'Height',
      min: 1.0,
      max: 20.0,
      step: 0.5,
      unit: 'm',
      description: 'Height of the box habitat (Y-axis)'
    },
    {
      name: 'depth',
      label: 'Depth',
      min: 1.0,
      max: 50.0,
      step: 0.5,
      unit: 'm',
      description: 'Depth of the box habitat (Z-axis)'
    }
  ],
  [EnvelopeType.TORUS]: [
    {
      name: 'majorRadius',
      label: 'Major Radius',
      min: 2.0,
      max: 20.0,
      step: 0.5,
      unit: 'm',
      description: 'Distance from center to tube center'
    },
    {
      name: 'minorRadius',
      label: 'Minor Radius',
      min: 0.5,
      max: 5.0,
      step: 0.1,
      unit: 'm',
      description: 'Radius of the tube cross-section'
    }
  ],
  [EnvelopeType.FREEFORM]: [
    {
      name: 'complexity',
      label: 'Complexity',
      min: 0.1,
      max: 2.0,
      step: 0.1,
      unit: '',
      description: 'Complexity factor for freeform shape'
    }
  ]
};

export const ParameterControls: React.FC<ParameterControlsProps> = ({
  envelopeType,
  params,
  onParameterChange,
  validation
}) => {
  const parameterConfigs = PARAMETER_CONFIGS[envelopeType] || [];

  const getFieldError = (fieldName: string) => {
    return validation.errors.find(error => error.field === fieldName);
  };

  const getFieldWarning = (fieldName: string) => {
    return validation.warnings.find(warning => warning.field === fieldName);
  };

  const handleInputChange = (paramName: string, value: string) => {
    const numericValue = parseFloat(value);
    if (!isNaN(numericValue)) {
      onParameterChange(paramName, numericValue);
    }
  };

  const handleSliderChange = (paramName: string, value: string) => {
    const numericValue = parseFloat(value);
    if (!isNaN(numericValue)) {
      onParameterChange(paramName, numericValue);
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-white">Parameters</h3>
      
      {parameterConfigs.map((config) => {
        const currentValue = params[config.name] || 0;
        const fieldError = getFieldError(config.name);
        const fieldWarning = getFieldWarning(config.name);
        const hasError = !!fieldError;
        const hasWarning = !!fieldWarning;

        return (
          <div key={config.name} className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-300">
                {config.label}
              </label>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  value={currentValue.toFixed(1)}
                  onChange={(e) => handleInputChange(config.name, e.target.value)}
                  min={config.min}
                  max={config.max}
                  step={config.step}
                  className={`w-20 px-2 py-1 text-sm bg-gray-700 border rounded text-white focus:outline-none focus:ring-1 ${
                    hasError
                      ? 'border-red-500 focus:ring-red-500'
                      : hasWarning
                      ? 'border-yellow-500 focus:ring-yellow-500'
                      : 'border-gray-600 focus:ring-blue-500'
                  }`}
                />
                <span className="text-xs text-gray-400 w-6">{config.unit}</span>
              </div>
            </div>

            {/* Slider */}
            <div className="px-1">
              <input
                type="range"
                value={currentValue}
                onChange={(e) => handleSliderChange(config.name, e.target.value)}
                min={config.min}
                max={config.max}
                step={config.step}
                className={`w-full h-2 rounded-lg appearance-none cursor-pointer slider ${
                  hasError
                    ? 'slider-error'
                    : hasWarning
                    ? 'slider-warning'
                    : 'slider-normal'
                }`}
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>{config.min}{config.unit}</span>
                <span>{config.max}{config.unit}</span>
              </div>
            </div>

            {/* Description */}
            {config.description && (
              <p className="text-xs text-gray-400">{config.description}</p>
            )}

            {/* Error/Warning Messages */}
            {fieldError && (
              <div className="text-xs text-red-400 bg-red-900/20 px-2 py-1 rounded">
                {fieldError.message}
              </div>
            )}
            {fieldWarning && (
              <div className="text-xs text-yellow-400 bg-yellow-900/20 px-2 py-1 rounded">
                {fieldWarning.message}
              </div>
            )}

            {/* Value constraints info */}
            <div className="text-xs text-gray-500">
              Range: {config.min} - {config.max} {config.unit}
            </div>
          </div>
        );
      })}

      {/* Additional constraints info */}
      <div className="mt-6 p-3 bg-gray-700/50 rounded-md">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Constraints</h4>
        <div className="text-xs text-gray-400 space-y-1">
          {envelopeType === EnvelopeType.CYLINDER && (
            <>
              <div>• Minimum volume: 10 m³</div>
              <div>• Maximum aspect ratio: 20:1</div>
              <div>• Recommended radius: 2-6 m</div>
            </>
          )}
          {envelopeType === EnvelopeType.BOX && (
            <>
              <div>• Minimum volume: 10 m³</div>
              <div>• All dimensions must be ≥ 1 m</div>
              <div>• Recommended ceiling height: 2-4 m</div>
            </>
          )}
          {envelopeType === EnvelopeType.TORUS && (
            <>
              <div>• Minor radius must be &lt; major radius</div>
              <div>• Minimum tube diameter: 1 m</div>
              <div>• Recommended major radius: 5-15 m</div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};