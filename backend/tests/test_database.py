"""
Unit tests for database models and CRUD operations
"""
import pytest
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.database import Envelope, ModuleLibrary, Layout
from app.models.base import (
    EnvelopeSpec, EnvelopeType, CoordinateFrame, EnvelopeMetadata,
    ModuleSpec, ModuleType, BoundingBox,
    LayoutSpec, PerformanceMetrics, ModulePlacement
)
from app.crud import envelope as crud_envelope
from app.crud import module_library as crud_module
from app.crud import layout as crud_layout


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    """Create a test database session"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def sample_envelope_spec():
    """Create a sample envelope specification"""
    metadata = EnvelopeMetadata(
        name="Test Cylinder",
        creator="test_user",
        created=datetime(2024, 1, 1),
        version="1.0",
        description="Test cylinder envelope"
    )
    
    return EnvelopeSpec(
        id="test_env_001",
        type=EnvelopeType.CYLINDER,
        params={"radius": 3.0, "length": 12.0},
        coordinate_frame=CoordinateFrame.LOCAL,
        metadata=metadata
    )


@pytest.fixture
def sample_module_spec():
    """Create a sample module specification"""
    return ModuleSpec(
        module_id="test_mod_001",
        type=ModuleType.SLEEP_QUARTER,
        name="Test Sleep Quarter",
        bbox_m=BoundingBox(x=2.0, y=2.0, z=2.5),
        mass_kg=500.0,
        power_w=100.0,
        stowage_m3=5.0,
        connectivity_ports=["port1", "port2"],
        adjacency_preferences=[ModuleType.GALLEY],
        adjacency_restrictions=[ModuleType.MECHANICAL]
    )


@pytest.fixture
def sample_layout_spec(sample_envelope_spec):
    """Create a sample layout specification"""
    module_placement = ModulePlacement(
        module_id="test_mod_001",
        type=ModuleType.SLEEP_QUARTER,
        position=[1.0, 2.0, 3.0],
        rotation_deg=45.0,
        connections=[]
    )
    
    metrics = PerformanceMetrics(
        mean_transit_time=30.5,
        egress_time=120.0,
        mass_total=15000.0,
        power_budget=5000.0,
        thermal_margin=0.25,
        lss_margin=0.30,
        stowage_utilization=0.85
    )
    
    return LayoutSpec(
        layout_id="test_layout_001",
        envelope_id=sample_envelope_spec.id,
        modules=[module_placement],
        kpis=metrics,
        explainability="Test layout for database validation"
    )


# ============================================================================
# DATABASE MODEL TESTS
# ============================================================================

class TestDatabaseModels:
    """Test SQLAlchemy database models"""
    
    @pytest.mark.asyncio
    async def test_envelope_model_creation(self, db_session: AsyncSession):
        """Test creating an envelope in the database"""
        envelope = Envelope(
            id="test_env_001",
            name="Test Envelope",
            type="cylinder",
            params={"radius": 3.0, "length": 12.0},
            coordinate_frame="local",
            creator="test_user",
            volume=339.29  # π * 3² * 12
        )
        
        db_session.add(envelope)
        await db_session.commit()
        await db_session.refresh(envelope)
        
        assert envelope.id == "test_env_001"
        assert envelope.name == "Test Envelope"
        assert envelope.type == "cylinder"
        assert envelope.params["radius"] == 3.0
        assert envelope.created_at is not None
        assert envelope.updated_at is not None

    @pytest.mark.asyncio
    async def test_module_library_model_creation(self, db_session: AsyncSession):
        """Test creating a module in the database"""
        module = ModuleLibrary(
            module_id="test_mod_001",
            type="sleep_quarter",
            name="Test Sleep Quarter",
            bbox_x=2.0,
            bbox_y=2.0,
            bbox_z=2.5,
            mass_kg=500.0,
            power_w=100.0,
            stowage_m3=5.0,
            connectivity_ports=["port1", "port2"],
            adjacency_preferences=["galley"],
            adjacency_restrictions=["mechanical"],
            volume=10.0,  # 2 * 2 * 2.5
            density_kg_m3=50.0,  # 500 / 10
            power_density_w_m3=10.0  # 100 / 10
        )
        
        db_session.add(module)
        await db_session.commit()
        await db_session.refresh(module)
        
        assert module.module_id == "test_mod_001"
        assert module.type == "sleep_quarter"
        assert module.volume == 10.0
        assert module.density_kg_m3 == 50.0
        assert module.created_at is not None

    @pytest.mark.asyncio
    async def test_layout_model_creation(self, db_session: AsyncSession):
        """Test creating a layout in the database"""
        # First create an envelope
        envelope = Envelope(
            id="test_env_001",
            name="Test Envelope",
            type="cylinder",
            params={"radius": 3.0, "length": 12.0},
            coordinate_frame="local",
            creator="test_user"
        )
        db_session.add(envelope)
        await db_session.commit()
        
        # Then create a layout
        layout = Layout(
            layout_id="test_layout_001",
            envelope_id="test_env_001",
            name="Test Layout",
            modules=[{
                "module_id": "test_mod_001",
                "type": "sleep_quarter",
                "position": [1.0, 2.0, 3.0],
                "rotation_deg": 45.0,
                "connections": []
            }],
            explainability="Test layout explanation",
            mean_transit_time=30.5,
            egress_time=120.0,
            mass_total=15000.0,
            power_budget=5000.0,
            thermal_margin=0.25,
            lss_margin=0.30,
            stowage_utilization=0.85,
            module_count=1,
            has_airlock=False
        )
        
        db_session.add(layout)
        await db_session.commit()
        await db_session.refresh(layout)
        
        assert layout.layout_id == "test_layout_001"
        assert layout.envelope_id == "test_env_001"
        assert len(layout.modules) == 1
        assert layout.module_count == 1
        assert layout.created_at is not None


# ============================================================================
# CRUD OPERATION TESTS
# ============================================================================

class TestEnvelopeCRUD:
    """Test envelope CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_create_envelope_from_spec(self, db_session: AsyncSession, sample_envelope_spec: EnvelopeSpec):
        """Test creating an envelope from a Pydantic spec"""
        envelope = await crud_envelope.create_from_spec(db_session, envelope_spec=sample_envelope_spec)
        
        assert envelope.id == sample_envelope_spec.id
        assert envelope.name == sample_envelope_spec.metadata.name
        assert envelope.type == sample_envelope_spec.type.value
        assert envelope.params == sample_envelope_spec.params
        assert envelope.volume == sample_envelope_spec.volume

    @pytest.mark.asyncio
    async def test_get_envelope_by_id(self, db_session: AsyncSession, sample_envelope_spec: EnvelopeSpec):
        """Test retrieving an envelope by ID"""
        # Create envelope
        created_envelope = await crud_envelope.create_from_spec(db_session, envelope_spec=sample_envelope_spec)
        
        # Retrieve envelope
        retrieved_envelope = await crud_envelope.get(db_session, id=sample_envelope_spec.id)
        
        assert retrieved_envelope is not None
        assert retrieved_envelope.id == created_envelope.id
        assert retrieved_envelope.name == created_envelope.name

    @pytest.mark.asyncio
    async def test_get_envelope_by_name(self, db_session: AsyncSession, sample_envelope_spec: EnvelopeSpec):
        """Test retrieving an envelope by name"""
        # Create envelope
        await crud_envelope.create_from_spec(db_session, envelope_spec=sample_envelope_spec)
        
        # Retrieve by name
        retrieved_envelope = await crud_envelope.get_by_name(db_session, name=sample_envelope_spec.metadata.name)
        
        assert retrieved_envelope is not None
        assert retrieved_envelope.name == sample_envelope_spec.metadata.name

    @pytest.mark.asyncio
    async def test_update_envelope_from_spec(self, db_session: AsyncSession, sample_envelope_spec: EnvelopeSpec):
        """Test updating an envelope from a Pydantic spec"""
        # Create envelope
        await crud_envelope.create_from_spec(db_session, envelope_spec=sample_envelope_spec)
        
        # Modify spec
        sample_envelope_spec.metadata.name = "Updated Test Cylinder"
        sample_envelope_spec.params["radius"] = 4.0
        
        # Update envelope
        updated_envelope = await crud_envelope.update_from_spec(
            db_session, 
            envelope_id=sample_envelope_spec.id, 
            envelope_spec=sample_envelope_spec
        )
        
        assert updated_envelope is not None
        assert updated_envelope.name == "Updated Test Cylinder"
        assert updated_envelope.params["radius"] == 4.0

    @pytest.mark.asyncio
    async def test_delete_envelope(self, db_session: AsyncSession, sample_envelope_spec: EnvelopeSpec):
        """Test deleting an envelope"""
        # Create envelope
        await crud_envelope.create_from_spec(db_session, envelope_spec=sample_envelope_spec)
        
        # Delete envelope
        deleted_envelope = await crud_envelope.remove(db_session, id=sample_envelope_spec.id)
        
        assert deleted_envelope is not None
        
        # Verify deletion
        retrieved_envelope = await crud_envelope.get(db_session, id=sample_envelope_spec.id)
        assert retrieved_envelope is None

    @pytest.mark.asyncio
    async def test_search_envelopes_by_type(self, db_session: AsyncSession):
        """Test searching envelopes by type"""
        # Create multiple envelopes of different types
        cylinder_spec = EnvelopeSpec(
            id="cylinder_001",
            type=EnvelopeType.CYLINDER,
            params={"radius": 3.0, "length": 12.0},
            coordinate_frame=CoordinateFrame.LOCAL,
            metadata=EnvelopeMetadata(name="Cylinder", creator="test")
        )
        
        box_spec = EnvelopeSpec(
            id="box_001",
            type=EnvelopeType.BOX,
            params={"width": 5.0, "height": 3.0, "depth": 8.0},
            coordinate_frame=CoordinateFrame.LOCAL,
            metadata=EnvelopeMetadata(name="Box", creator="test")
        )
        
        await crud_envelope.create_from_spec(db_session, envelope_spec=cylinder_spec)
        await crud_envelope.create_from_spec(db_session, envelope_spec=box_spec)
        
        # Search for cylinders
        cylinders = await crud_envelope.search_by_type(db_session, envelope_type="cylinder")
        assert len(cylinders) == 1
        assert cylinders[0].type == "cylinder"
        
        # Search for boxes
        boxes = await crud_envelope.search_by_type(db_session, envelope_type="box")
        assert len(boxes) == 1
        assert boxes[0].type == "box"


