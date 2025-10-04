"""
Simulation API endpoints for crew workflow and emergency scenarios
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional, List
import logging

from ....services.crew_simulation import AgentSimulator, SimulationResults
from ....models.base import LayoutSpec, MissionParameters, ModulePlacement, ModuleType, PerformanceMetrics
from ....crud.layout import layout as layout_crud

logger = logging.getLogger(__name__)

router = APIRouter()


def _create_mock_layout(layout_id: str) -> LayoutSpec:
    """Create a mock layout for demonstration purposes"""
    mock_modules = [
        ModulePlacement(
            module_id="sleep_1",
            type=ModuleType.SLEEP_QUARTER,
            position=[0, 0, 0],
            rotation_deg=0,
            connections=["corridor_1"]
        ),
        ModulePlacement(
            module_id="galley_1",
            type=ModuleType.GALLEY,
            position=[4, 0, 0],
            rotation_deg=0,
            connections=["corridor_1"]
        ),
        ModulePlacement(
            module_id="corridor_1",
            type=ModuleType.STORAGE,
            position=[2, 0, 0],
            rotation_deg=0,
            connections=["sleep_1", "galley_1", "airlock_1"]
        ),
        ModulePlacement(
            module_id="airlock_1",
            type=ModuleType.AIRLOCK,
            position=[6, 0, 0],
            rotation_deg=0,
            connections=["corridor_1"]
        )
    ]
    
    mock_kpis = PerformanceMetrics(
        mean_transit_time=45.0,
        egress_time=120.0,
        mass_total=15000.0,
        power_budget=2500.0,
        thermal_margin=0.15,
        lss_margin=0.20,
        stowage_utilization=0.85
    )
    
    return LayoutSpec(
        layout_id=layout_id,
        envelope_id="mock_envelope",
        modules=mock_modules,
        kpis=mock_kpis,
        explainability="Mock layout for simulation testing"
    )


@router.post("/crew-workflow/{layout_id}")
async def simulate_crew_workflow(
    layout_id: str,
    mission_params: MissionParameters,
    simulation_duration_hours: float = 24.0
) -> Dict[str, Any]:
    """
    Run agent-based simulation of crew daily activities
    
    Args:
        layout_id: ID of the layout to simulate
        mission_params: Mission parameters including crew size and priorities
        simulation_duration_hours: Duration of simulation in hours (default 24)
        
    Returns:
        Simulation results including movement patterns, congestion analysis, etc.
    """
    try:
        # Get layout from database (using mock for demonstration)
        layout = _create_mock_layout(layout_id)
        
        # Initialize simulator
        simulator = AgentSimulator()
        
        # Run simulation
        results = await simulator.simulate_crew_workflow(
            layout=layout,
            mission_params=mission_params,
            simulation_duration_hours=simulation_duration_hours
        )
        
        # Convert results to API response format
        return {
            "layout_id": layout_id,
            "simulation_duration_hours": results.total_runtime_hours,
            "total_movement_events": len(results.movement_events),
            "crew_utilization": results.crew_utilization,
            "congestion_hotspots": results.congestion_hotspots,
            "heatmap_data": results.heatmap_data,
            "emergency_evacuation_times": results.emergency_evacuation_times,
            "module_occupancy_summary": {
                module_id: {
                    "max_occupancy": max(occ for _, occ in history) if history else 0,
                    "avg_occupancy": sum(occ for _, occ in history) / len(history) if history else 0
                }
                for module_id, history in results.module_occupancy.items()
            }
        }
        
    except Exception as e:
        logger.error(f"Crew workflow simulation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.post("/emergency-evacuation/{layout_id}")
async def simulate_emergency_evacuation(
    layout_id: str,
    mission_params: MissionParameters,
    emergency_type: str = "fire"
) -> Dict[str, Any]:
    """
    Simulate emergency evacuation scenarios
    
    Args:
        layout_id: ID of the layout to simulate
        mission_params: Mission parameters
        emergency_type: Type of emergency (fire, depressurization, etc.)
        
    Returns:
        Emergency evacuation analysis results
    """
    try:
        # Get layout from database (using mock for demonstration)
        layout = _create_mock_layout(layout_id)
        
        # Initialize simulator
        simulator = AgentSimulator()
        
        # Run emergency simulation
        results = await simulator.simulate_emergency_evacuation(
            layout=layout,
            mission_params=mission_params,
            emergency_type=emergency_type
        )
        
        return {
            "layout_id": layout_id,
            "emergency_type": emergency_type,
            "evacuation_analysis": results,
            "safety_assessment": {
                "max_evacuation_time_minutes": results["max_evacuation_time"],
                "average_evacuation_time_minutes": results["average_evacuation_time"],
                "safety_rating": "SAFE" if results["max_evacuation_time"] < 10 else "WARNING" if results["max_evacuation_time"] < 20 else "CRITICAL"
            }
        }
        
    except Exception as e:
        logger.error(f"Emergency evacuation simulation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Emergency simulation failed: {str(e)}")


@router.get("/heatmap/{layout_id}")
async def get_traffic_heatmap(
    layout_id: str,
    mission_params: MissionParameters,
    simulation_duration_hours: float = 24.0
) -> Dict[str, float]:
    """
    Generate traffic heatmap data for a layout
    
    Args:
        layout_id: ID of the layout
        mission_params: Mission parameters
        simulation_duration_hours: Duration to simulate
        
    Returns:
        Dictionary mapping module IDs to traffic intensity values
    """
    try:
        # Get layout from database (using mock for demonstration)
        layout = _create_mock_layout(layout_id)
        
        # Initialize simulator and run simulation
        simulator = AgentSimulator()
        results = await simulator.simulate_crew_workflow(
            layout=layout,
            mission_params=mission_params,
            simulation_duration_hours=simulation_duration_hours
        )
        
        # Return heatmap data
        return simulator.generate_heatmap_data(results)
        
    except Exception as e:
        logger.error(f"Heatmap generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Heatmap generation failed: {str(e)}")


@router.post("/congestion-analysis/{layout_id}")
async def analyze_congestion_patterns(
    layout_id: str,
    mission_params: MissionParameters,
    simulation_duration_hours: float = 24.0
) -> Dict[str, Any]:
    """
    Analyze congestion patterns and bottlenecks in a layout
    
    Args:
        layout_id: ID of the layout to analyze
        mission_params: Mission parameters
        simulation_duration_hours: Duration to simulate
        
    Returns:
        Congestion analysis results including bottlenecks and peak usage times
    """
    try:
        # Get layout from database (using mock for demonstration)
        layout = _create_mock_layout(layout_id)
        
        # Initialize simulator and run simulation
        simulator = AgentSimulator()
        results = await simulator.simulate_crew_workflow(
            layout=layout,
            mission_params=mission_params,
            simulation_duration_hours=simulation_duration_hours
        )
        
        # Analyze congestion patterns
        congestion_analysis = simulator.analyze_congestion_patterns(results)
        
        return {
            "layout_id": layout_id,
            "analysis_duration_hours": simulation_duration_hours,
            "congestion_analysis": congestion_analysis,
            "recommendations": _generate_congestion_recommendations(congestion_analysis)
        }
        
    except Exception as e:
        logger.error(f"Congestion analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Congestion analysis failed: {str(e)}")


def _generate_congestion_recommendations(analysis: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on congestion analysis"""
    recommendations = []
    
    if analysis.get("bottlenecks"):
        most_congested = max(analysis["bottlenecks"].items(), key=lambda x: x[1])
        recommendations.append(
            f"Consider expanding capacity or adding alternative routes near {most_congested[0]} "
            f"(congestion score: {most_congested[1]:.2f})"
        )
    
    if analysis.get("peak_congestion"):
        peak_modules = [
            module_id for module_id, data in analysis["peak_congestion"].items()
            if data["max_occupancy"] > 4
        ]
        if peak_modules:
            recommendations.append(
                f"High occupancy detected in modules: {', '.join(peak_modules)}. "
                "Consider staggering crew schedules or adding capacity."
            )
    
    if analysis.get("total_congestion_events", 0) > 10:
        recommendations.append(
            "High number of congestion events detected. "
            "Consider redesigning traffic flow patterns or module placement."
        )
    
    if not recommendations:
        recommendations.append("No significant congestion issues detected. Layout appears well-optimized for crew flow.")
    
    return recommendations