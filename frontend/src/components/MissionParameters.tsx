import React, { useState, useCallback, useMemo } from 'react';
import { MissionParameters, ValidationResult } from '../types';
import { validateMissionParameters } from '../types/validation';

interface MissionParametersProps {
  onMissionChange: (mission: MissionParameters) => void;
  initialMission?: MissionParameters;
}

interface MissionTemplate {
  name: string;
  description: string;
  parameters: Partial<MissionParameters>;
}

const MISSION_TEMPLATES: MissionTemplate[] = [
  {
    name: 'Lunar Gateway',
    description: 'Long-duration lunar orbit station',
    parameters: {
      crew_size: 4,
      duration_days: 180,
      priority_weights: {
        safety: 0.4,
        efficiency: 0.3,
        mass: 0.2,
        power: 0.1
      },
      activity_schedule: {
        sleep: 8,
        work: 8,
        exercise: 2,
        meals: 2,
        maintenance: 2,
        recreation: 2
      },
      emergency_scenarios: ['depressurization', 'fire', 'medical_emergency']
    }
  },
  {
    name: 'Mars Transit',
    description: 'Interplanetary transfer vehicle',
    parameters: {
      crew_size: 6,
      duration_days: 270,
      priority_weights: {
        safety: 0.5,
        efficiency: 0.2,
        mass: 0.2,
        power: 0.1
      },
      activity_schedule: {
        sleep: 8,
        work: 6,
        exercise: 3,
        meals: 2,
        maintenance: 3,
        recreation: 2
      },
      emergency_scenarios: ['depressurization', 'fire', 'medical_emergency', 'radiation_exposure']
    }
  },
  {
    name: 'ISS Research',
    description: 'Low Earth orbit research station',
    parameters: {
      crew_size: 7,
      duration_days: 180,
      priority_weights: {
        safety: 0.3,
        efficiency: 0.4,
        mass: 0.15,
        power: 0.15
      },
      activity_schedule: {
        sleep: 8,
        work: 8,
        exercise: 2.5,
        meals: 1.5,
        maintenance: 2,
        recreation: 2
      },
      emergency_scenarios: ['depressurization', 'fire', 'medical_emergency']
    }
  },
  {
    name: 'Mars Surface Base',
    description: 'Planetary surface habitat',
    parameters: {
      crew_size: 8,
      duration_days: 500,
      priority_weights: {
        safety: 0.35,
        efficiency: 0.25,
        mass: 0.25,
        power: 0.15
      },
      activity_schedule: {
        sleep: 8,
        work: 8,
        exercise: 2,
        meals: 2,
        maintenance: 2,
        recreation: 1,
        eva: 1
      },
      emergency_scenarios: ['depressurization', 'fire', 'medical_emergency', 'dust_storm', 'equipment_failure']
    }
  }
];

const DEFAULT_MISSION: MissionParameters = {
  crew_size: 4,
  duration_days: 180,
  priority_weights: {
    safety: 0.4,
    efficiency: 0.3,
    mass: 0.2,
    power: 0.1
  },
  activity_schedule: {
    sleep: 8,
    work: 8,
    exercise: 2,
    meals: 2,
    maintenance: 2,
    recreation: 2
  },
  emergency_scenarios: ['depressurization', 'fire', 'medical_emergency']
};