class TestModuleCRUD:
    """Test module library CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_create_module_from_spec(self, db_session: AsyncSession, sample_module_spec: ModuleSpec):
        """Test creating a module from a Pydantic spec"""
        module = await crud_module.create_from_spec(db_session, module_spec=sample_module_spec)
        
        assert module.module_id == sample_module_spec.module_id
        assert module.type == sample_module_spec.type.value
        assert module.name == sample_module_spec.name
        assert module.mass_kg == sample_module_spec.mass_kg
        assert module.volume == sample_module_spec.bbox_m.volume

    @pytest.mark.asyncio
    async def test_get_modules_by_type(self, db_session: AsyncSession):
        """Test retrieving modules by type"""
        # Create modules of different types
        sleep_spec = ModuleSpec(
            module_id="sleep_001",
            type=ModuleType.SLEEP_QUARTER,
            name="Sleep Quarter",
            bbox_m=BoundingBox(x=2.0, y=2.0, z=2.5),
            mass_kg=500.0,
            power_w=100.0,
            stowage_m3=5.0
        )
        
        galley_spec = ModuleSpec(
            module_id="galley_001",
            type=ModuleType.GALLEY,
            name="Galley",
            bbox_m=BoundingBox(x=3.0, y=2.0, z=2.5),
            mass_kg=800.0,
            power_w=500.0,
            stowage_m3=8.0
        )
        
        await crud_module.create_from_spec(db_session, module_spec=sleep_spec)
        await crud_module.create_from_spec(db_session, module_spec=galley_spec)
        
        # Get sleep quarters
        sleep_modules = await crud_module.get_by_type(db_session, module_type=ModuleType.SLEEP_QUARTER)
        assert len(sleep_modules) == 1
        assert sleep_modules[0].type == "sleep_quarter"
        
        # Get galleys
        galley_modules = await crud_module.get_by_type(db_session, module_type=ModuleType.GALLEY)
        assert len(galley_modules) == 1
        assert galley_modules[0].type == "galley"

    @pytest.mark.asyncio
    async def test_search_modules_by_mass_range(self, db_session: AsyncSession):
        """Test searching modules by mass range"""
        # Create modules with different masses
        light_module = ModuleSpec(
            module_id="light_001",
            type=ModuleType.STORAGE,
            name="Light Storage",
            bbox_m=BoundingBox(x=1.0, y=1.0, z=1.0),
            mass_kg=200.0,
            power_w=50.0,
            stowage_m3=0.8
        )
        
        heavy_module = ModuleSpec(
            module_id="heavy_001",
            type=ModuleType.MECHANICAL,
            name="Heavy Mechanical",
            bbox_m=BoundingBox(x=3.0, y=3.0, z=3.0),
            mass_kg=1500.0,
            power_w=3000.0,
            stowage_m3=1.0
        )
        
        await crud_module.create_from_spec(db_session, module_spec=light_module)
        await crud_module.create_from_spec(db_session, module_spec=heavy_module)
        
        # Search for modules between 100-500 kg
        light_modules = await crud_module.search_by_mass_range(db_session, min_mass=100.0, max_mass=500.0)
        assert len(light_modules) == 1
        assert light_modules[0].mass_kg == 200.0
        
        # Search for modules over 1000 kg
        heavy_modules = await crud_module.search_by_mass_range(db_session, min_mass=1000.0)
        assert len(heavy_modules) == 1
        assert heavy_modules[0].mass_kg == 1500.0


class TestLayoutCRUD:
    """Test layout CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_create_layout_from_spec(
        self, 
        db_session: AsyncSession, 
        sample_envelope_spec: EnvelopeSpec,
        sample_layout_spec: LayoutSpec
    ):
        """Test creating a layout from a Pydantic spec"""
        # First create the envelope
        await crud_envelope.create_from_spec(db_session, envelope_spec=sample_envelope_spec)
        
        # Then create the layout
        layout = await crud_layout.create_from_spec(db_session, layout_spec=sample_layout_spec)
        
        assert layout.layout_id == sample_layout_spec.layout_id
        assert layout.envelope_id == sample_layout_spec.envelope_id
        assert len(layout.modules) == len(sample_layout_spec.modules)
        assert layout.mean_transit_time == sample_layout_spec.kpis.mean_transit_time

    @pytest.mark.asyncio
    async def test_get_layouts_by_envelope(
        self, 
        db_session: AsyncSession, 
        sample_envelope_spec: EnvelopeSpec,
        sample_layout_spec: LayoutSpec
    ):
        """Test retrieving layouts by envelope ID"""
        # Create envelope and layout
        await crud_envelope.create_from_spec(db_session, envelope_spec=sample_envelope_spec)
        await crud_layout.create_from_spec(db_session, layout_spec=sample_layout_spec)
        
        # Get layouts for envelope
        layouts = await crud_layout.get_by_envelope(db_session, envelope_id=sample_envelope_spec.id)
        
        assert len(layouts) == 1
        assert layouts[0].envelope_id == sample_envelope_spec.id

    @pytest.mark.asyncio
    async def test_update_layout_metrics(
        self, 
        db_session: AsyncSession, 
        sample_envelope_spec: EnvelopeSpec,
        sample_layout_spec: LayoutSpec
    ):
        """Test updating layout performance metrics"""
        # Create envelope and layout
        await crud_envelope.create_from_spec(db_session, envelope_spec=sample_envelope_spec)
        await crud_layout.create_from_spec(db_session, layout_spec=sample_layout_spec)
        
        # Update metrics
        new_metrics = PerformanceMetrics(
            mean_transit_time=25.0,  # Improved
            egress_time=100.0,  # Improved
            mass_total=14000.0,  # Reduced
            power_budget=4500.0,  # Reduced
            thermal_margin=0.35,  # Improved
            lss_margin=0.40,  # Improved
            stowage_utilization=0.80  # Optimized
        )
        
        updated_layout = await crud_layout.update_metrics(
            db_session, 
            layout_id=sample_layout_spec.layout_id, 
            metrics=new_metrics
        )
        
        assert updated_layout is not None
        assert updated_layout.mean_transit_time == 25.0
        assert updated_layout.thermal_margin == 0.35
        assert updated_layout.overall_score > sample_layout_spec.kpis.overall_score  # Should be better


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestDatabaseIntegration:
    """Test integration between different database models"""
    
    @pytest.mark.asyncio
    async def test_envelope_layout_relationship(
        self, 
        db_session: AsyncSession, 
        sample_envelope_spec: EnvelopeSpec,
        sample_layout_spec: LayoutSpec
    ):
        """Test the relationship between envelopes and layouts"""
        # Create envelope
        envelope = await crud_envelope.create_from_spec(db_session, envelope_spec=sample_envelope_spec)
        
        # Create layout
        layout = await crud_layout.create_from_spec(db_session, layout_spec=sample_layout_spec)
        
        # Get envelope with layouts
        envelope_with_layouts = await crud_envelope.get_with_layouts(
            db_session, 
            envelope_id=sample_envelope_spec.id
        )
        
        assert envelope_with_layouts is not None
        assert len(envelope_with_layouts.layouts) == 1
        assert envelope_with_layouts.layouts[0].layout_id == layout.layout_id

    @pytest.mark.asyncio
    async def test_cascade_delete_envelope_layouts(
        self, 
        db_session: AsyncSession, 
        sample_envelope_spec: EnvelopeSpec,
        sample_layout_spec: LayoutSpec
    ):
        """Test that deleting an envelope cascades to delete its layouts"""
        # Create envelope and layout
        await crud_envelope.create_from_spec(db_session, envelope_spec=sample_envelope_spec)
        await crud_layout.create_from_spec(db_session, layout_spec=sample_layout_spec)
        
        # Verify layout exists
        layout = await crud_layout.get(db_session, id=sample_layout_spec.layout_id)
        assert layout is not None
        
        # Delete envelope
        await crud_envelope.remove(db_session, id=sample_envelope_spec.id)
        
        # Verify layout is also deleted (cascade)
        layout_after_delete = await crud_layout.get(db_session, id=sample_layout_spec.layout_id)
        assert layout_after_delete is None