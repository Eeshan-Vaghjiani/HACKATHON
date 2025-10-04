"""
Seed data for the HabitatCanvas database
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import ModuleLibrary
from app.models.base import ModuleType
import logging

logger = logging.getLogger(__name__)


async def seed_module_library(db: AsyncSession) -> None:
    """Seed the module library with standard habitat modules"""
    
    # Standard habitat modules based on ISS and future habitat designs
    modules_data = [
        {
            "module_id": "sleep_quarter_std",
            "type": ModuleType.SLEEP_QUARTER.value,
            "name": "Standard Sleep Quarter",
            "bbox_x": 2.0,
            "bbox_y": 2.0,
            "bbox_z": 2.5,
            "mass_kg": 450.0,
            "power_w": 75.0,
            "stowage_m3": 1.2,
            "connectivity_ports": ["port_main", "port_emergency"],
            "adjacency_preferences": [ModuleType.GALLEY.value, ModuleType.MEDICAL.value],
            "adjacency_restrictions": [ModuleType.MECHANICAL.value, ModuleType.AIRLOCK.value],
            "description": "Individual crew sleeping quarters with privacy partition and personal storage",
            "manufacturer": "SpaceHab Systems",
            "model": "SQ-2024",
            "certification": "NASA-STD-3001"
        },
        {
            "module_id": "galley_main",
            "type": ModuleType.GALLEY.value,
            "name": "Main Galley Module",
            "bbox_x": 3.0,
            "bbox_y": 2.5,
            "bbox_z": 2.5,
            "mass_kg": 800.0,
            "power_w": 2500.0,
            "stowage_m3": 2.5,
            "connectivity_ports": ["port_main", "port_utility", "port_waste"],
            "adjacency_preferences": [ModuleType.SLEEP_QUARTER.value, ModuleType.LABORATORY.value],
            "adjacency_restrictions": [ModuleType.MECHANICAL.value],
            "description": "Food preparation and dining area with water recycling and waste management",
            "manufacturer": "Orbital Dynamics",
            "model": "GAL-300",
            "certification": "NASA-STD-3001"
        },
        {
            "module_id": "lab_science",
            "type": ModuleType.LABORATORY.value,
            "name": "Science Laboratory",
            "bbox_x": 4.0,
            "bbox_y": 2.5,
            "bbox_z": 2.5,
            "mass_kg": 1200.0,
            "power_w": 1800.0,
            "stowage_m3": 3.0,
            "connectivity_ports": ["port_main", "port_data", "port_utility"],
            "adjacency_preferences": [ModuleType.GALLEY.value, ModuleType.STORAGE.value],
            "adjacency_restrictions": [ModuleType.EXERCISE.value, ModuleType.MECHANICAL.value],
            "description": "Multi-purpose laboratory with workbenches, microscopy, and sample storage",
            "manufacturer": "Research Systems Inc",
            "model": "LAB-450",
            "certification": "NASA-STD-3001"
        },
        {
            "module_id": "airlock_eva",
            "type": ModuleType.AIRLOCK.value,
            "name": "EVA Airlock",
            "bbox_x": 2.5,
            "bbox_y": 2.5,
            "bbox_z": 3.0,
            "mass_kg": 900.0,
            "power_w": 500.0,
            "stowage_m3": 1.8,
            "connectivity_ports": ["port_internal", "port_external"],
            "adjacency_preferences": [ModuleType.STORAGE.value, ModuleType.MECHANICAL.value],
            "adjacency_restrictions": [ModuleType.SLEEP_QUARTER.value, ModuleType.GALLEY.value],
            "description": "Extravehicular activity airlock with suit storage and pre-breathing area",
            "manufacturer": "Aerospace Dynamics",
            "model": "AL-EVA-200",
            "certification": "NASA-STD-3001"
        },
        {
            "module_id": "mechanical_lss",
            "type": ModuleType.MECHANICAL.value,
            "name": "Life Support Systems",
            "bbox_x": 3.5,
            "bbox_y": 2.5,
            "bbox_z": 2.5,
            "mass_kg": 1500.0,
            "power_w": 3000.0,
            "stowage_m3": 0.5,
            "connectivity_ports": ["port_main", "port_utility_1", "port_utility_2", "port_emergency"],
            "adjacency_preferences": [ModuleType.AIRLOCK.value, ModuleType.STORAGE.value],
            "adjacency_restrictions": [ModuleType.SLEEP_QUARTER.value, ModuleType.GALLEY.value, ModuleType.LABORATORY.value],
            "description": "Environmental control, life support, and power distribution systems",
            "manufacturer": "Life Support Technologies",
            "model": "LSS-500",
            "certification": "NASA-STD-3001"
        },
        {
            "module_id": "medical_bay",
            "type": ModuleType.MEDICAL.value,
            "name": "Medical Bay",
            "bbox_x": 3.0,
            "bbox_y": 2.5,
            "bbox_z": 2.5,
            "mass_kg": 700.0,
            "power_w": 800.0,
            "stowage_m3": 2.0,
            "connectivity_ports": ["port_main", "port_emergency"],
            "adjacency_preferences": [ModuleType.SLEEP_QUARTER.value, ModuleType.GALLEY.value],
            "adjacency_restrictions": [ModuleType.MECHANICAL.value, ModuleType.EXERCISE.value],
            "description": "Medical examination and treatment facility with emergency care capabilities",
            "manufacturer": "Medical Systems Corp",
            "model": "MED-250",
            "certification": "NASA-STD-3001"
        },
        {
            "module_id": "exercise_gym",
            "type": ModuleType.EXERCISE.value,
            "name": "Exercise Module",
            "bbox_x": 3.5,
            "bbox_y": 3.0,
            "bbox_z": 2.5,
            "mass_kg": 600.0,
            "power_w": 400.0,
            "stowage_m3": 1.5,
            "connectivity_ports": ["port_main"],
            "adjacency_preferences": [ModuleType.STORAGE.value],
            "adjacency_restrictions": [ModuleType.LABORATORY.value, ModuleType.MEDICAL.value, ModuleType.MECHANICAL.value],
            "description": "Exercise equipment and fitness area for crew health maintenance",
            "manufacturer": "Fitness Systems Ltd",
            "model": "EX-300",
            "certification": "NASA-STD-3001"
        },
        {
            "module_id": "storage_general",
            "type": ModuleType.STORAGE.value,
            "name": "General Storage",
            "bbox_x": 2.5,
            "bbox_y": 2.0,
            "bbox_z": 2.5,
            "mass_kg": 300.0,
            "power_w": 50.0,
            "stowage_m3": 8.0,
            "connectivity_ports": ["port_main"],
            "adjacency_preferences": [ModuleType.AIRLOCK.value, ModuleType.MECHANICAL.value, ModuleType.LABORATORY.value],
            "adjacency_restrictions": [],
            "description": "General purpose storage for supplies, equipment, and consumables",
            "manufacturer": "Storage Solutions Inc",
            "model": "ST-200",
            "certification": "NASA-STD-3001"
        }
    ]
    
    try:
        # Check if modules already exist
        for module_data in modules_data:
            # Calculate computed fields
            module_data["volume"] = module_data["bbox_x"] * module_data["bbox_y"] * module_data["bbox_z"]
            module_data["density_kg_m3"] = module_data["mass_kg"] / module_data["volume"]
            module_data["power_density_w_m3"] = module_data["power_w"] / module_data["volume"]
            
            # Create module if it doesn't exist
            existing = await db.get(ModuleLibrary, module_data["module_id"])
            if not existing:
                module = ModuleLibrary(**module_data)
                db.add(module)
                logger.info(f"Added module: {module_data['name']}")
        
        await db.commit()
        logger.info("Module library seeded successfully")
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error seeding module library: {e}")
        raise


async def seed_database(db: AsyncSession) -> None:
    """Seed the entire database with initial data"""
    logger.info("Starting database seeding...")
    
    try:
        await seed_module_library(db)
        logger.info("Database seeding completed successfully")
    except Exception as e:
        logger.error(f"Database seeding failed: {e}")
        raise