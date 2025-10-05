"""
Microsoft Planetary Computer Integration Service

This service integrates with Microsoft's Planetary Computer platform to provide:
- Earth observation data for habitat site analysis
- Environmental datasets for life support optimization
- Terrain analysis for landing site selection
- Climate data for mission planning
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json

import httpx
import planetary_computer as pc
from pystac_client import Client
import stackstac
import numpy as np
import rasterio
from rasterio.warp import transform_bounds
import geopandas as gpd
from shapely.geometry import Point, Polygon

logger = logging.getLogger(__name__)


@dataclass
class SiteAnalysis:
    """Site analysis results from Planetary Computer data"""
    location: Tuple[float, float]  # (latitude, longitude)
    elevation_m: float
    slope_degrees: float
    temperature_range_c: Tuple[float, float]  # (min, max)
    precipitation_mm_year: float
    vegetation_index: float  # NDVI
    terrain_roughness: float
    solar_irradiance_kwh_m2_day: float
    accessibility_score: float  # 0-1, higher is better
    environmental_hazards: List[str]
    suitability_score: float  # 0-1, higher is better for habitat placement


@dataclass
class EnvironmentalData:
    """Environmental data for life support system optimization"""
    temperature_profile: Dict[str, float]  # seasonal temperature data
    humidity_profile: Dict[str, float]
    wind_patterns: Dict[str, float]
    atmospheric_pressure: float
    air_quality_index: float
    water_availability: float  # 0-1 scale
    soil_composition: Dict[str, float]
    natural_resources: List[str]


@dataclass
class LandingSiteCandidate:
    """Landing site candidate with analysis"""
    site_id: str
    name: str
    coordinates: Tuple[float, float]
    site_analysis: SiteAnalysis
    environmental_data: EnvironmentalData
    mission_suitability: Dict[str, float]  # scores for different mission types
    risk_assessment: Dict[str, float]
    recommended_habitat_config: Dict[str, Any]


class PlanetaryComputerService:
    """
    Service for integrating Microsoft Planetary Computer data into habitat design.
    
    Provides Earth observation data, environmental analysis, and site selection
    capabilities for optimizing habitat placement and life support systems.
    """
    
    def __init__(self):
        self.stac_api_url = "https://planetarycomputer.microsoft.com/api/stac/v1"
        self.data_api_url = "https://planetarycomputer.microsoft.com/api/data/v1"
        self.client = None
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Initialize STAC client
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the STAC client with Planetary Computer"""
        try:
            self.client = Client.open(
                self.stac_api_url,
                modifier=pc.sign_inplace  # Sign requests for data access
            )
            logger.info("Planetary Computer STAC client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Planetary Computer client: {e}")
            self.client = None
    
    async def analyze_landing_site(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 10.0,
        mission_type: str = "mars_analog"
    ) -> SiteAnalysis:
        """
        Analyze a potential landing site using Planetary Computer data.
        
        Args:
            latitude: Site latitude
            longitude: Site longitude  
            radius_km: Analysis radius in kilometers
            mission_type: Type of mission (mars_analog, lunar_analog, earth_base)
            
        Returns:
            SiteAnalysis with comprehensive site data
        """
        if not self.client:
            raise RuntimeError("Planetary Computer client not initialized")
        
        try:
            # Define area of interest
            bbox = self._calculate_bbox(latitude, longitude, radius_km)
            
            # Get elevation data from NASADEM
            elevation_data = await self._get_elevation_data(bbox)
            
            # Get Landsat data for terrain and vegetation analysis
            landsat_data = await self._get_landsat_data(bbox)
            
            # Get climate data
            climate_data = await self._get_climate_data(bbox)
            
            # Analyze terrain characteristics
            terrain_analysis = self._analyze_terrain(elevation_data, landsat_data)
            
            # Calculate suitability score
            suitability_score = self._calculate_site_suitability(
                terrain_analysis, climate_data, mission_type
            )
            
            return SiteAnalysis(
                location=(latitude, longitude),
                elevation_m=terrain_analysis["elevation"],
                slope_degrees=terrain_analysis["slope"],
                temperature_range_c=climate_data["temperature_range"],
                precipitation_mm_year=climate_data["precipitation"],
                vegetation_index=terrain_analysis["ndvi"],
                terrain_roughness=terrain_analysis["roughness"],
                solar_irradiance_kwh_m2_day=climate_data["solar_irradiance"],
                accessibility_score=terrain_analysis["accessibility"],
                environmental_hazards=climate_data["hazards"],
                suitability_score=suitability_score
            )
            
        except Exception as e:
            logger.error(f"Site analysis failed: {e}")
            raise
    
    async def find_optimal_landing_sites(
        self,
        region_bounds: Tuple[float, float, float, float],  # (min_lat, min_lon, max_lat, max_lon)
        mission_type: str = "mars_analog",
        num_sites: int = 5
    ) -> List[LandingSiteCandidate]:
        """
        Find optimal landing sites within a region using ML and environmental data.
        
        Args:
            region_bounds: Bounding box for search region
            mission_type: Type of mission for optimization
            num_sites: Number of candidate sites to return
            
        Returns:
            List of ranked landing site candidates
        """
        try:
            # Generate candidate sites using terrain analysis
            candidate_points = await self._generate_candidate_sites(region_bounds, mission_type)
            
            # Analyze each candidate site
            site_analyses = []
            for i, (lat, lon) in enumerate(candidate_points[:num_sites * 2]):  # Analyze more than needed
                try:
                    analysis = await self.analyze_landing_site(lat, lon, mission_type=mission_type)
                    environmental_data = await self._get_environmental_data(lat, lon)
                    
                    site_candidate = LandingSiteCandidate(
                        site_id=f"site_{i+1:03d}",
                        name=f"Candidate Site {i+1}",
                        coordinates=(lat, lon),
                        site_analysis=analysis,
                        environmental_data=environmental_data,
                        mission_suitability=self._calculate_mission_suitability(analysis, mission_type),
                        risk_assessment=self._assess_site_risks(analysis, environmental_data),
                        recommended_habitat_config=self._recommend_habitat_config(analysis, environmental_data)
                    )
                    site_analyses.append(site_candidate)
                    
                except Exception as e:
                    logger.warning(f"Failed to analyze candidate site {i+1}: {e}")
                    continue
            
            # Rank sites by suitability
            ranked_sites = sorted(
                site_analyses, 
                key=lambda x: x.site_analysis.suitability_score, 
                reverse=True
            )
            
            return ranked_sites[:num_sites]
            
        except Exception as e:
            logger.error(f"Optimal site finding failed: {e}")
            raise
    
    async def get_environmental_optimization_data(
        self,
        latitude: float,
        longitude: float,
        mission_duration_days: int = 500
    ) -> Dict[str, Any]:
        """
        Get environmental data for optimizing life support systems.
        
        Args:
            latitude: Site latitude
            longitude: Site longitude
            mission_duration_days: Mission duration for seasonal analysis
            
        Returns:
            Environmental optimization data
        """
        try:
            # Get multi-temporal environmental data
            seasonal_data = await self._get_seasonal_environmental_data(
                latitude, longitude, mission_duration_days
            )
            
            # Calculate life support optimization parameters
            lss_optimization = {
                "atmospheric_processing": {
                    "co2_levels_ppm": seasonal_data.get("co2_levels", 410),
                    "humidity_range": seasonal_data.get("humidity_range", (30, 70)),
                    "pressure_variation": seasonal_data.get("pressure_variation", 0.02)
                },
                "thermal_management": {
                    "temperature_extremes": seasonal_data.get("temperature_range", (-20, 40)),
                    "thermal_mass_requirements": seasonal_data.get("thermal_mass", 1000),
                    "insulation_r_value": seasonal_data.get("insulation_needs", 30)
                },
                "power_generation": {
                    "solar_availability": seasonal_data.get("solar_irradiance", 5.0),
                    "wind_potential": seasonal_data.get("wind_speed", 3.0),
                    "backup_power_days": seasonal_data.get("cloudy_days", 7)
                },
                "water_management": {
                    "atmospheric_water": seasonal_data.get("humidity", 50),
                    "precipitation": seasonal_data.get("precipitation", 500),
                    "water_recycling_efficiency": 0.95
                }
            }
            
            return {
                "site_coordinates": (latitude, longitude),
                "mission_duration_days": mission_duration_days,
                "seasonal_data": seasonal_data,
                "lss_optimization": lss_optimization,
                "environmental_constraints": self._calculate_environmental_constraints(seasonal_data),
                "recommended_systems": self._recommend_life_support_systems(lss_optimization)
            }
            
        except Exception as e:
            logger.error(f"Environmental optimization data retrieval failed: {e}")
            raise
    
    # Private helper methods
    
    def _calculate_bbox(self, lat: float, lon: float, radius_km: float) -> Tuple[float, float, float, float]:
        """Calculate bounding box around a point"""
        # Rough conversion: 1 degree ≈ 111 km
        degree_offset = radius_km / 111.0
        return (
            lon - degree_offset,  # min_lon
            lat - degree_offset,  # min_lat  
            lon + degree_offset,  # max_lon
            lat + degree_offset   # max_lat
        )
    
    async def _get_elevation_data(self, bbox: Tuple[float, float, float, float]) -> Dict[str, Any]:
        """Get elevation data from NASADEM"""
        try:
            search = self.client.search(
                collections=["nasadem"],
                bbox=bbox,
                limit=10
            )
            
            items = list(search.get_items())
            if not items:
                return {"elevation": 0, "slope": 0, "roughness": 0}
            
            # Stack the data using stackstac
            stack = stackstac.stack(items, assets=["elevation"])
            
            # Calculate terrain metrics
            elevation_mean = float(np.nanmean(stack.values))
            elevation_std = float(np.nanstd(stack.values))
            
            return {
                "elevation": elevation_mean,
                "slope": elevation_std * 0.1,  # Simplified slope calculation
                "roughness": elevation_std / elevation_mean if elevation_mean > 0 else 0
            }
            
        except Exception as e:
            logger.warning(f"Elevation data retrieval failed: {e}")
            return {"elevation": 0, "slope": 0, "roughness": 0}
    
    async def _get_landsat_data(self, bbox: Tuple[float, float, float, float]) -> Dict[str, Any]:
        """Get Landsat data for vegetation and terrain analysis"""
        try:
            # Search for recent Landsat Collection 2 Level-2 data
            search = self.client.search(
                collections=["landsat-c2-l2"],
                bbox=bbox,
                datetime="2023-01-01/2023-12-31",
                query={"eo:cloud_cover": {"lt": 20}},
                limit=5
            )
            
            items = list(search.get_items())
            if not items:
                return {"ndvi": 0.3, "accessibility": 0.5}
            
            # Calculate NDVI (simplified)
            # In a real implementation, you'd process the actual bands
            ndvi_estimate = 0.4  # Placeholder
            accessibility_score = 0.7  # Based on terrain analysis
            
            return {
                "ndvi": ndvi_estimate,
                "accessibility": accessibility_score
            }
            
        except Exception as e:
            logger.warning(f"Landsat data retrieval failed: {e}")
            return {"ndvi": 0.3, "accessibility": 0.5}
    
    async def _get_climate_data(self, bbox: Tuple[float, float, float, float]) -> Dict[str, Any]:
        """Get climate data for the region"""
        try:
            # In a real implementation, you'd use climate datasets from Planetary Computer
            # For now, return reasonable estimates
            return {
                "temperature_range": (-10, 35),  # Celsius
                "precipitation": 400,  # mm/year
                "solar_irradiance": 5.5,  # kWh/m²/day
                "hazards": ["extreme_temperature", "dust_storms"]
            }
            
        except Exception as e:
            logger.warning(f"Climate data retrieval failed: {e}")
            return {
                "temperature_range": (0, 30),
                "precipitation": 500,
                "solar_irradiance": 5.0,
                "hazards": []
            }
    
    def _analyze_terrain(self, elevation_data: Dict, landsat_data: Dict) -> Dict[str, Any]:
        """Analyze terrain characteristics"""
        return {
            "elevation": elevation_data["elevation"],
            "slope": elevation_data["slope"],
            "roughness": elevation_data["roughness"],
            "ndvi": landsat_data["ndvi"],
            "accessibility": landsat_data["accessibility"]
        }
    
    def _calculate_site_suitability(
        self, 
        terrain: Dict[str, Any], 
        climate: Dict[str, Any], 
        mission_type: str
    ) -> float:
        """Calculate overall site suitability score"""
        # Weighted scoring based on mission type
        weights = {
            "mars_analog": {
                "elevation": 0.1,
                "slope": 0.2,
                "temperature": 0.3,
                "accessibility": 0.2,
                "hazards": 0.2
            },
            "lunar_analog": {
                "elevation": 0.15,
                "slope": 0.25,
                "temperature": 0.2,
                "accessibility": 0.25,
                "hazards": 0.15
            },
            "earth_base": {
                "elevation": 0.1,
                "slope": 0.15,
                "temperature": 0.2,
                "accessibility": 0.35,
                "hazards": 0.2
            }
        }
        
        mission_weights = weights.get(mission_type, weights["mars_analog"])
        
        # Normalize scores (0-1)
        elevation_score = max(0, 1 - abs(terrain["elevation"]) / 3000)  # Prefer moderate elevations
        slope_score = max(0, 1 - terrain["slope"] / 30)  # Prefer gentle slopes
        temp_range = climate["temperature_range"]
        temp_score = max(0, 1 - (temp_range[1] - temp_range[0]) / 60)  # Prefer stable temperatures
        accessibility_score = terrain["accessibility"]
        hazard_score = max(0, 1 - len(climate["hazards"]) / 5)  # Fewer hazards is better
        
        # Calculate weighted score
        total_score = (
            elevation_score * mission_weights["elevation"] +
            slope_score * mission_weights["slope"] +
            temp_score * mission_weights["temperature"] +
            accessibility_score * mission_weights["accessibility"] +
            hazard_score * mission_weights["hazards"]
        )
        
        return min(1.0, max(0.0, total_score))
    
    async def _generate_candidate_sites(
        self, 
        bounds: Tuple[float, float, float, float], 
        mission_type: str
    ) -> List[Tuple[float, float]]:
        """Generate candidate sites within bounds"""
        # Simple grid-based candidate generation
        # In a real implementation, you'd use ML and terrain analysis
        min_lat, min_lon, max_lat, max_lon = bounds
        
        candidates = []
        lat_step = (max_lat - min_lat) / 10
        lon_step = (max_lon - min_lon) / 10
        
        for i in range(10):
            for j in range(10):
                lat = min_lat + i * lat_step
                lon = min_lon + j * lon_step
                candidates.append((lat, lon))
        
        return candidates
    
    async def _get_environmental_data(self, lat: float, lon: float) -> EnvironmentalData:
        """Get detailed environmental data for a site"""
        # Placeholder implementation
        return EnvironmentalData(
            temperature_profile={"winter": -5, "spring": 15, "summer": 30, "fall": 10},
            humidity_profile={"winter": 60, "spring": 55, "summer": 45, "fall": 65},
            wind_patterns={"avg_speed": 3.5, "max_speed": 15, "direction": "SW"},
            atmospheric_pressure=101.3,
            air_quality_index=50,
            water_availability=0.7,
            soil_composition={"sand": 40, "clay": 30, "silt": 30},
            natural_resources=["water", "minerals", "solar"]
        )
    
    def _calculate_mission_suitability(self, analysis: SiteAnalysis, mission_type: str) -> Dict[str, float]:
        """Calculate suitability for different mission aspects"""
        return {
            "landing_safety": analysis.suitability_score * 0.9,
            "construction_feasibility": (1 - analysis.terrain_roughness) * 0.8,
            "resource_availability": analysis.accessibility_score * 0.7,
            "environmental_stability": 1 - len(analysis.environmental_hazards) / 10,
            "power_generation": analysis.solar_irradiance_kwh_m2_day / 8.0,
            "overall": analysis.suitability_score
        }
    
    def _assess_site_risks(self, analysis: SiteAnalysis, env_data: EnvironmentalData) -> Dict[str, float]:
        """Assess risks for the site"""
        return {
            "terrain_risk": analysis.terrain_roughness,
            "weather_risk": len(analysis.environmental_hazards) / 10,
            "accessibility_risk": 1 - analysis.accessibility_score,
            "resource_risk": 1 - env_data.water_availability,
            "overall_risk": (analysis.terrain_roughness + len(analysis.environmental_hazards) / 10) / 2
        }
    
    def _recommend_habitat_config(self, analysis: SiteAnalysis, env_data: EnvironmentalData) -> Dict[str, Any]:
        """Recommend habitat configuration based on site analysis"""
        return {
            "foundation_type": "reinforced_concrete" if analysis.slope_degrees < 5 else "pile_foundation",
            "insulation_rating": "high" if env_data.temperature_profile["winter"] < 0 else "standard",
            "power_system": "solar_primary" if analysis.solar_irradiance_kwh_m2_day > 4 else "hybrid",
            "water_system": "atmospheric_extraction" if env_data.humidity_profile["summer"] > 60 else "storage_primary",
            "structural_reinforcement": "high" if env_data.wind_patterns["max_speed"] > 20 else "standard"
        }
    
    async def _get_seasonal_environmental_data(
        self, 
        lat: float, 
        lon: float, 
        duration_days: int
    ) -> Dict[str, Any]:
        """Get seasonal environmental data"""
        # Placeholder implementation
        return {
            "temperature_range": (-15, 40),
            "humidity_range": (30, 80),
            "pressure_variation": 0.05,
            "co2_levels": 415,
            "solar_irradiance": 5.2,
            "wind_speed": 4.1,
            "precipitation": 450,
            "cloudy_days": 120,
            "humidity": 55
        }
    
    def _calculate_environmental_constraints(self, seasonal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate environmental constraints for habitat design"""
        return {
            "max_temperature_c": seasonal_data["temperature_range"][1],
            "min_temperature_c": seasonal_data["temperature_range"][0],
            "max_wind_speed_ms": seasonal_data.get("wind_speed", 5) * 2,
            "max_humidity_percent": seasonal_data["humidity_range"][1],
            "min_solar_days": 365 - seasonal_data["cloudy_days"]
        }
    
    def _recommend_life_support_systems(self, lss_data: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend life support systems based on environmental data"""
        return {
            "atmospheric_control": {
                "co2_scrubbers": "molecular_sieve" if lss_data["atmospheric_processing"]["co2_levels_ppm"] > 400 else "standard",
                "humidity_control": "active_dehumidification" if max(lss_data["atmospheric_processing"]["humidity_range"]) > 70 else "passive",
                "pressure_regulation": "active" if lss_data["atmospheric_processing"]["pressure_variation"] > 0.03 else "passive"
            },
            "thermal_systems": {
                "heating": "electric_resistance" if lss_data["thermal_management"]["temperature_extremes"][0] < -10 else "heat_pump",
                "cooling": "vapor_compression" if lss_data["thermal_management"]["temperature_extremes"][1] > 35 else "evaporative",
                "insulation": f"R-{lss_data['thermal_management']['insulation_r_value']}"
            },
            "power_systems": {
                "primary": "solar_array" if lss_data["power_generation"]["solar_availability"] > 4 else "hybrid",
                "backup": f"battery_{lss_data['power_generation']['backup_power_days']}_days",
                "efficiency_target": 0.85
            }
        }
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()


# Global service instance
planetary_computer_service = PlanetaryComputerService()