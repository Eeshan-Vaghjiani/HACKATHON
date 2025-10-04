"""
Power and Thermal Budget Analysis for HabitatCanvas

This module implements comprehensive power and thermal analysis including:
- Power consumption calculator for all modules and systems
- Battery sizing and solar panel requirement estimation
- Steady-state thermal analysis with heat generation and rejection
- Thermal margin calculation with hot/cold case scenarios

Requirements: 4.4, 4.6
"""

import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

from app.models.base import (
    ModulePlacement, EnvelopeSpec, MissionParameters, ModuleType
)
from app.models.module_library import get_module_library, ModuleDefinition

logger = logging.getLogger(__name__)


class ThermalScenario(str, Enum):
    """Thermal analysis scenarios"""
    HOT_CASE = "hot_case"      # Maximum heat generation, minimum rejection
    COLD_CASE = "cold_case"    # Minimum heat generation, maximum rejection
    NOMINAL = "nominal"        # Average operating conditions
    ECLIPSE = "eclipse"        # No solar heating, battery power only
    PEAK_SOLAR = "peak_solar"  # Maximum solar heating


class PowerSource(str, Enum):
    """Types of power sources"""
    SOLAR_PANELS = "solar_panels"
    BATTERIES = "batteries"
    FUEL_CELLS = "fuel_cells"
    NUCLEAR_RTG = "nuclear_rtg"
    GRID_CONNECTION = "grid_connection"


class ThermalControlMethod(str, Enum):
    """Thermal control methods"""
    PASSIVE_RADIATORS = "passive_radiators"
    ACTIVE_COOLING = "active_cooling"
    HEAT_PUMPS = "heat_pumps"
    PHASE_CHANGE_MATERIALS = "phase_change_materials"


@dataclass
class PowerComponent:
    """Power system component specification"""
    component_id: str
    power_source: PowerSource
    capacity_w: float
    efficiency: float
    mass_kg: float
    volume_m3: float
    operational_temp_range_c: Tuple[float, float]
    degradation_rate_per_year: float


@dataclass
class ThermalComponent:
    """Thermal control system component"""
    component_id: str
    control_method: ThermalControlMethod
    heat_rejection_capacity_w: float
    power_consumption_w: float
    mass_kg: float
    operating_temp_range_c: Tuple[float, float]
    efficiency: float


@dataclass
class PowerBudget:
    """Power consumption and generation analysis"""
    total_consumption_w: float
    module_consumption_w: Dict[str, float]
    system_consumption_w: Dict[str, float]
    peak_consumption_w: float
    average_consumption_w: float
    power_sources: List[PowerComponent]
    total_generation_capacity_w: float
    battery_capacity_wh: float
    solar_panel_area_m2: float
    power_margin: float
    autonomy_hours: float


@dataclass
class ThermalBudget:
    """Thermal generation and rejection analysis"""
    total_heat_generation_w: float
    heat_sources: Dict[str, float]
    heat_rejection_capacity_w: float
    thermal_control_systems: List[ThermalComponent]
    steady_state_temp_c: float
    thermal_margin: float
    hot_case_temp_c: float
    cold_case_temp_c: float
    critical_components: List[str]


@dataclass
class PowerThermalAnalysis:
    """Comprehensive power and thermal analysis results"""
    power_budget: PowerBudget
    thermal_budget: ThermalBudget
    scenario_analyses: Dict[ThermalScenario, Dict[str, float]]
    integration_issues: List[str]
    recommendations: List[str]
    overall_power_score: float
    overall_thermal_score: float