export const MissionParametersComponent: React.FC<MissionParametersProps> = ({
  onMissionChange,
  initialMission
}) => {
  const [mission, setMission] = useState<MissionParameters>(
    initialMission || DEFAULT_MISSION
  );

  const [validation, setValidation] = useState<ValidationResult>({
    isValid: true,
    errors: [],
    warnings: []
  });

  // Validate mission parameters
  const validateAndUpdate = useCallback((updatedMission: MissionParameters) => {
    const validationResult = validateMissionParameters(updatedMission);
    setValidation(validationResult);
    setMission(updatedMission);
    
    if (validationResult.isValid) {
      onMissionChange(updatedMission);
    }
  }, [onMissionChange]);

  // Handle crew size change
  const handleCrewSizeChange = useCallback((value: number) => {
    const updatedMission = {
      ...mission,
      crew_size: Math.max(1, Math.min(20, Math.round(value)))
    };
    validateAndUpdate(updatedMission);
  }, [mission, validateAndUpdate]);

  // Handle duration change
  const handleDurationChange = useCallback((value: number) => {
    const updatedMission = {
      ...mission,
      duration_days: Math.max(1, Math.min(1000, Math.round(value)))
    };
    validateAndUpdate(updatedMission);
  }, [mission, validateAndUpdate]);

  // Handle priority weight change
  const handlePriorityWeightChange = useCallback((priority: string, value: number) => {
    const updatedWeights = {
      ...mission.priority_weights,
      [priority]: value / 100 // Convert percentage to decimal
    };

    // Normalize weights to sum to 1.0
    const totalWeight = Object.values(updatedWeights).reduce((sum, weight) => sum + weight, 0);
    if (totalWeight > 0) {
      Object.keys(updatedWeights).forEach(key => {
        updatedWeights[key] = updatedWeights[key] / totalWeight;
      });
    }

    const updatedMission = {
      ...mission,
      priority_weights: updatedWeights
    };
    validateAndUpdate(updatedMission);
  }, [mission, validateAndUpdate]);

  // Handle activity schedule change
  const handleActivityScheduleChange = useCallback((activity: string, value: number) => {
    const updatedSchedule = {
      ...mission.activity_schedule,
      [activity]: Math.max(0, Math.min(24, value))
    };

    const updatedMission = {
      ...mission,
      activity_schedule: updatedSchedule
    };
    validateAndUpdate(updatedMission);
  }, [mission, validateAndUpdate]);

  // Handle emergency scenario toggle
  const handleEmergencyScenarioToggle = useCallback((scenario: string) => {
    const updatedScenarios = mission.emergency_scenarios.includes(scenario)
      ? mission.emergency_scenarios.filter(s => s !== scenario)
      : [...mission.emergency_scenarios, scenario];

    const updatedMission = {
      ...mission,
      emergency_scenarios: updatedScenarios
    };
    validateAndUpdate(updatedMission);
  }, [mission, validateAndUpdate]);

  // Handle template selection
  const handleTemplateSelect = useCallback((template: MissionTemplate) => {
    const updatedMission = {
      ...DEFAULT_MISSION,
      ...template.parameters
    } as MissionParameters;
    validateAndUpdate(updatedMission);
  }, [validateAndUpdate]);

  // Calculate total activity hours
  const totalActivityHours = useMemo(() => {
    return Object.values(mission.activity_schedule).reduce((sum, hours) => sum + hours, 0);
  }, [mission.activity_schedule]);

  // Export mission configuration
  const handleExport = useCallback(() => {
    const dataStr = JSON.stringify(mission, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `mission_parameters_${Date.now()}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  }, [mission]);

  // Import mission configuration
  const handleImport = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const importedMission = JSON.parse(e.target?.result as string) as MissionParameters;
        validateAndUpdate(importedMission);
      } catch (error) {
        console.error('Failed to import mission parameters:', error);
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
  }, [validateAndUpdate]);

  return (
    <div className="bg-gray-800 p-6 rounded-lg space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white mb-2">Mission Parameters</h2>
        <p className="text-gray-400 text-sm">
          Configure crew requirements and mission constraints for layout optimization
        </p>
      </div>

      {/* Mission Templates */}
      <div className="space-y-3">
        <h3 className="text-lg font-semibold text-white">Mission Templates</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {MISSION_TEMPLATES.map((template) => (
            <button
              key={template.name}
              data-testid={`template-${template.name.toLowerCase().replace(/\s+/g, '-')}`}
              onClick={() => handleTemplateSelect(template)}
              className="p-3 bg-gray-700 hover:bg-gray-600 rounded-md text-left transition-colors"
            >
              <div className="text-white font-medium">{template.name}</div>
              <div className="text-gray-400 text-sm mt-1">{template.description}</div>
              <div className="text-gray-500 text-xs mt-1">
                {template.parameters.crew_size} crew • {template.parameters.duration_days} days
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Basic Parameters */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-white">Basic Parameters</h3>
        
        {/* Crew Size */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-300">Crew Size</label>
            <div className="flex items-center space-x-2">
              <input
                type="number"
                data-testid="crew-size-input"
                value={mission.crew_size}
                onChange={(e) => handleCrewSizeChange(parseInt(e.target.value) || 1)}
                min={1}
                max={20}
                className="w-16 px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <span className="text-xs text-gray-400">people</span>
            </div>
          </div>
          <input
            type="range"
            data-testid="crew-size-slider"
            value={mission.crew_size}
            onChange={(e) => handleCrewSizeChange(parseInt(e.target.value))}
            min={1}
            max={20}
            step={1}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-xs text-gray-500">
            <span>1 person</span>
            <span>20 people</span>
          </div>
        </div>

        {/* Mission Duration */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-300">Mission Duration</label>
            <div className="flex items-center space-x-2">
              <input
                type="number"
                data-testid="duration-input"
                value={mission.duration_days}
                onChange={(e) => handleDurationChange(parseInt(e.target.value) || 1)}
                min={1}
                max={1000}
                className="w-20 px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <span className="text-xs text-gray-400">days</span>
            </div>
          </div>
          <input
            type="range"
            data-testid="duration-slider"
            value={mission.duration_days}
            onChange={(e) => handleDurationChange(parseInt(e.target.value))}
            min={1}
            max={1000}
            step={1}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-xs text-gray-500">
            <span>1 day</span>
            <span>1000 days</span>
          </div>
        </div>
      </div>

      {/* Priority Weights */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-white">Priority Weights</h3>
        <p className="text-gray-400 text-sm">
          Adjust the relative importance of different optimization objectives
        </p>
        
        {Object.entries(mission.priority_weights).map(([priority, weight]) => (
          <div key={priority} className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-300 capitalize">
                {priority}
              </label>
              <span className="text-sm text-gray-400">
                {(weight * 100).toFixed(1)}%
              </span>
            </div>
            <input
              type="range"
              data-testid={`priority-${priority}-slider`}
              value={weight * 100}
              onChange={(e) => handlePriorityWeightChange(priority, parseFloat(e.target.value))}
              min={0}
              max={100}
              step={1}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
            />
          </div>
        ))}
        
        <div className="text-xs text-gray-500">
          Weights are automatically normalized to sum to 100%
        </div>
      </div>

      {/* Activity Schedule */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-white">Daily Activity Schedule</h3>
        <p className="text-gray-400 text-sm">
          Define how crew time is allocated throughout the day
        </p>
        
        {Object.entries(mission.activity_schedule).map(([activity, hours]) => (
          <div key={activity} className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-300 capitalize">
                {activity.replace('_', ' ')}
              </label>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  data-testid={`activity-${activity}-input`}
                  value={hours.toFixed(1)}
                  onChange={(e) => handleActivityScheduleChange(activity, parseFloat(e.target.value) || 0)}
                  min={0}
                  max={24}
                  step={0.5}
                  className="w-16 px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <span className="text-xs text-gray-400">hrs</span>
              </div>
            </div>
            <input
              type="range"
              data-testid={`activity-${activity}-slider`}
              value={hours}
              onChange={(e) => handleActivityScheduleChange(activity, parseFloat(e.target.value))}
              min={0}
              max={24}
              step={0.5}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
            />
          </div>
        ))}
        
        <div className={`text-sm ${totalActivityHours > 24 ? 'text-yellow-400' : 'text-gray-400'}`}>
          Total: {totalActivityHours.toFixed(1)} hours
          {totalActivityHours > 24 && ' (exceeds 24 hours)'}
        </div>
      </div>

      {/* Emergency Scenarios */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-white">Emergency Scenarios</h3>
        <p className="text-gray-400 text-sm">
          Select emergency scenarios to consider in layout optimization
        </p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {[
            'depressurization',
            'fire',
            'medical_emergency',
            'radiation_exposure',
            'dust_storm',
            'equipment_failure',
            'power_loss',
            'communication_loss'
          ].map((scenario) => (
            <label key={scenario} className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                data-testid={`emergency-${scenario}`}
                checked={mission.emergency_scenarios.includes(scenario)}
                onChange={() => handleEmergencyScenarioToggle(scenario)}
                className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
              />
              <span className="text-sm text-gray-300 capitalize">
                {scenario.replace('_', ' ')}
              </span>
            </label>
          ))}
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
        <h3 className="text-lg font-semibold text-white">Configuration</h3>
        <div className="flex space-x-2">
          <button
            data-testid="export-mission-button"
            onClick={handleExport}
            disabled={!validation.isValid}
            className="flex-1 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
          >
            Export Configuration
          </button>
          <label className="flex-1">
            <input
              type="file"
              data-testid="import-mission-input"
              accept=".json"
              onChange={handleImport}
              className="hidden"
            />
            <div className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 cursor-pointer text-center transition-colors">
              Import Configuration
            </div>
          </label>
        </div>
      </div>
    </div>
  );
};