"""
Life Support Systems (LSS) Model for HabitatCanvas

This module implements comprehensive life support systems analysis including:
- Oxygen consumption and CO2 scrubbing mass balance calculations
- Water recycling and storage requirement estimators
- Atmospheric pressure and composition validation
- LSS margin calculation with safety factor recommendations

Requirements: 4.3, 4.6
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


class AtmosphereComposition(str, Enum):
    """Standard atmosphere composition profiles"""
    EARTH_NORMAL = "earth_normal"  # 21% O2, 78% N2, 1% other
    SPACE_STATION = "space_station"  # 21% O2, 79% N2 (simplified)
    HIGH_OXYGEN = "high_oxygen"  # 26% O2, 74% N2 (fire risk)
    LOW_PRESSURE = "low_pressure"  # 21% O2 at reduced pressure


class LSSComponentType(str, Enum):
    """Types of LSS components"""
    OXYGEN_GENERATOR = "oxygen_generator"
    CO2_SCRUBBER = "co2_scrubber"
    WATER_RECYCLER = "water_recycler"
    ATMOSPHERE_PROCESSOR = "atmosphere_processor"
    PRESSURE_REGULATOR = "pressure_regulator"
    BACKUP_SYSTEM = "backup_system"


@dataclass
class AtmosphereParameters:
    """Atmospheric parameters and composition"""
    pressure_kpa: float  # Total pressure in kPa
    oxygen_partial_pressure_kpa: float  # O2 partial pressure
    co2_partial_pressure_ppm: float  # CO2 concentration in ppm
    nitrogen_partial_pressure_kpa: float  # N2 partial pressure
    humidity_percent: float  # Relative humidity
    temperature_c: float  # Temperature in Celsius
    
    @property
    def oxygen_percentage(self) -> float:
        """Calculate oxygen percentage by volume"""
        return (self.oxygen_partial_pressure_kpa / self.pressure_kpa) * 100
    
    @property
    def is_breathable(self) -> bool:
        """Check if atmosphere is breathable"""
        return (
            16.0 <= self.oxygen_percentage <= 25.0 and
            self.co2_partial_pressure_ppm < 5000 and
            80.0 <= self.pressure_kpa <= 110.0
        )


@dataclass
class ConsumableRequirements:
    """Daily consumable requirements per crew member"""
    oxygen_kg_day: float
    water_kg_day: float
    food_kg_day: float
    co2_production_kg_day: float
    metabolic_water_kg_day: float
    waste_water_kg_day: float


@dataclass
class LSSComponent:
    """Life support system component specification"""
    component_id: str
    component_type: LSSComponentType
    capacity_per_day: float  # Processing capacity (kg/day or m³/day)
    power_consumption_w: float
    mass_kg: float
    reliability: float  # 0.0 to 1.0
    maintenance_hours_per_month: float
    redundancy_level: int  # 0 = no redundancy, 1 = backup, 2 = triple redundancy


@dataclass
class MassBalance:
    """Mass balance for consumables"""
    input_kg_day: float
    output_kg_day: float
    recycled_kg_day: float
    net_consumption_kg_day: float
    storage_required_kg: float
    margin_percent: float


@dataclass
class LSSAnalysis:
    """Comprehensive LSS analysis results"""
    atmosphere_parameters: AtmosphereParameters
    oxygen_balance: MassBalance
    co2_balance: MassBalance
    water_balance: MassBalance
    lss_components: List[LSSComponent]
    total_power_consumption_w: float
    total_mass_kg: float
    overall_reliability: float
    safety_margins: Dict[str, float]
    critical_failures: List[str]
    recommendations: List[str]
    lss_margin: float


class LSSModel:
    """
    Comprehensive Life Support Systems model for habitat analysis.
    
    Calculates mass balances, atmospheric composition, and system margins
    for oxygen, CO2, water, and other life support requirements.
    """
    
    def __init__(self):
        self.module_library = get_module_library()
        
        # Standard consumable requirements per crew member per day
        self.baseline_requirements = ConsumableRequirements(
            oxygen_kg_day=0.84,  # kg O2 per person per day
            water_kg_day=3.52,   # kg H2O per person per day (drinking + hygiene)
            food_kg_day=1.83,    # kg food per person per day
            co2_production_kg_day=1.04,  # kg CO2 per person per day
            metabolic_water_kg_day=0.35,  # kg H2O from metabolism per day
            waste_water_kg_day=3.17      # kg waste water per person per day
        )
        
        # Standard atmosphere compositions
        self.atmosphere_profiles = {
            AtmosphereComposition.EARTH_NORMAL: AtmosphereParameters(
                pressure_kpa=101.325,
                oxygen_partial_pressure_kpa=21.27,
                co2_partial_pressure_ppm=400,
                nitrogen_partial_pressure_kpa=79.12,
                humidity_percent=50.0,
                temperature_c=22.0
            ),
            AtmosphereComposition.SPACE_STATION: AtmosphereParameters(
                pressure_kpa=101.325,
                oxygen_partial_pressure_kpa=21.27,
                co2_partial_pressure_ppm=3000,  # Higher CO2 tolerance
                nitrogen_partial_pressure_kpa=80.05,
                humidity_percent=60.0,
                temperature_c=22.0
            ),
            AtmosphereComposition.HIGH_OXYGEN: AtmosphereParameters(
                pressure_kpa=101.325,
                oxygen_partial_pressure_kpa=26.34,
                co2_partial_pressure_ppm=400,
                nitrogen_partial_pressure_kpa=74.98,
                humidity_percent=45.0,
                temperature_c=20.0
            ),
            AtmosphereComposition.LOW_PRESSURE: AtmosphereParameters(
                pressure_kpa=70.0,
                oxygen_partial_pressure_kpa=14.7,  # 21% of 70 kPa
                co2_partial_pressure_ppm=400,
                nitrogen_partial_pressure_kpa=55.3,
                humidity_percent=40.0,
                temperature_c=24.0
            )
        }
        
        # LSS component specifications
        self.standard_components = {
            LSSComponentType.OXYGEN_GENERATOR: LSSComponent(
                component_id="ogs_standard",
                component_type=LSSComponentType.OXYGEN_GENERATOR,
                capacity_per_day=5.0,  # kg O2/day
                power_consumption_w=3500,
                mass_kg=200,
                reliability=0.98,
                maintenance_hours_per_month=8,
                redundancy_level=1
            ),
            LSSComponentType.CO2_SCRUBBER: LSSComponent(
                component_id="cdra_standard",
                component_type=LSSComponentType.CO2_SCRUBBER,
                capacity_per_day=6.0,  # kg CO2/day
                power_consumption_w=600,
                mass_kg=85,
                reliability=0.95,
                maintenance_hours_per_month=4,
                redundancy_level=1
            ),
            LSSComponentType.WATER_RECYCLER: LSSComponent(
                component_id="wrs_standard",
                component_type=LSSComponentType.WATER_RECYCLER,
                capacity_per_day=20.0,  # kg H2O/day
                power_consumption_w=1200,
                mass_kg=150,
                reliability=0.92,
                maintenance_hours_per_month=12,
                redundancy_level=1
            ),
            LSSComponentType.ATMOSPHERE_PROCESSOR: LSSComponent(
                component_id="atm_proc_standard",
                component_type=LSSComponentType.ATMOSPHERE_PROCESSOR,
                capacity_per_day=1000.0,  # m³ air/day
                power_consumption_w=800,
                mass_kg=120,
                reliability=0.97,
                maintenance_hours_per_month=6,
                redundancy_level=0
            )
        }
        
        # Safety factors and margins
        self.safety_factors = {
            "oxygen": 1.25,      # 25% safety margin for oxygen
            "co2_scrubbing": 1.30,  # 30% safety margin for CO2 removal
            "water": 1.20,       # 20% safety margin for water
            "power": 1.15,       # 15% safety margin for power
            "storage": 1.40      # 40% safety margin for storage
        }
        
        # Recycling efficiencies
        self.recycling_efficiencies = {
            "water_from_humidity": 0.85,    # 85% recovery from humidity
            "water_from_urine": 0.93,       # 93% recovery from urine
            "water_from_wash": 0.75,        # 75% recovery from wash water
            "oxygen_from_co2": 0.50,        # 50% O2 recovery from CO2 (Sabatier)
            "oxygen_from_water": 0.89       # 89% efficiency of electrolysis
        }
    
    async def analyze_lss_requirements(
        self,
        modules: List[ModulePlacement],
        envelope: EnvelopeSpec,
        mission_params: MissionParameters,
        atmosphere_profile: AtmosphereComposition = AtmosphereComposition.SPACE_STATION
    ) -> LSSAnalysis:
        """
        Perform comprehensive LSS analysis for the habitat layout.
        
        Args:
            modules: List of module placements
            envelope: Habitat envelope specification
            mission_params: Mission parameters and constraints
            atmosphere_profile: Target atmosphere composition
            
        Returns:
            Comprehensive LSS analysis results
        """
        logger.info(f"Starting LSS analysis for {mission_params.crew_size} crew, {mission_params.duration_days} days")
        
        # Get target atmosphere parameters
        atmosphere_params = self.atmosphere_profiles[atmosphere_profile]
        
        # Calculate habitat volume for atmospheric calculations
        habitat_volume_m3 = envelope.volume
        
        # Identify LSS-capable modules
        lss_modules = self._identify_lss_modules(modules)
        
        # Calculate consumable requirements
        crew_requirements = self._calculate_crew_requirements(mission_params)
        
        # Perform mass balance calculations
        oxygen_balance = await self._calculate_oxygen_balance(
            crew_requirements, lss_modules, mission_params
        )
        
        co2_balance = await self._calculate_co2_balance(
            crew_requirements, lss_modules, mission_params, habitat_volume_m3
        )
        
        water_balance = await self._calculate_water_balance(
            crew_requirements, lss_modules, mission_params
        )
        
        # Determine required LSS components
        required_components = self._determine_lss_components(
            crew_requirements, oxygen_balance, co2_balance, water_balance
        )
        
        # Calculate system characteristics
        total_power = sum(comp.power_consumption_w for comp in required_components)
        total_mass = sum(comp.mass_kg for comp in required_components)
        overall_reliability = self._calculate_system_reliability(required_components)
        
        # Calculate safety margins
        safety_margins = self._calculate_safety_margins(
            oxygen_balance, co2_balance, water_balance, required_components, crew_requirements
        )
        
        # Identify critical failures and generate recommendations
        critical_failures = self._identify_critical_failures(
            oxygen_balance, co2_balance, water_balance, safety_margins
        )
        
        recommendations = self._generate_lss_recommendations(
            oxygen_balance, co2_balance, water_balance, safety_margins, 
            critical_failures, mission_params
        )
        
        # Calculate overall LSS margin
        lss_margin = self._calculate_overall_lss_margin(safety_margins)
        
        return LSSAnalysis(
            atmosphere_parameters=atmosphere_params,
            oxygen_balance=oxygen_balance,
            co2_balance=co2_balance,
            water_balance=water_balance,
            lss_components=required_components,
            total_power_consumption_w=total_power,
            total_mass_kg=total_mass,
            overall_reliability=overall_reliability,
            safety_margins=safety_margins,
            critical_failures=critical_failures,
            recommendations=recommendations,
            lss_margin=lss_margin
        )
    
    def _identify_lss_modules(self, modules: List[ModulePlacement]) -> List[ModulePlacement]:
        """Identify modules that can house LSS equipment."""
        lss_capable_types = {
            ModuleType.MECHANICAL,
            ModuleType.LABORATORY,  # Can house some LSS equipment
            ModuleType.STORAGE      # Can house backup systems
        }
        
        return [m for m in modules if m.type in lss_capable_types]
    
    def _calculate_crew_requirements(self, mission_params: MissionParameters) -> ConsumableRequirements:
        """Calculate total crew consumable requirements."""
        crew_size = mission_params.crew_size
        
        # Apply activity-based modifiers
        activity_modifier = 1.0
        if mission_params.activity_schedule.get("exercise", 0) > 2.5:
            activity_modifier += 0.1  # Higher metabolism with more exercise
        
        return ConsumableRequirements(
            oxygen_kg_day=self.baseline_requirements.oxygen_kg_day * crew_size * activity_modifier,
            water_kg_day=self.baseline_requirements.water_kg_day * crew_size,
            food_kg_day=self.baseline_requirements.food_kg_day * crew_size * activity_modifier,
            co2_production_kg_day=self.baseline_requirements.co2_production_kg_day * crew_size * activity_modifier,
            metabolic_water_kg_day=self.baseline_requirements.metabolic_water_kg_day * crew_size,
            waste_water_kg_day=self.baseline_requirements.waste_water_kg_day * crew_size
        )
    
    async def _calculate_oxygen_balance(
        self,
        crew_requirements: ConsumableRequirements,
        lss_modules: List[ModulePlacement],
        mission_params: MissionParameters
    ) -> MassBalance:
        """Calculate oxygen mass balance with recycling."""
        
        # Daily oxygen consumption
        daily_consumption = crew_requirements.oxygen_kg_day
        
        # Oxygen generation capacity from LSS modules
        oxygen_generation_capacity = len([m for m in lss_modules if m.type == ModuleType.MECHANICAL]) * 5.0  # kg/day per mechanical module
        
        # Oxygen recovery from CO2 (Sabatier reaction)
        co2_to_oxygen_recovery = (
            crew_requirements.co2_production_kg_day * 
            self.recycling_efficiencies["oxygen_from_co2"] * 
            (32.0 / 44.0)  # Molecular weight conversion CO2 -> O2
        )
        
        # Total oxygen production
        total_production = oxygen_generation_capacity + co2_to_oxygen_recovery
        
        # Net consumption (production - consumption)
        net_consumption = daily_consumption - total_production
        
        # Storage requirements (mission duration + safety margin)
        storage_required = max(0, net_consumption) * mission_params.duration_days * self.safety_factors["storage"]
        
        # Calculate margin
        if daily_consumption > 0:
            margin_percent = ((total_production - daily_consumption) / daily_consumption) * 100
        else:
            margin_percent = 100.0
        
        return MassBalance(
            input_kg_day=total_production,
            output_kg_day=daily_consumption,
            recycled_kg_day=co2_to_oxygen_recovery,
            net_consumption_kg_day=net_consumption,
            storage_required_kg=storage_required,
            margin_percent=margin_percent
        )
    
    async def _calculate_co2_balance(
        self,
        crew_requirements: ConsumableRequirements,
        lss_modules: List[ModulePlacement],
        mission_params: MissionParameters,
        habitat_volume_m3: float
    ) -> MassBalance:
        """Calculate CO2 mass balance with scrubbing capacity."""
        
        # Daily CO2 production
        daily_production = crew_requirements.co2_production_kg_day
        
        # CO2 scrubbing capacity from LSS modules
        scrubbing_capacity = len([m for m in lss_modules if m.type == ModuleType.MECHANICAL]) * 6.0  # kg/day per mechanical module
        
        # CO2 recycling (Sabatier reaction)
        co2_recycled = daily_production * self.recycling_efficiencies["oxygen_from_co2"]
        
        # Net CO2 removal needed
        net_removal_needed = daily_production - co2_recycled
        
        # Check atmospheric CO2 buildup
        # Assume 10% of habitat volume is air space, rest is equipment/structure
        air_volume_m3 = habitat_volume_m3 * 0.1
        
        # CO2 concentration buildup without scrubbing (simplified)
        co2_buildup_rate_ppm_day = (daily_production * 1000) / (air_volume_m3 * 1.225)  # Rough approximation
        
        # Storage requirements (for venting or processing)
        storage_required = max(0, net_removal_needed - scrubbing_capacity) * mission_params.duration_days
        
        # Calculate margin
        if daily_production > 0:
            margin_percent = ((scrubbing_capacity - net_removal_needed) / daily_production) * 100
        else:
            margin_percent = 100.0
        
        return MassBalance(
            input_kg_day=daily_production,
            output_kg_day=scrubbing_capacity,
            recycled_kg_day=co2_recycled,
            net_consumption_kg_day=net_removal_needed,
            storage_required_kg=storage_required,
            margin_percent=margin_percent
        )
    
    async def _calculate_water_balance(
        self,
        crew_requirements: ConsumableRequirements,
        lss_modules: List[ModulePlacement],
        mission_params: MissionParameters
    ) -> MassBalance:
        """Calculate water mass balance with recycling systems."""
        
        # Daily water consumption
        daily_consumption = crew_requirements.water_kg_day
        
        # Water recovery from various sources
        humidity_recovery = crew_requirements.waste_water_kg_day * 0.3 * self.recycling_efficiencies["water_from_humidity"]
        urine_recovery = crew_requirements.waste_water_kg_day * 0.4 * self.recycling_efficiencies["water_from_urine"]
        wash_water_recovery = crew_requirements.waste_water_kg_day * 0.3 * self.recycling_efficiencies["water_from_wash"]
        metabolic_water = crew_requirements.metabolic_water_kg_day
        
        # Total water recovery
        total_recovery = humidity_recovery + urine_recovery + wash_water_recovery + metabolic_water
        
        # Water recycling capacity from LSS modules
        recycling_capacity = len([m for m in lss_modules if m.type == ModuleType.MECHANICAL]) * 20.0  # kg/day per mechanical module
        
        # Effective water production (limited by recycling capacity)
        effective_production = min(total_recovery, recycling_capacity)
        
        # Net water consumption
        net_consumption = daily_consumption - effective_production
        
        # Storage requirements
        storage_required = max(0, net_consumption) * mission_params.duration_days * self.safety_factors["water"]
        
        # Calculate margin
        if daily_consumption > 0:
            margin_percent = ((effective_production - daily_consumption) / daily_consumption) * 100
        else:
            margin_percent = 100.0
        
        return MassBalance(
            input_kg_day=effective_production,
            output_kg_day=daily_consumption,
            recycled_kg_day=total_recovery,
            net_consumption_kg_day=net_consumption,
            storage_required_kg=storage_required,
            margin_percent=margin_percent
        )
    
    def _determine_lss_components(
        self,
        crew_requirements: ConsumableRequirements,
        oxygen_balance: MassBalance,
        co2_balance: MassBalance,
        water_balance: MassBalance
    ) -> List[LSSComponent]:
        """Determine required LSS components based on mass balances."""
        components = []
        
        # Oxygen generation systems
        if oxygen_balance.net_consumption_kg_day > 0:
            num_oxygen_generators = math.ceil(
                oxygen_balance.net_consumption_kg_day * self.safety_factors["oxygen"] / 
                self.standard_components[LSSComponentType.OXYGEN_GENERATOR].capacity_per_day
            )
            
            for i in range(num_oxygen_generators):
                comp = self.standard_components[LSSComponentType.OXYGEN_GENERATOR]
                components.append(LSSComponent(
                    component_id=f"{comp.component_id}_{i+1}",
                    component_type=comp.component_type,
                    capacity_per_day=comp.capacity_per_day,
                    power_consumption_w=comp.power_consumption_w,
                    mass_kg=comp.mass_kg,
                    reliability=comp.reliability,
                    maintenance_hours_per_month=comp.maintenance_hours_per_month,
                    redundancy_level=comp.redundancy_level
                ))
        
        # CO2 scrubbing systems
        if co2_balance.net_consumption_kg_day > 0:
            num_co2_scrubbers = math.ceil(
                co2_balance.net_consumption_kg_day * self.safety_factors["co2_scrubbing"] / 
                self.standard_components[LSSComponentType.CO2_SCRUBBER].capacity_per_day
            )
            
            for i in range(num_co2_scrubbers):
                comp = self.standard_components[LSSComponentType.CO2_SCRUBBER]
                components.append(LSSComponent(
                    component_id=f"{comp.component_id}_{i+1}",
                    component_type=comp.component_type,
                    capacity_per_day=comp.capacity_per_day,
                    power_consumption_w=comp.power_consumption_w,
                    mass_kg=comp.mass_kg,
                    reliability=comp.reliability,
                    maintenance_hours_per_month=comp.maintenance_hours_per_month,
                    redundancy_level=comp.redundancy_level
                ))
        
        # Water recycling systems
        if water_balance.net_consumption_kg_day > 0:
            num_water_recyclers = math.ceil(
                water_balance.net_consumption_kg_day * self.safety_factors["water"] / 
                self.standard_components[LSSComponentType.WATER_RECYCLER].capacity_per_day
            )
            
            for i in range(num_water_recyclers):
                comp = self.standard_components[LSSComponentType.WATER_RECYCLER]
                components.append(LSSComponent(
                    component_id=f"{comp.component_id}_{i+1}",
                    component_type=comp.component_type,
                    capacity_per_day=comp.capacity_per_day,
                    power_consumption_w=comp.power_consumption_w,
                    mass_kg=comp.mass_kg,
                    reliability=comp.reliability,
                    maintenance_hours_per_month=comp.maintenance_hours_per_month,
                    redundancy_level=comp.redundancy_level
                ))
        
        # Always include atmosphere processor
        comp = self.standard_components[LSSComponentType.ATMOSPHERE_PROCESSOR]
        components.append(comp)
        
        return components
    
    def _calculate_system_reliability(self, components: List[LSSComponent]) -> float:
        """Calculate overall system reliability."""
        if not components:
            return 0.0
        
        # Group components by type for redundancy calculation
        component_groups = {}
        for comp in components:
            if comp.component_type not in component_groups:
                component_groups[comp.component_type] = []
            component_groups[comp.component_type].append(comp)
        
        # Calculate reliability for each component type
        type_reliabilities = []
        for comp_type, comp_list in component_groups.items():
            if len(comp_list) == 1:
                # Single component - no redundancy
                type_reliabilities.append(comp_list[0].reliability)
            else:
                # Multiple components - calculate redundancy reliability
                # Assuming parallel redundancy: R_system = 1 - (1-R1)(1-R2)...(1-Rn)
                failure_prob = 1.0
                for comp in comp_list:
                    failure_prob *= (1.0 - comp.reliability)
                type_reliabilities.append(1.0 - failure_prob)
        
        # Overall system reliability (series system)
        overall_reliability = 1.0
        for reliability in type_reliabilities:
            overall_reliability *= reliability
        
        return overall_reliability
    
    def _calculate_safety_margins(
        self,
        oxygen_balance: MassBalance,
        co2_balance: MassBalance,
        water_balance: MassBalance,
        components: List[LSSComponent],
        crew_requirements: ConsumableRequirements
    ) -> Dict[str, float]:
        """Calculate safety margins for all LSS subsystems."""
        
        margins = {}
        
        # Oxygen margin
        margins["oxygen"] = oxygen_balance.margin_percent / 100.0
        
        # CO2 scrubbing margin
        margins["co2_scrubbing"] = co2_balance.margin_percent / 100.0
        
        # Water margin
        margins["water"] = water_balance.margin_percent / 100.0
        
        # Power margin
        total_power_required = sum(comp.power_consumption_w for comp in components)
        # Assume 5kW baseline power available per mechanical module
        mechanical_modules = len([comp for comp in components if comp.component_type == LSSComponentType.ATMOSPHERE_PROCESSOR])
        available_power = max(1, mechanical_modules) * 5000  # watts
        margins["power"] = (available_power - total_power_required) / total_power_required if total_power_required > 0 else 1.0
        
        # Storage margin (based on worst-case consumable)
        worst_storage_margin = min(
            oxygen_balance.margin_percent,
            co2_balance.margin_percent,
            water_balance.margin_percent
        ) / 100.0
        margins["storage"] = worst_storage_margin
        
        # Reliability margin
        overall_reliability = self._calculate_system_reliability(components)
        margins["reliability"] = overall_reliability
        
        return margins
    
    def _identify_critical_failures(
        self,
        oxygen_balance: MassBalance,
        co2_balance: MassBalance,
        water_balance: MassBalance,
        safety_margins: Dict[str, float]
    ) -> List[str]:
        """Identify critical LSS failures and risks."""
        failures = []
        
        # Check for negative margins (critical failures)
        if safety_margins["oxygen"] < 0:
            failures.append(f"CRITICAL: Oxygen deficit of {abs(safety_margins['oxygen']*100):.1f}% - insufficient oxygen generation")
        
        if safety_margins["co2_scrubbing"] < 0:
            failures.append(f"CRITICAL: CO2 scrubbing deficit of {abs(safety_margins['co2_scrubbing']*100):.1f}% - CO2 buildup risk")
        
        if safety_margins["water"] < 0:
            failures.append(f"CRITICAL: Water deficit of {abs(safety_margins['water']*100):.1f}% - insufficient water recycling")
        
        if safety_margins["power"] < 0:
            failures.append(f"CRITICAL: Power deficit of {abs(safety_margins['power']*100):.1f}% - insufficient power for LSS")
        
        # Check for low margins (warnings)
        if 0 <= safety_margins["oxygen"] < 0.1:
            failures.append(f"WARNING: Low oxygen margin ({safety_margins['oxygen']*100:.1f}%) - consider additional generation capacity")
        
        if 0 <= safety_margins["co2_scrubbing"] < 0.15:
            failures.append(f"WARNING: Low CO2 scrubbing margin ({safety_margins['co2_scrubbing']*100:.1f}%) - consider additional scrubbing capacity")
        
        if 0 <= safety_margins["water"] < 0.1:
            failures.append(f"WARNING: Low water margin ({safety_margins['water']*100:.1f}%) - consider additional recycling capacity")
        
        if safety_margins["reliability"] < 0.9:
            failures.append(f"WARNING: Low system reliability ({safety_margins['reliability']*100:.1f}%) - consider redundancy improvements")
        
        return failures
    
    def _generate_lss_recommendations(
        self,
        oxygen_balance: MassBalance,
        co2_balance: MassBalance,
        water_balance: MassBalance,
        safety_margins: Dict[str, float],
        critical_failures: List[str],
        mission_params: MissionParameters
    ) -> List[str]:
        """Generate LSS optimization recommendations."""
        recommendations = []
        
        # Address critical failures first
        if safety_margins["oxygen"] < 0.1:
            additional_capacity = abs(oxygen_balance.net_consumption_kg_day) * 0.3
            recommendations.append(
                f"Add oxygen generation capacity: {additional_capacity:.1f} kg/day "
                f"(consider additional electrolysis unit or oxygen storage)"
            )
        
        if safety_margins["co2_scrubbing"] < 0.15:
            additional_capacity = abs(co2_balance.net_consumption_kg_day) * 0.4
            recommendations.append(
                f"Add CO2 scrubbing capacity: {additional_capacity:.1f} kg/day "
                f"(consider additional CDRA unit or backup scrubbers)"
            )
        
        if safety_margins["water"] < 0.1:
            additional_capacity = abs(water_balance.net_consumption_kg_day) * 0.25
            recommendations.append(
                f"Add water recycling capacity: {additional_capacity:.1f} kg/day "
                f"(consider additional WRS unit or water storage)"
            )
        
        # Efficiency improvements
        if water_balance.recycled_kg_day < water_balance.output_kg_day * 0.8:
            recommendations.append(
                "Improve water recycling efficiency - current recovery rate is below 80%"
            )
        
        if oxygen_balance.recycled_kg_day < oxygen_balance.output_kg_day * 0.3:
            recommendations.append(
                "Consider Sabatier reactor for oxygen recovery from CO2 - could reduce oxygen storage requirements"
            )
        
        # Redundancy recommendations
        if safety_margins["reliability"] < 0.95:
            recommendations.append(
                "Add redundant LSS components - single point failures detected in critical systems"
            )
        
        # Mission-specific recommendations
        if mission_params.duration_days > 365:
            recommendations.append(
                "Long-duration mission detected - consider closed-loop LSS with minimal resupply requirements"
            )
        
        if mission_params.crew_size > 6:
            recommendations.append(
                "Large crew size - consider distributed LSS architecture with multiple processing nodes"
            )
        
        # Storage optimization
        total_storage = oxygen_balance.storage_required_kg + water_balance.storage_required_kg
        if total_storage > 1000:  # kg
            recommendations.append(
                f"High storage requirements ({total_storage:.0f} kg) - optimize recycling efficiency to reduce storage needs"
            )
        
        return recommendations
    
    def _calculate_overall_lss_margin(self, safety_margins: Dict[str, float]) -> float:
        """Calculate overall LSS margin as weighted average."""
        
        # Weight critical systems more heavily
        weights = {
            "oxygen": 0.25,
            "co2_scrubbing": 0.25,
            "water": 0.20,
            "power": 0.15,
            "reliability": 0.15
        }
        
        weighted_margin = 0.0
        total_weight = 0.0
        
        for system, margin in safety_margins.items():
            if system in weights:
                weighted_margin += margin * weights[system]
                total_weight += weights[system]
        
        overall_margin = weighted_margin / total_weight if total_weight > 0 else 0.0
        
        # Clamp to reasonable range for the PerformanceMetrics model
        return max(-0.2, min(1.0, overall_margin))