class PowerThermalAnalyzer:
    """
    Comprehensive power and thermal analysis engine for habitat layouts.
    
    Analyzes power consumption, generation, thermal loads, and cooling
    requirements to ensure system viability and optimize performance.
    """
    
    def __init__(self):
        self.module_library = get_module_library()
        
        # Power consumption parameters
        self.base_power_per_crew_w = 200  # Base power per crew member (lighting, ventilation, etc.)
        self.activity_power_multipliers = {
            "sleep": 0.3,      # Reduced power during sleep
            "work": 1.2,       # Increased power during work
            "exercise": 1.5,   # High power during exercise
            "meals": 1.0,      # Normal power during meals
            "personal": 0.8    # Reduced power during personal time
        }
        
        # Heat generation parameters (watts per crew member)
        self.crew_heat_generation = {
            "metabolic_base": 80,     # Base metabolic heat
            "activity_sleep": 70,     # Heat during sleep
            "activity_work": 120,     # Heat during work
            "activity_exercise": 400, # Heat during exercise
            "activity_meals": 100,    # Heat during meals
            "activity_personal": 90   # Heat during personal time
        }
        
        # Environmental parameters
        self.solar_flux_w_m2 = 1361  # Solar constant at 1 AU
        self.earth_albedo = 0.3      # Earth's albedo
        self.space_temp_k = 4        # Deep space temperature
        self.stefan_boltzmann = 5.67e-8  # Stefan-Boltzmann constant
        
        # Standard power components
        self.standard_power_components = {
            PowerSource.SOLAR_PANELS: PowerComponent(
                component_id="solar_array_standard",
                power_source=PowerSource.SOLAR_PANELS,
                capacity_w=300,  # per m²
                efficiency=0.22,  # 22% efficiency
                mass_kg=2.5,     # kg per m²
                volume_m3=0.01,  # m³ per m²
                operational_temp_range_c=(-150, 120),
                degradation_rate_per_year=0.005  # 0.5% per year
            ),
            PowerSource.BATTERIES: PowerComponent(
                component_id="battery_lithium_ion",
                power_source=PowerSource.BATTERIES,
                capacity_w=1000,  # Discharge rate
                efficiency=0.95,
                mass_kg=15,      # kg per kWh
                volume_m3=0.008, # m³ per kWh
                operational_temp_range_c=(-20, 60),
                degradation_rate_per_year=0.02  # 2% per year
            ),
            PowerSource.FUEL_CELLS: PowerComponent(
                component_id="fuel_cell_pem",
                power_source=PowerSource.FUEL_CELLS,
                capacity_w=5000,
                efficiency=0.50,
                mass_kg=200,
                volume_m3=0.5,
                operational_temp_range_c=(5, 80),
                degradation_rate_per_year=0.01
            )
        }
        
        # Standard thermal components
        self.standard_thermal_components = {
            ThermalControlMethod.PASSIVE_RADIATORS: ThermalComponent(
                component_id="radiator_passive",
                control_method=ThermalControlMethod.PASSIVE_RADIATORS,
                heat_rejection_capacity_w=400,  # per m²
                power_consumption_w=0,
                mass_kg=5,  # kg per m²
                operating_temp_range_c=(-150, 150),
                efficiency=0.85
            ),
            ThermalControlMethod.ACTIVE_COOLING: ThermalComponent(
                component_id="cooling_system_active",
                control_method=ThermalControlMethod.ACTIVE_COOLING,
                heat_rejection_capacity_w=2000,
                power_consumption_w=300,
                mass_kg=50,
                operating_temp_range_c=(-40, 80),
                efficiency=0.70
            ),
            ThermalControlMethod.HEAT_PUMPS: ThermalComponent(
                component_id="heat_pump_standard",
                control_method=ThermalControlMethod.HEAT_PUMPS,
                heat_rejection_capacity_w=3000,
                power_consumption_w=800,
                mass_kg=80,
                operating_temp_range_c=(-20, 60),
                efficiency=0.75
            )
        }
        
        # Safety margins
        self.safety_margins = {
            "power_generation": 1.25,    # 25% margin for power generation
            "battery_capacity": 1.30,    # 30% margin for battery capacity
            "thermal_rejection": 1.20,   # 20% margin for thermal rejection
            "component_derating": 0.85   # Derate components to 85% of capacity
        }
    
    async def analyze_power_thermal(
        self,
        modules: List[ModulePlacement],
        envelope: EnvelopeSpec,
        mission_params: MissionParameters,
        orbital_parameters: Optional[Dict[str, float]] = None
    ) -> PowerThermalAnalysis:
        """
        Perform comprehensive power and thermal analysis.
        
        Args:
            modules: List of module placements
            envelope: Habitat envelope specification
            mission_params: Mission parameters and constraints
            orbital_parameters: Optional orbital parameters for solar/thermal environment
            
        Returns:
            Comprehensive power and thermal analysis
        """
        logger.info(f"Starting power/thermal analysis for {len(modules)} modules")
        
        # Set default orbital parameters if not provided
        if orbital_parameters is None:
            orbital_parameters = {
                "altitude_km": 400,      # ISS-like orbit
                "inclination_deg": 51.6,
                "eclipse_fraction": 0.35, # 35% of orbit in eclipse
                "beta_angle_deg": 0      # Sun angle relative to orbital plane
            }
        
        # Calculate power budget
        power_budget = await self._calculate_power_budget(modules, mission_params, orbital_parameters)
        
        # Calculate thermal budget
        thermal_budget = await self._calculate_thermal_budget(
            modules, envelope, mission_params, power_budget, orbital_parameters
        )
        
        # Analyze different thermal scenarios
        scenario_analyses = await self._analyze_thermal_scenarios(
            modules, envelope, mission_params, power_budget, orbital_parameters
        )
        
        # Identify integration issues
        integration_issues = self._identify_integration_issues(power_budget, thermal_budget)
        
        # Generate recommendations
        recommendations = self._generate_power_thermal_recommendations(
            power_budget, thermal_budget, scenario_analyses, integration_issues, mission_params
        )
        
        # Calculate overall scores
        power_score = self._calculate_power_score(power_budget)
        thermal_score = self._calculate_thermal_score(thermal_budget, scenario_analyses)
        
        return PowerThermalAnalysis(
            power_budget=power_budget,
            thermal_budget=thermal_budget,
            scenario_analyses=scenario_analyses,
            integration_issues=integration_issues,
            recommendations=recommendations,
            overall_power_score=power_score,
            overall_thermal_score=thermal_score
        )
    
    async def _calculate_power_budget(
        self,
        modules: List[ModulePlacement],
        mission_params: MissionParameters,
        orbital_parameters: Dict[str, float]
    ) -> PowerBudget:
        """Calculate comprehensive power consumption and generation budget."""
        
        # Calculate module power consumption
        module_consumption = {}
        total_module_power = 0.0
        
        for module in modules:
            module_def = self._get_module_definition(module.module_id)
            if module_def:
                power = module_def.spec.power_w
                module_consumption[module.module_id] = power
                total_module_power += power
        
        # Calculate system power consumption
        crew_size = mission_params.crew_size
        base_crew_power = crew_size * self.base_power_per_crew_w
        
        # Activity-based power variations
        activity_power = 0.0
        total_activity_time = sum(mission_params.activity_schedule.values())
        
        for activity, time_hours in mission_params.activity_schedule.items():
            if activity in self.activity_power_multipliers:
                multiplier = self.activity_power_multipliers[activity]
                activity_fraction = time_hours / 24.0 if total_activity_time > 0 else 0.0
                activity_power += base_crew_power * multiplier * activity_fraction
        
        # System power breakdown
        system_consumption = {
            "crew_base": base_crew_power,
            "crew_activity": activity_power,
            "life_support": crew_size * 150,  # LSS power per crew member
            "thermal_control": 500,           # Base thermal control power
            "communications": 200,            # Communications systems
            "computers": 300,                 # Computing and control systems
            "lighting": crew_size * 50        # Lighting power per crew member
        }
        
        total_system_power = sum(system_consumption.values())
        total_consumption = total_module_power + total_system_power
        
        # Calculate peak and average consumption
        peak_multiplier = 1.3  # 30% peak above average
        peak_consumption = total_consumption * peak_multiplier
        average_consumption = total_consumption * 0.85  # 85% average utilization
        
        # Size power generation systems
        required_generation = peak_consumption * self.safety_margins["power_generation"]
        
        # Solar panel sizing
        eclipse_fraction = orbital_parameters.get("eclipse_fraction", 0.35)
        solar_efficiency = self.standard_power_components[PowerSource.SOLAR_PANELS].efficiency
        solar_flux = self.solar_flux_w_m2 * solar_efficiency
        
        # Account for eclipse - panels must generate enough during sunlight to power through eclipse
        effective_solar_time = 1.0 - eclipse_fraction
        solar_panel_area = required_generation / (solar_flux * effective_solar_time)
        
        # Battery sizing for eclipse periods
        eclipse_duration_hours = 24 * eclipse_fraction  # Simplified daily eclipse
        battery_energy_wh = average_consumption * eclipse_duration_hours
        battery_capacity_wh = battery_energy_wh * self.safety_margins["battery_capacity"]
        
        # Create power source components
        power_sources = []
        
        # Solar panels
        solar_component = self.standard_power_components[PowerSource.SOLAR_PANELS]
        solar_generation_capacity = solar_panel_area * solar_flux
        power_sources.append(PowerComponent(
            component_id="habitat_solar_array",
            power_source=PowerSource.SOLAR_PANELS,
            capacity_w=solar_generation_capacity,
            efficiency=solar_component.efficiency,
            mass_kg=solar_component.mass_kg * solar_panel_area,
            volume_m3=solar_component.volume_m3 * solar_panel_area,
            operational_temp_range_c=solar_component.operational_temp_range_c,
            degradation_rate_per_year=solar_component.degradation_rate_per_year
        ))
        
        # Batteries
        battery_component = self.standard_power_components[PowerSource.BATTERIES]
        num_battery_units = math.ceil(battery_capacity_wh / 1000)  # 1kWh per unit
        power_sources.append(PowerComponent(
            component_id="habitat_battery_bank",
            power_source=PowerSource.BATTERIES,
            capacity_w=battery_component.capacity_w * num_battery_units,
            efficiency=battery_component.efficiency,
            mass_kg=battery_component.mass_kg * (battery_capacity_wh / 1000),
            volume_m3=battery_component.volume_m3 * (battery_capacity_wh / 1000),
            operational_temp_range_c=battery_component.operational_temp_range_c,
            degradation_rate_per_year=battery_component.degradation_rate_per_year
        ))
        
        total_generation_capacity = sum(source.capacity_w for source in power_sources)
        
        # Calculate power margin and autonomy
        power_margin = (total_generation_capacity - peak_consumption) / peak_consumption
        autonomy_hours = battery_capacity_wh / average_consumption
        
        return PowerBudget(
            total_consumption_w=total_consumption,
            module_consumption_w=module_consumption,
            system_consumption_w=system_consumption,
            peak_consumption_w=peak_consumption,
            average_consumption_w=average_consumption,
            power_sources=power_sources,
            total_generation_capacity_w=total_generation_capacity,
            battery_capacity_wh=battery_capacity_wh,
            solar_panel_area_m2=solar_panel_area,
            power_margin=power_margin,
            autonomy_hours=autonomy_hours
        )
    
    async def _calculate_thermal_budget(
        self,
        modules: List[ModulePlacement],
        envelope: EnvelopeSpec,
        mission_params: MissionParameters,
        power_budget: PowerBudget,
        orbital_parameters: Dict[str, float]
    ) -> ThermalBudget:
        """Calculate thermal generation and rejection budget."""
        
        # Calculate heat generation sources
        heat_sources = {}
        
        # Crew metabolic heat
        crew_size = mission_params.crew_size
        crew_metabolic_heat = 0.0
        
        for activity, time_hours in mission_params.activity_schedule.items():
            activity_key = f"activity_{activity}"
            if activity_key in self.crew_heat_generation:
                heat_rate = self.crew_heat_generation[activity_key]
                activity_fraction = time_hours / 24.0
                crew_metabolic_heat += heat_rate * crew_size * activity_fraction
        
        if crew_metabolic_heat == 0:
            # Fallback to base metabolic heat
            crew_metabolic_heat = self.crew_heat_generation["metabolic_base"] * crew_size
        
        heat_sources["crew_metabolic"] = crew_metabolic_heat
        
        # Equipment heat generation (assume 80% of power becomes heat)
        equipment_heat = power_budget.total_consumption_w * 0.8
        heat_sources["equipment"] = equipment_heat
        
        # Solar heating (external)
        solar_heating = self._calculate_solar_heating(envelope, orbital_parameters)
        heat_sources["solar_external"] = solar_heating
        
        # Earth infrared heating
        earth_ir_heating = self._calculate_earth_ir_heating(envelope, orbital_parameters)
        heat_sources["earth_infrared"] = earth_ir_heating
        
        total_heat_generation = sum(heat_sources.values())
        
        # Calculate required heat rejection capacity
        required_rejection = total_heat_generation * self.safety_margins["thermal_rejection"]
        
        # Size thermal control systems
        thermal_systems = []
        
        # Passive radiators (primary heat rejection)
        radiator_component = self.standard_thermal_components[ThermalControlMethod.PASSIVE_RADIATORS]
        radiator_area_m2 = required_rejection * 0.7 / radiator_component.heat_rejection_capacity_w
        
        thermal_systems.append(ThermalComponent(
            component_id="habitat_radiators",
            control_method=ThermalControlMethod.PASSIVE_RADIATORS,
            heat_rejection_capacity_w=radiator_area_m2 * radiator_component.heat_rejection_capacity_w,
            power_consumption_w=0,
            mass_kg=radiator_component.mass_kg * radiator_area_m2,
            operating_temp_range_c=radiator_component.operating_temp_range_c,
            efficiency=radiator_component.efficiency
        ))
        
        # Active cooling (backup and peak load)
        active_cooling_component = self.standard_thermal_components[ThermalControlMethod.ACTIVE_COOLING]
        active_cooling_capacity = required_rejection * 0.3  # Handle 30% of load
        
        thermal_systems.append(ThermalComponent(
            component_id="habitat_active_cooling",
            control_method=ThermalControlMethod.ACTIVE_COOLING,
            heat_rejection_capacity_w=active_cooling_capacity,
            power_consumption_w=active_cooling_component.power_consumption_w,
            mass_kg=active_cooling_component.mass_kg,
            operating_temp_range_c=active_cooling_component.operating_temp_range_c,
            efficiency=active_cooling_component.efficiency
        ))
        
        total_rejection_capacity = sum(system.heat_rejection_capacity_w for system in thermal_systems)
        
        # Calculate steady-state temperature (simplified)
        steady_state_temp = self._calculate_steady_state_temperature(
            total_heat_generation, total_rejection_capacity, envelope
        )
        
        # Calculate thermal margin
        thermal_margin = (total_rejection_capacity - total_heat_generation) / total_heat_generation
        
        # Identify critical components (those near temperature limits)
        critical_components = self._identify_thermal_critical_components(
            modules, steady_state_temp
        )
        
        # Calculate hot and cold case temperatures
        hot_case_temp = steady_state_temp + 15  # +15°C for hot case
        cold_case_temp = steady_state_temp - 20  # -20°C for cold case
        
        return ThermalBudget(
            total_heat_generation_w=total_heat_generation,
            heat_sources=heat_sources,
            heat_rejection_capacity_w=total_rejection_capacity,
            thermal_control_systems=thermal_systems,
            steady_state_temp_c=steady_state_temp,
            thermal_margin=thermal_margin,
            hot_case_temp_c=hot_case_temp,
            cold_case_temp_c=cold_case_temp,
            critical_components=critical_components
        )
    
    def _calculate_solar_heating(
        self, 
        envelope: EnvelopeSpec, 
        orbital_parameters: Dict[str, float]
    ) -> float:
        """Calculate solar heating load on habitat exterior."""
        
        # Calculate habitat cross-sectional area exposed to sun
        envelope_type = envelope.type if isinstance(envelope.type, str) else envelope.type.value
        
        if envelope_type == "cylinder":
            radius = envelope.params['radius']
            length = envelope.params['length']
            # Projected area of cylinder
            cross_sectional_area = 2 * radius * length  # Side view
        elif envelope_type == "box":
            width = envelope.params['width']
            height = envelope.params['height']
            # Projected area of box
            cross_sectional_area = width * height
        else:
            # Default estimate
            cross_sectional_area = 50.0  # m²
        
        # Solar flux with orbital considerations
        altitude_km = orbital_parameters.get("altitude_km", 400)
        # Solar flux decreases slightly with altitude (negligible for LEO)
        solar_flux = self.solar_flux_w_m2
        
        # Account for eclipse fraction
        eclipse_fraction = orbital_parameters.get("eclipse_fraction", 0.35)
        effective_solar_fraction = 1.0 - eclipse_fraction
        
        # Solar absorptivity (assume 0.3 for typical spacecraft materials)
        solar_absorptivity = 0.3
        
        solar_heating = (
            solar_flux * cross_sectional_area * solar_absorptivity * effective_solar_fraction
        )
        
        return solar_heating
    
    def _calculate_earth_ir_heating(
        self, 
        envelope: EnvelopeSpec, 
        orbital_parameters: Dict[str, float]
    ) -> float:
        """Calculate Earth infrared heating load."""
        
        # Earth infrared flux (approximately 237 W/m²)
        earth_ir_flux = 237.0  # W/m²
        
        # Calculate habitat surface area facing Earth
        envelope_type = envelope.type if isinstance(envelope.type, str) else envelope.type.value
        
        if envelope_type == "cylinder":
            radius = envelope.params['radius']
            length = envelope.params['length']
            # Half of cylinder surface faces Earth on average
            earth_facing_area = math.pi * radius * length * 0.5
        elif envelope_type == "box":
            width = envelope.params['width']
            height = envelope.params['height']
            depth = envelope.params['depth']
            # One face of box faces Earth
            earth_facing_area = width * height
        else:
            # Default estimate
            earth_facing_area = 30.0  # m²
        
        # Infrared absorptivity (assume 0.8 for typical materials)
        ir_absorptivity = 0.8
        
        # View factor to Earth (depends on altitude)
        altitude_km = orbital_parameters.get("altitude_km", 400)
        earth_radius_km = 6371
        view_factor = (earth_radius_km / (earth_radius_km + altitude_km)) ** 2
        
        earth_ir_heating = (
            earth_ir_flux * earth_facing_area * ir_absorptivity * view_factor
        )
        
        return earth_ir_heating
    
    def _calculate_steady_state_temperature(
        self, 
        heat_generation_w: float, 
        heat_rejection_w: float, 
        envelope: EnvelopeSpec
    ) -> float:
        """Calculate steady-state internal temperature."""
        
        # Simplified thermal model
        # Assume internal temperature is determined by heat balance
        
        # If heat rejection matches generation, use nominal temperature
        if abs(heat_generation_w - heat_rejection_w) < 100:  # Within 100W
            return 22.0  # Nominal 22°C
        
        # Calculate temperature rise/drop based on imbalance
        # Assume thermal mass and heat transfer coefficients
        thermal_mass_j_k = envelope.volume * 1000 * 1000  # Rough estimate (air + structure)
        
        # Temperature change rate (simplified)
        net_heat_w = heat_generation_w - heat_rejection_w
        temp_change_rate = net_heat_w / thermal_mass_j_k * 3600  # °C/hour
        
        # Steady-state temperature (assuming 24-hour equilibrium)
        steady_state_temp = 22.0 + (temp_change_rate * 24)
        
        # Clamp to reasonable range
        return max(-10, min(50, steady_state_temp))
    
    def _identify_thermal_critical_components(
        self, 
        modules: List[ModulePlacement], 
        ambient_temp_c: float
    ) -> List[str]:
        """Identify components that may exceed temperature limits."""
        critical_components = []
        
        # Temperature limits for different module types
        temp_limits = {
            ModuleType.LABORATORY: (15, 25),      # Tight temperature control
            ModuleType.MEDICAL: (18, 24),         # Medical equipment limits
            ModuleType.GALLEY: (10, 30),          # Food storage limits
            ModuleType.SLEEP_QUARTER: (18, 26),   # Crew comfort
            ModuleType.EXERCISE: (15, 28),        # Exercise equipment
            ModuleType.MECHANICAL: (-10, 40),     # Robust equipment
            ModuleType.STORAGE: (-5, 35),         # Storage limits
            ModuleType.AIRLOCK: (-20, 50)        # Wide range for EVA equipment
        }
        
        for module in modules:
            if module.type in temp_limits:
                min_temp, max_temp = temp_limits[module.type]
                
                if ambient_temp_c < min_temp:
                    critical_components.append(
                        f"{module.module_id}: Too cold ({ambient_temp_c:.1f}°C < {min_temp}°C)"
                    )
                elif ambient_temp_c > max_temp:
                    critical_components.append(
                        f"{module.module_id}: Too hot ({ambient_temp_c:.1f}°C > {max_temp}°C)"
                    )
        
        return critical_components
    
    async def _analyze_thermal_scenarios(
        self,
        modules: List[ModulePlacement],
        envelope: EnvelopeSpec,
        mission_params: MissionParameters,
        power_budget: PowerBudget,
        orbital_parameters: Dict[str, float]
    ) -> Dict[ThermalScenario, Dict[str, float]]:
        """Analyze different thermal scenarios (hot case, cold case, etc.)."""
        
        scenarios = {}
        
        # Base heat generation
        base_heat = power_budget.total_consumption_w * 0.8
        crew_heat = mission_params.crew_size * self.crew_heat_generation["metabolic_base"]
        
        # Hot case scenario
        hot_case_heat = base_heat * 1.2 + crew_heat * 1.3  # 20% higher equipment, 30% higher crew
        hot_case_solar = self._calculate_solar_heating(envelope, orbital_parameters) * 1.5  # Peak solar
        hot_case_total = hot_case_heat + hot_case_solar
        hot_case_temp = self._calculate_steady_state_temperature(hot_case_total, 0, envelope) + 30
        
        scenarios[ThermalScenario.HOT_CASE] = {
            "heat_generation_w": hot_case_total,
            "temperature_c": hot_case_temp,
            "margin": -0.2 if hot_case_temp > 35 else 0.1
        }
        
        # Cold case scenario
        cold_case_heat = base_heat * 0.6 + crew_heat * 0.8  # Reduced equipment and crew heat
        cold_case_temp = self._calculate_steady_state_temperature(cold_case_heat, 0, envelope) - 25
        
        scenarios[ThermalScenario.COLD_CASE] = {
            "heat_generation_w": cold_case_heat,
            "temperature_c": cold_case_temp,
            "margin": -0.1 if cold_case_temp < 15 else 0.2
        }
        
        # Eclipse scenario
        eclipse_heat = base_heat * 0.9 + crew_heat  # Normal operation, no solar heating
        eclipse_temp = self._calculate_steady_state_temperature(eclipse_heat, 0, envelope)
        
        scenarios[ThermalScenario.ECLIPSE] = {
            "heat_generation_w": eclipse_heat,
            "temperature_c": eclipse_temp,
            "margin": 0.0 if 18 <= eclipse_temp <= 26 else -0.1
        }
        
        # Peak solar scenario
        peak_solar_heat = base_heat + crew_heat
        peak_solar_external = self._calculate_solar_heating(envelope, orbital_parameters) * 2.0
        peak_solar_total = peak_solar_heat + peak_solar_external
        peak_solar_temp = self._calculate_steady_state_temperature(peak_solar_total, 0, envelope) + 20
        
        scenarios[ThermalScenario.PEAK_SOLAR] = {
            "heat_generation_w": peak_solar_total,
            "temperature_c": peak_solar_temp,
            "margin": -0.3 if peak_solar_temp > 40 else 0.0
        }
        
        # Nominal scenario
        nominal_heat = base_heat + crew_heat
        nominal_solar = self._calculate_solar_heating(envelope, orbital_parameters)
        nominal_total = nominal_heat + nominal_solar * 0.7  # Average solar
        nominal_temp = self._calculate_steady_state_temperature(nominal_total, 0, envelope)
        
        scenarios[ThermalScenario.NOMINAL] = {
            "heat_generation_w": nominal_total,
            "temperature_c": nominal_temp,
            "margin": 0.1 if 20 <= nominal_temp <= 24 else -0.05
        }
        
        return scenarios
    
    def _identify_integration_issues(
        self, 
        power_budget: PowerBudget, 
        thermal_budget: ThermalBudget
    ) -> List[str]:
        """Identify power-thermal integration issues."""
        issues = []
        
        # Power margin issues
        if power_budget.power_margin < 0:
            issues.append(
                f"CRITICAL: Power deficit of {abs(power_budget.power_margin*100):.1f}% - "
                f"insufficient power generation capacity"
            )
        elif power_budget.power_margin < 0.1:
            issues.append(
                f"WARNING: Low power margin ({power_budget.power_margin*100:.1f}%) - "
                f"consider additional generation capacity"
            )
        
        # Battery autonomy issues
        if power_budget.autonomy_hours < 8:
            issues.append(
                f"WARNING: Low battery autonomy ({power_budget.autonomy_hours:.1f} hours) - "
                f"insufficient for eclipse periods"
            )
        
        # Thermal margin issues
        if thermal_budget.thermal_margin < 0:
            issues.append(
                f"CRITICAL: Thermal rejection deficit of {abs(thermal_budget.thermal_margin*100):.1f}% - "
                f"insufficient cooling capacity"
            )
        elif thermal_budget.thermal_margin < 0.1:
            issues.append(
                f"WARNING: Low thermal margin ({thermal_budget.thermal_margin*100:.1f}%) - "
                f"consider additional cooling capacity"
            )
        
        # Temperature range issues
        if thermal_budget.hot_case_temp_c > 35:
            issues.append(
                f"CRITICAL: Hot case temperature ({thermal_budget.hot_case_temp_c:.1f}°C) "
                f"exceeds crew comfort limits"
            )
        
        if thermal_budget.cold_case_temp_c < 15:
            issues.append(
                f"WARNING: Cold case temperature ({thermal_budget.cold_case_temp_c:.1f}°C) "
                f"below crew comfort range"
            )
        
        # Power-thermal coupling issues
        thermal_control_power = sum(
            system.power_consumption_w for system in thermal_budget.thermal_control_systems
        )
        
        if thermal_control_power > power_budget.total_consumption_w * 0.2:
            issues.append(
                f"WARNING: Thermal control systems consume {thermal_control_power:.0f}W "
                f"({thermal_control_power/power_budget.total_consumption_w*100:.1f}% of total power)"
            )
        
        return issues
    
    def _generate_power_thermal_recommendations(
        self,
        power_budget: PowerBudget,
        thermal_budget: ThermalBudget,
        scenario_analyses: Dict[ThermalScenario, Dict[str, float]],
        integration_issues: List[str],
        mission_params: MissionParameters
    ) -> List[str]:
        """Generate power and thermal optimization recommendations."""
        recommendations = []
        
        # Power recommendations
        if power_budget.power_margin < 0.15:
            additional_solar = abs(power_budget.peak_consumption_w * 0.2)
            additional_area = additional_solar / (self.solar_flux_w_m2 * 0.22)
            recommendations.append(
                f"Add {additional_area:.1f} m² of solar panels ({additional_solar:.0f}W capacity) "
                f"to improve power margin"
            )
        
        if power_budget.autonomy_hours < 12:
            additional_battery = power_budget.average_consumption_w * 4  # 4 hours additional
            recommendations.append(
                f"Add {additional_battery:.0f} Wh of battery capacity for extended autonomy"
            )
        
        # Thermal recommendations
        if thermal_budget.thermal_margin < 0.15:
            additional_rejection = thermal_budget.total_heat_generation_w * 0.3
            additional_radiator_area = additional_rejection / 400  # 400 W/m² for radiators
            recommendations.append(
                f"Add {additional_radiator_area:.1f} m² of radiator area "
                f"({additional_rejection:.0f}W capacity) to improve thermal margin"
            )
        
        # Scenario-specific recommendations
        hot_case = scenario_analyses.get(ThermalScenario.HOT_CASE, {})
        if hot_case.get("temperature_c", 0) > 35:
            recommendations.append(
                "Install active cooling system for hot case scenarios - "
                "passive radiators insufficient for peak thermal loads"
            )
        
        cold_case = scenario_analyses.get(ThermalScenario.COLD_CASE, {})
        if cold_case.get("temperature_c", 0) < 15:
            recommendations.append(
                "Add thermal insulation and heating elements for cold case scenarios"
            )
        
        # Efficiency recommendations
        if power_budget.solar_panel_area_m2 > 100:
            recommendations.append(
                f"Large solar array required ({power_budget.solar_panel_area_m2:.1f} m²) - "
                f"consider power efficiency improvements or alternative power sources"
            )
        
        # Mission-specific recommendations
        if mission_params.duration_days > 365:
            recommendations.append(
                "Long-duration mission - consider degradation of solar panels and batteries "
                "over mission lifetime"
            )
        
        if mission_params.crew_size > 6:
            recommendations.append(
                "Large crew size - consider distributed power and thermal systems "
                "for improved redundancy"
            )
        
        return recommendations
    
    def _calculate_power_score(self, power_budget: PowerBudget) -> float:
        """Calculate overall power system performance score."""
        
        # Power margin score (target: 15-25% margin)
        margin_score = 1.0
        if power_budget.power_margin < 0:
            margin_score = 0.0
        elif power_budget.power_margin < 0.1:
            margin_score = power_budget.power_margin / 0.1
        elif power_budget.power_margin > 0.4:
            margin_score = 0.8  # Penalize over-sizing
        
        # Autonomy score (target: 12+ hours)
        autonomy_score = min(1.0, power_budget.autonomy_hours / 12.0)
        
        # Efficiency score (based on specific power)
        total_mass = sum(source.mass_kg for source in power_budget.power_sources)
        specific_power = power_budget.total_generation_capacity_w / total_mass if total_mass > 0 else 0
        efficiency_score = min(1.0, specific_power / 100.0)  # Target: 100 W/kg
        
        # Combine scores
        overall_score = (margin_score * 0.4 + autonomy_score * 0.3 + efficiency_score * 0.3)
        
        return max(0.0, min(1.0, overall_score))
    
    def _calculate_thermal_score(
        self, 
        thermal_budget: ThermalBudget, 
        scenario_analyses: Dict[ThermalScenario, Dict[str, float]]
    ) -> float:
        """Calculate overall thermal system performance score."""
        
        # Thermal margin score (target: 15-25% margin)
        margin_score = 1.0
        if thermal_budget.thermal_margin < 0:
            margin_score = 0.0
        elif thermal_budget.thermal_margin < 0.1:
            margin_score = thermal_budget.thermal_margin / 0.1
        elif thermal_budget.thermal_margin > 0.4:
            margin_score = 0.8  # Penalize over-sizing
        
        # Temperature control score (target: 20-24°C nominal)
        temp_score = 1.0
        nominal_temp = thermal_budget.steady_state_temp_c
        if 20 <= nominal_temp <= 24:
            temp_score = 1.0
        elif 18 <= nominal_temp <= 26:
            temp_score = 0.8
        elif 15 <= nominal_temp <= 30:
            temp_score = 0.6
        else:
            temp_score = 0.2
        
        # Scenario robustness score
        scenario_score = 1.0
        for scenario, results in scenario_analyses.items():
            scenario_temp = results.get("temperature_c", 22)
            if scenario_temp < 10 or scenario_temp > 40:
                scenario_score *= 0.5  # Penalize extreme temperatures
            elif scenario_temp < 15 or scenario_temp > 35:
                scenario_score *= 0.8
        
        # Combine scores
        overall_score = (margin_score * 0.4 + temp_score * 0.4 + scenario_score * 0.2)
        
        return max(0.0, min(1.0, overall_score))
    
    def _get_module_definition(self, module_id: str) -> Optional[ModuleDefinition]:
        """Get module definition by ID, handling both library and instance IDs."""
        # First try direct lookup
        module_def = self.module_library.get_module(module_id)
        if module_def:
            return module_def
        
        # If not found, try to extract base type from instance ID
        if '_' in module_id:
            parts = module_id.split('_')
            if len(parts) >= 3:
                module_type = '_'.join(parts[:-2])
                std_module_id = f"std_{module_type}"
                module_def = self.module_library.get_module(std_module_id)
                if module_def:
                    return module_def
        
        return None