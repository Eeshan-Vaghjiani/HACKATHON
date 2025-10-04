from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.base import Base


class Envelope(Base):
    """Database model for habitat envelopes"""
    __tablename__ = "envelopes"

    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # cylinder, torus, box, freeform
    params = Column(JSON, nullable=False)  # Type-specific geometric parameters
    coordinate_frame = Column(String(50), nullable=False, default="local")
    
    # Metadata fields
    creator = Column(String(255), nullable=False)
    version = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    
    # Constraints (optional)
    min_volume = Column(Float, nullable=True)
    max_volume = Column(Float, nullable=True)
    min_dimension = Column(Float, nullable=True)
    max_dimension = Column(Float, nullable=True)
    
    # Computed fields
    volume = Column(Float, nullable=True)  # Calculated volume
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    layouts = relationship("Layout", back_populates="envelope", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Envelope(id='{self.id}', name='{self.name}', type='{self.type}')>"


class ModuleLibrary(Base):
    """Database model for module specifications in the library"""
    __tablename__ = "module_library"

    module_id = Column(String(255), primary_key=True)
    type = Column(String(50), nullable=False, index=True)  # sleep_quarter, galley, etc.
    name = Column(String(255), nullable=False)
    
    # Bounding box dimensions
    bbox_x = Column(Float, nullable=False)  # Width in meters
    bbox_y = Column(Float, nullable=False)  # Height in meters
    bbox_z = Column(Float, nullable=False)  # Depth in meters
    
    # Physical properties
    mass_kg = Column(Float, nullable=False)
    power_w = Column(Float, nullable=False)
    stowage_m3 = Column(Float, nullable=False)
    
    # Connectivity and adjacency
    connectivity_ports = Column(JSON, nullable=False, default=list)  # List of port names
    adjacency_preferences = Column(JSON, nullable=False, default=list)  # Preferred module types
    adjacency_restrictions = Column(JSON, nullable=False, default=list)  # Restricted module types
    
    # Metadata (optional)
    description = Column(Text, nullable=True)
    manufacturer = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    certification = Column(String(255), nullable=True)
    
    # Computed properties
    volume = Column(Float, nullable=True)  # bbox_x * bbox_y * bbox_z
    density_kg_m3 = Column(Float, nullable=True)  # mass_kg / volume
    power_density_w_m3 = Column(Float, nullable=True)  # power_w / volume
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<ModuleLibrary(module_id='{self.module_id}', type='{self.type}', name='{self.name}')>"


class Layout(Base):
    """Database model for habitat layouts"""
    __tablename__ = "layouts"

    layout_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    envelope_id = Column(String(255), ForeignKey("envelopes.id"), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    
    # Layout data
    modules = Column(JSON, nullable=False)  # List of ModulePlacement objects
    explainability = Column(Text, nullable=False)
    
    # Performance metrics
    mean_transit_time = Column(Float, nullable=False)
    egress_time = Column(Float, nullable=False)
    mass_total = Column(Float, nullable=False)
    power_budget = Column(Float, nullable=False)
    thermal_margin = Column(Float, nullable=False)
    lss_margin = Column(Float, nullable=False)
    stowage_utilization = Column(Float, nullable=False)
    
    # Optional metrics
    connectivity_score = Column(Float, nullable=True)
    safety_score = Column(Float, nullable=True)
    efficiency_score = Column(Float, nullable=True)
    volume_utilization = Column(Float, nullable=True)
    
    # Generation metadata
    generation_params = Column(JSON, nullable=True)  # Parameters used for generation
    version = Column(String(50), nullable=True)
    
    # Constraints (optional)
    total_mass_constraint = Column(Float, nullable=True)
    total_power_constraint = Column(Float, nullable=True)
    min_clearance_constraint = Column(Float, nullable=True)
    
    # Computed fields
    module_count = Column(Integer, nullable=True)
    module_types_count = Column(JSON, nullable=True)  # Dict of type counts
    has_airlock = Column(Boolean, nullable=True)
    layout_bounds = Column(JSON, nullable=True)  # Bounding box coordinates
    overall_score = Column(Float, nullable=True)  # Computed overall performance score
    critical_issues = Column(JSON, nullable=True)  # List of critical issue strings
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    envelope = relationship("Envelope", back_populates="layouts")
    simulation_results = relationship("SimulationResult", back_populates="layout", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Layout(layout_id='{self.layout_id}', envelope_id='{self.envelope_id}', name='{self.name}')>"


class SimulationResult(Base):
    """Database model for agent simulation results"""
    __tablename__ = "simulation_results"

    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    layout_id = Column(String(255), ForeignKey("layouts.layout_id"), nullable=False, index=True)
    simulation_type = Column(String(50), nullable=False, index=True)  # crew_workflow, emergency, etc.
    
    # Simulation parameters
    simulation_params = Column(JSON, nullable=True)  # Parameters used for simulation
    
    # Results data
    results = Column(JSON, nullable=False)  # Simulation output data
    
    # Summary metrics
    duration_simulated = Column(Float, nullable=True)  # Simulated time in hours
    agents_count = Column(Integer, nullable=True)  # Number of agents simulated
    
    # Performance indicators
    avg_congestion = Column(Float, nullable=True)  # Average congestion level
    max_queue_time = Column(Float, nullable=True)  # Maximum queuing time in seconds
    bottleneck_locations = Column(JSON, nullable=True)  # List of bottleneck coordinates
    
    # Heatmap data
    traffic_heatmap = Column(JSON, nullable=True)  # Traffic density data
    occupancy_heatmap = Column(JSON, nullable=True)  # Module occupancy data
    
    # Status and metadata
    status = Column(String(50), nullable=False, default="completed")  # running, completed, failed
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    layout = relationship("Layout", back_populates="simulation_results")

    def __repr__(self):
        return f"<SimulationResult(id='{self.id}', layout_id='{self.layout_id}', type='{self.simulation_type}')>"


class MissionProfile(Base):
    """Database model for mission parameters and profiles"""
    __tablename__ = "mission_profiles"

    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Mission parameters
    crew_size = Column(Integer, nullable=False)
    duration_days = Column(Integer, nullable=False)
    
    # Priority weights (stored as JSON for flexibility)
    priority_weights = Column(JSON, nullable=False)  # Dict of priority weights
    activity_schedule = Column(JSON, nullable=False)  # Dict of activity time allocations
    emergency_scenarios = Column(JSON, nullable=False)  # List of emergency scenario names
    
    # Constraints (optional)
    max_crew_size = Column(Integer, nullable=True)
    max_duration = Column(Integer, nullable=True)
    min_safety_margin = Column(Float, nullable=True)
    
    # Computed fields
    total_crew_hours = Column(Float, nullable=True)  # crew_size * duration_days * 24
    daily_activity_total = Column(Float, nullable=True)  # Sum of activity_schedule values
    
    # Template information
    is_template = Column(Boolean, nullable=False, default=False)
    template_category = Column(String(100), nullable=True)  # mars, moon, iss, etc.
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<MissionProfile(id='{self.id}', name='{self.name}', crew_size={self.crew_size})>"


class ExportJob(Base):
    """Database model for tracking export jobs"""
    __tablename__ = "export_jobs"

    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    layout_id = Column(String(255), ForeignKey("layouts.layout_id"), nullable=False, index=True)
    export_type = Column(String(50), nullable=False)  # gltf, json, pdf, png, step, iges
    
    # Job status
    status = Column(String(50), nullable=False, default="pending")  # pending, processing, completed, failed
    progress = Column(Float, nullable=False, default=0.0)  # 0.0 to 1.0
    
    # Export parameters
    export_params = Column(JSON, nullable=True)  # Export-specific parameters
    
    # Results
    file_path = Column(String(500), nullable=True)  # Path to exported file
    file_size = Column(Integer, nullable=True)  # File size in bytes
    download_url = Column(String(500), nullable=True)  # URL for downloading
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # When download expires

    def __repr__(self):
        return f"<ExportJob(id='{self.id}', layout_id='{self.layout_id}', type='{self.export_type}', status='{self.status}')>"