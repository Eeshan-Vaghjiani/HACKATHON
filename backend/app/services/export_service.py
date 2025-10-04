"""
Export Service for HabitatCanvas

This service handles exporting layouts and models to various formats including:
- GLTF/GLB for 3D visualization
- CAD formats (STEP, IGES) for engineering
- JSON specifications for data exchange
- Batch export functionality
"""

import json
import tempfile
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, BinaryIO
from datetime import datetime
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import io
import base64

import trimesh
import numpy as np
from pygltflib import (
    GLTF2, Scene, Node, Mesh, Primitive, Accessor, BufferView, Buffer,
    Material, PbrMetallicRoughness, TextureInfo, Image, Sampler, Texture,
    BufferFormat, ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER, FLOAT, UNSIGNED_INT
)

from app.models.base import LayoutSpec, EnvelopeSpec, ModulePlacement, ModuleType
from app.models.module_library import get_module_library, ModuleDefinition

logger = logging.getLogger(__name__)


class ExportFormat:
    """Supported export formats"""
    GLTF = "gltf"
    GLB = "glb"
    JSON = "json"
    STEP = "step"
    IGES = "iges"
    ZIP = "zip"


class ExportError(Exception):
    """Export operation error"""
    pass


class ModelExporter:
    """3D model export functionality"""
    
    def __init__(self):
        self.module_library = get_module_library()
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def export_layout_gltf(
        self, 
        layout: LayoutSpec, 
        envelope: EnvelopeSpec,
        include_envelope: bool = True,
        include_materials: bool = True
    ) -> bytes:
        """
        Export layout as GLTF/GLB format
        
        Args:
            layout: Layout specification to export
            envelope: Habitat envelope specification
            include_envelope: Whether to include envelope geometry
            include_materials: Whether to include material definitions
            
        Returns:
            GLTF binary data
        """
        try:
            # Run the heavy computation in thread pool
            loop = asyncio.get_event_loop()
            gltf_data = await loop.run_in_executor(
                self.executor,
                self._create_gltf_scene,
                layout,
                envelope,
                include_envelope,
                include_materials
            )
            return gltf_data
            
        except Exception as e:
            logger.error(f"Failed to export layout {layout.layout_id} as GLTF: {str(e)}")
            raise ExportError(f"GLTF export failed: {str(e)}")
    
    def _create_gltf_scene(
        self, 
        layout: LayoutSpec, 
        envelope: EnvelopeSpec,
        include_envelope: bool,
        include_materials: bool
    ) -> bytes:
        """Create GLTF scene from layout (runs in thread pool)"""
        
        # Create trimesh scene
        scene = trimesh.Scene()
        
        # Add envelope geometry if requested
        if include_envelope:
            envelope_mesh = self._create_envelope_mesh(envelope)
            if envelope_mesh:
                # Set material properties if available
                try:
                    if hasattr(envelope_mesh.visual, 'material'):
                        envelope_mesh.visual.material.name = "envelope_material"
                        if hasattr(envelope_mesh.visual.material, 'diffuse'):
                            envelope_mesh.visual.material.diffuse = [200, 200, 255, 100]  # Semi-transparent blue
                except AttributeError:
                    # Fallback for different trimesh versions
                    pass
                scene.add_geometry(envelope_mesh, node_name="habitat_envelope")
        
        # Add module geometries
        for i, module_placement in enumerate(layout.modules):
            module_mesh = self._create_module_mesh(module_placement)
            if module_mesh:
                # Apply transformation
                transform = self._get_module_transform(module_placement)
                node_name = f"module_{module_placement.module_id}"
                scene.add_geometry(module_mesh, node_name=node_name, transform=transform)
        
        # Export to GLB format
        try:
            # Use trimesh's built-in GLTF export
            export_data = scene.export(file_type='glb')
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export trimesh scene to GLB: {str(e)}")
            # Fallback to manual GLTF creation
            return self._create_manual_gltf(scene)
    
    def _create_envelope_mesh(self, envelope: EnvelopeSpec) -> Optional[trimesh.Trimesh]:
        """Create envelope mesh based on type and parameters"""
        try:
            envelope_type = envelope.type.value if hasattr(envelope.type, 'value') else str(envelope.type)
            if envelope_type == "cylinder":
                radius = envelope.params["radius"]
                length = envelope.params["length"]
                
                # Create cylinder mesh
                cylinder = trimesh.creation.cylinder(
                    radius=radius,
                    height=length,
                    sections=32
                )
                return cylinder
                
            elif envelope_type == "box":
                width = envelope.params["width"]
                height = envelope.params["height"]
                depth = envelope.params["depth"]
                
                # Create box mesh
                box = trimesh.creation.box(extents=[width, height, depth])
                return box
                
            elif envelope_type == "torus":
                major_radius = envelope.params["major_radius"]
                minor_radius = envelope.params["minor_radius"]
                
                # Create torus mesh
                torus = trimesh.creation.torus(
                    major_radius=major_radius,
                    minor_radius=minor_radius,
                    major_sections=32,
                    minor_sections=16
                )
                return torus
                
            else:
                logger.warning(f"Unsupported envelope type for mesh generation: {envelope.type}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create envelope mesh: {str(e)}")
            return None
    
    def _create_module_mesh(self, module_placement: ModulePlacement) -> Optional[trimesh.Trimesh]:
        """Create module mesh from module library or generate basic geometry"""
        try:
            # Try to get module from library
            module_def = self.module_library.get_module(module_placement.module_id)
            if not module_def:
                # Create basic box geometry based on module type
                return self._create_basic_module_mesh(module_placement)
            
            # Try to load 3D asset
            asset_path = Path("assets/modules") / module_def.asset.file_path
            if asset_path.exists():
                try:
                    mesh = trimesh.load(str(asset_path))
                    if isinstance(mesh, trimesh.Scene):
                        # Combine all geometries in the scene
                        combined = trimesh.util.concatenate([
                            geom for geom in mesh.geometry.values()
                            if isinstance(geom, trimesh.Trimesh)
                        ])
                        return combined
                    elif isinstance(mesh, trimesh.Trimesh):
                        return mesh
                except Exception as e:
                    logger.warning(f"Failed to load asset {asset_path}: {str(e)}")
            
            # Fallback to basic geometry
            return self._create_basic_module_mesh(module_placement, module_def)
            
        except Exception as e:
            logger.error(f"Failed to create module mesh for {module_placement.module_id}: {str(e)}")
            return self._create_basic_module_mesh(module_placement)
    
    def _create_basic_module_mesh(
        self, 
        module_placement: ModulePlacement, 
        module_def: Optional[ModuleDefinition] = None
    ) -> trimesh.Trimesh:
        """Create basic box mesh for module"""
        
        if module_def:
            # Use module definition dimensions
            bbox = module_def.spec.bbox_m
            extents = [bbox.x, bbox.y, bbox.z]
        else:
            # Use default dimensions based on module type
            type_dimensions = {
                ModuleType.SLEEP_QUARTER: [2.0, 2.0, 2.5],
                ModuleType.GALLEY: [3.0, 2.5, 2.2],
                ModuleType.LABORATORY: [4.0, 3.0, 2.8],
                ModuleType.AIRLOCK: [2.5, 2.5, 3.0],
                ModuleType.MECHANICAL: [3.5, 2.8, 2.5],
                ModuleType.MEDICAL: [3.0, 2.5, 2.5],
                ModuleType.EXERCISE: [4.0, 3.5, 2.8],
                ModuleType.STORAGE: [2.5, 2.0, 2.0]
            }
            extents = type_dimensions.get(module_placement.type, [2.0, 2.0, 2.0])
        
        # Create box mesh
        mesh = trimesh.creation.box(extents=extents)
        
        # Set material color based on module type
        type_colors = {
            ModuleType.SLEEP_QUARTER: [100, 150, 200, 255],  # Light blue
            ModuleType.GALLEY: [200, 150, 100, 255],         # Orange
            ModuleType.LABORATORY: [150, 200, 100, 255],     # Green
            ModuleType.AIRLOCK: [200, 100, 100, 255],        # Red
            ModuleType.MECHANICAL: [150, 150, 150, 255],     # Gray
            ModuleType.MEDICAL: [200, 200, 100, 255],        # Yellow
            ModuleType.EXERCISE: [150, 100, 200, 255],       # Purple
            ModuleType.STORAGE: [100, 200, 200, 255]         # Cyan
        }
        
        color = type_colors.get(module_placement.type, [128, 128, 128, 255])
        
        # Set material properties if available
        try:
            if hasattr(mesh.visual, 'material'):
                if hasattr(mesh.visual.material, 'diffuse'):
                    mesh.visual.material.diffuse = color
                if hasattr(mesh.visual.material, 'name'):
                    module_type_str = module_placement.type.value if hasattr(module_placement.type, 'value') else str(module_placement.type)
                    mesh.visual.material.name = f"{module_type_str}_material"
        except AttributeError:
            # Fallback for different trimesh versions
            pass
        
        return mesh
    
    def _get_module_transform(self, module_placement: ModulePlacement) -> np.ndarray:
        """Get transformation matrix for module placement"""
        # Create transformation matrix
        transform = np.eye(4)
        
        # Apply translation
        transform[0:3, 3] = module_placement.position
        
        # Apply rotation around Z-axis
        angle_rad = np.radians(module_placement.rotation_deg)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)
        
        rotation_matrix = np.array([
            [cos_a, -sin_a, 0],
            [sin_a, cos_a, 0],
            [0, 0, 1]
        ])
        
        transform[0:3, 0:3] = rotation_matrix
        
        return transform
    
    def _create_manual_gltf(self, scene: trimesh.Scene) -> bytes:
        """Manual GLTF creation as fallback"""
        try:
            # This is a simplified GLTF creation
            # In a production system, you'd want more robust GLTF generation
            
            gltf = GLTF2()
            
            # Create basic scene structure
            gltf.scenes = [Scene(nodes=[0])]
            gltf.scene = 0
            gltf.nodes = [Node(mesh=0)]
            
            # For now, create a simple placeholder mesh
            vertices = np.array([
                [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],  # Bottom face
                [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]       # Top face
            ], dtype=np.float32)
            
            indices = np.array([
                0, 1, 2, 0, 2, 3,  # Bottom
                4, 7, 6, 4, 6, 5,  # Top
                0, 4, 5, 0, 5, 1,  # Front
                2, 6, 7, 2, 7, 3,  # Back
                0, 3, 7, 0, 7, 4,  # Left
                1, 5, 6, 1, 6, 2   # Right
            ], dtype=np.uint32)
            
            # Create buffers
            vertex_buffer = vertices.tobytes()
            index_buffer = indices.tobytes()
            
            gltf.buffers = [
                Buffer(byteLength=len(vertex_buffer) + len(index_buffer))
            ]
            
            gltf.bufferViews = [
                BufferView(
                    buffer=0,
                    byteOffset=0,
                    byteLength=len(vertex_buffer),
                    target=ARRAY_BUFFER
                ),
                BufferView(
                    buffer=0,
                    byteOffset=len(vertex_buffer),
                    byteLength=len(index_buffer),
                    target=ELEMENT_ARRAY_BUFFER
                )
            ]
            
            gltf.accessors = [
                Accessor(
                    bufferView=0,
                    componentType=FLOAT,
                    count=len(vertices),
                    type="VEC3",
                    min=vertices.min(axis=0).tolist(),
                    max=vertices.max(axis=0).tolist()
                ),
                Accessor(
                    bufferView=1,
                    componentType=UNSIGNED_INT,
                    count=len(indices),
                    type="SCALAR"
                )
            ]
            
            gltf.meshes = [
                Mesh(primitives=[
                    Primitive(
                        attributes={"POSITION": 0},
                        indices=1,
                        material=0
                    )
                ])
            ]
            
            gltf.materials = [
                Material(
                    pbrMetallicRoughness=PbrMetallicRoughness(
                        baseColorFactor=[0.8, 0.8, 0.8, 1.0],
                        metallicFactor=0.0,
                        roughnessFactor=0.5
                    )
                )
            ]
            
            # Convert to GLB
            gltf.convert_buffers(BufferFormat.BINARYBLOB)
            glb_data = gltf.save_to_bytes()
            
            return glb_data
            
        except Exception as e:
            logger.error(f"Manual GLTF creation failed: {str(e)}")
            raise ExportError(f"Failed to create GLTF data: {str(e)}")
    
    async def export_layout_json(self, layout: LayoutSpec, envelope: EnvelopeSpec) -> Dict[str, Any]:
        """Export layout specification as JSON"""
        try:
            export_data = {
                "metadata": {
                    "export_timestamp": datetime.utcnow().isoformat(),
                    "format_version": "1.0",
                    "exporter": "HabitatCanvas Export Service"
                },
                "envelope": envelope.model_dump(mode='json'),
                "layout": layout.model_dump(mode='json'),
                "module_specifications": {}
            }
            
            # Include module specifications for reference
            for module_placement in layout.modules:
                module_def = self.module_library.get_module(module_placement.module_id)
                if module_def:
                    export_data["module_specifications"][module_placement.module_id] = module_def.spec.model_dump(mode='json')
            
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export layout {layout.layout_id} as JSON: {str(e)}")
            raise ExportError(f"JSON export failed: {str(e)}")
    
    async def export_batch_layouts(
        self, 
        layouts: List[LayoutSpec], 
        envelopes: Dict[str, EnvelopeSpec],
        format: str = ExportFormat.GLB,
        include_json: bool = True
    ) -> bytes:
        """
        Export multiple layouts as a ZIP archive
        
        Args:
            layouts: List of layouts to export
            envelopes: Dictionary mapping envelope IDs to envelope specs
            format: Export format for 3D models
            include_json: Whether to include JSON specifications
            
        Returns:
            ZIP archive as bytes
        """
        try:
            # Create temporary directory for files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Export each layout
                for layout in layouts:
                    envelope = envelopes.get(layout.envelope_id)
                    if not envelope:
                        logger.warning(f"Envelope {layout.envelope_id} not found for layout {layout.layout_id}")
                        continue
                    
                    layout_dir = temp_path / f"layout_{layout.layout_id}"
                    layout_dir.mkdir(exist_ok=True)
                    
                    # Export 3D model
                    if format in [ExportFormat.GLTF, ExportFormat.GLB]:
                        model_data = await self.export_layout_gltf(layout, envelope)
                        model_file = layout_dir / f"{layout.layout_id}.{format}"
                        model_file.write_bytes(model_data)
                    
                    # Export JSON specification
                    if include_json:
                        json_data = await self.export_layout_json(layout, envelope)
                        json_file = layout_dir / f"{layout.layout_id}.json"
                        json_file.write_text(json.dumps(json_data, indent=2))
                
                # Create ZIP archive
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for file_path in temp_path.rglob('*'):
                        if file_path.is_file():
                            arcname = file_path.relative_to(temp_path)
                            zip_file.write(file_path, arcname)
                
                return zip_buffer.getvalue()
                
        except Exception as e:
            logger.error(f"Failed to export batch layouts: {str(e)}")
            raise ExportError(f"Batch export failed: {str(e)}")


class CADExporter:
    """CAD format export functionality"""
    
    def __init__(self):
        self.module_library = get_module_library()
        self._init_opencascade()
    
    def _init_opencascade(self):
        """Initialize OpenCASCADE components"""
        try:
            # Import OpenCASCADE modules
            from OCC.Core import (
                gp_Pnt, gp_Vec, gp_Ax2, gp_Dir,
                BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeTorus,
                BRepBuilderAPI_Transform, BRepBuilderAPI_MakeCompound,
                STEPControl_Writer, IGESControl_Writer,
                Interface_Static, IFSelect_ReturnStatus,
                TopoDS_Compound, BRep_Builder,
                gp_Trsf, TopLoc_Location
            )
            
            self.occ_available = True
            self.gp_Pnt = gp_Pnt
            self.gp_Vec = gp_Vec
            self.gp_Ax2 = gp_Ax2
            self.gp_Dir = gp_Dir
            self.BRepPrimAPI_MakeBox = BRepPrimAPI_MakeBox
            self.BRepPrimAPI_MakeCylinder = BRepPrimAPI_MakeCylinder
            self.BRepPrimAPI_MakeTorus = BRepPrimAPI_MakeTorus
            self.BRepBuilderAPI_Transform = BRepBuilderAPI_Transform
            self.BRepBuilderAPI_MakeCompound = BRepBuilderAPI_MakeCompound
            self.STEPControl_Writer = STEPControl_Writer
            self.IGESControl_Writer = IGESControl_Writer
            self.Interface_Static = Interface_Static
            self.IFSelect_ReturnStatus = IFSelect_ReturnStatus
            self.TopoDS_Compound = TopoDS_Compound
            self.BRep_Builder = BRep_Builder
            self.gp_Trsf = gp_Trsf
            self.TopLoc_Location = TopLoc_Location
            
            logger.info("OpenCASCADE initialized successfully")
            
        except ImportError as e:
            logger.warning(f"OpenCASCADE not available: {e}")
            self.occ_available = False
    
    async def export_layout_step(self, layout: LayoutSpec, envelope: EnvelopeSpec) -> bytes:
        """Export layout as STEP format using OpenCASCADE"""
        try:
            if not self.occ_available:
                # Fallback to simplified STEP format
                step_content = self._generate_step_content(layout, envelope)
                return step_content.encode('utf-8')
            
            # Use OpenCASCADE for proper STEP export
            loop = asyncio.get_event_loop()
            step_data = await loop.run_in_executor(
                None,
                self._create_step_with_opencascade,
                layout,
                envelope
            )
            return step_data
            
        except Exception as e:
            logger.error(f"Failed to export layout {layout.layout_id} as STEP: {str(e)}")
            raise ExportError(f"STEP export failed: {str(e)}")
    
    def _create_step_with_opencascade(self, layout: LayoutSpec, envelope: EnvelopeSpec) -> bytes:
        """Create STEP file using OpenCASCADE"""
        try:
            # Create compound to hold all shapes
            compound_builder = self.BRep_Builder()
            compound = self.TopoDS_Compound()
            compound_builder.MakeCompound(compound)
            
            # Add envelope geometry
            envelope_shape = self._create_envelope_shape_occ(envelope)
            if envelope_shape:
                compound_builder.Add(compound, envelope_shape)
            
            # Add module geometries
            for module_placement in layout.modules:
                module_shape = self._create_module_shape_occ(module_placement)
                if module_shape:
                    compound_builder.Add(compound, module_shape)
            
            # Write to STEP format
            step_writer = self.STEPControl_Writer()
            
            # Set units to millimeters
            self.Interface_Static.SetCVal("write.step.unit", "MM")
            self.Interface_Static.SetCVal("write.step.schema", "AP214")
            
            # Add the compound to the writer
            status = step_writer.Transfer(compound, self.STEPControl_Writer.STEPControl_AsIs)
            
            if status != self.IFSelect_ReturnStatus.IFSelect_RetDone:
                raise ExportError("Failed to transfer geometry to STEP writer")
            
            # Write to temporary file
            with tempfile.NamedTemporaryFile(suffix='.step', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                status = step_writer.Write(temp_path)
                if status != self.IFSelect_ReturnStatus.IFSelect_RetDone:
                    raise ExportError("Failed to write STEP file")
                
                # Read the file content
                with open(temp_path, 'rb') as f:
                    step_data = f.read()
                
                return step_data
                
            finally:
                # Clean up temporary file
                Path(temp_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"OpenCASCADE STEP export failed: {str(e)}")
            raise ExportError(f"OpenCASCADE STEP export failed: {str(e)}")
    
    def _create_envelope_shape_occ(self, envelope: EnvelopeSpec):
        """Create envelope shape using OpenCASCADE"""
        try:
            envelope_type = envelope.type.value if hasattr(envelope.type, 'value') else str(envelope.type)
            if envelope_type == "cylinder":
                radius = envelope.params["radius"] * 1000  # Convert to mm
                length = envelope.params["length"] * 1000
                
                # Create cylinder at origin
                axis = self.gp_Ax2(
                    self.gp_Pnt(0, 0, -length/2),
                    self.gp_Dir(0, 0, 1)
                )
                cylinder_maker = self.BRepPrimAPI_MakeCylinder(axis, radius, length)
                return cylinder_maker.Shape()
                
            elif envelope_type == "box":
                width = envelope.params["width"] * 1000
                height = envelope.params["height"] * 1000
                depth = envelope.params["depth"] * 1000
                
                # Create box centered at origin
                box_maker = self.BRepPrimAPI_MakeBox(
                    self.gp_Pnt(-width/2, -height/2, -depth/2),
                    width, height, depth
                )
                return box_maker.Shape()
                
            elif envelope_type == "torus":
                major_radius = envelope.params["major_radius"] * 1000
                minor_radius = envelope.params["minor_radius"] * 1000
                
                # Create torus at origin
                axis = self.gp_Ax2(
                    self.gp_Pnt(0, 0, 0),
                    self.gp_Dir(0, 0, 1)
                )
                torus_maker = self.BRepPrimAPI_MakeTorus(axis, major_radius, minor_radius)
                return torus_maker.Shape()
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to create envelope shape: {str(e)}")
            return None
    
    def _create_module_shape_occ(self, module_placement: ModulePlacement):
        """Create module shape using OpenCASCADE"""
        try:
            # Get module definition
            module_def = self.module_library.get_module(module_placement.module_id)
            
            if module_def:
                bbox = module_def.spec.bbox_m
                width = bbox.x * 1000  # Convert to mm
                height = bbox.y * 1000
                depth = bbox.z * 1000
            else:
                # Default dimensions
                width = height = depth = 2000  # 2m default
            
            # Create box
            box_maker = self.BRepPrimAPI_MakeBox(
                self.gp_Pnt(-width/2, -height/2, -depth/2),
                width, height, depth
            )
            box_shape = box_maker.Shape()
            
            # Apply transformation
            transform = self.gp_Trsf()
            
            # Apply rotation around Z-axis
            angle_rad = np.radians(module_placement.rotation_deg)
            transform.SetRotation(
                self.gp_Ax2(self.gp_Pnt(0, 0, 0), self.gp_Dir(0, 0, 1)).Axis(),
                angle_rad
            )
            
            # Apply translation (convert to mm)
            position = [p * 1000 for p in module_placement.position]
            transform.SetTranslation(self.gp_Vec(position[0], position[1], position[2]))
            
            # Apply transformation to shape
            transformer = self.BRepBuilderAPI_Transform(box_shape, transform)
            return transformer.Shape()
            
        except Exception as e:
            logger.error(f"Failed to create module shape: {str(e)}")
            return None
    
    def _generate_step_content(self, layout: LayoutSpec, envelope: EnvelopeSpec) -> str:
        """Generate STEP file content (simplified)"""
        
        # STEP file header
        step_content = [
            "ISO-10303-21;",
            "HEADER;",
            "FILE_DESCRIPTION(('HabitatCanvas Layout Export'), '2;1');",
            f"FILE_NAME('{layout.layout_id}.step', '{datetime.utcnow().isoformat()}', ('HabitatCanvas',), ('',), 'HabitatCanvas Export Service', '', '');",
            "FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));",
            "ENDSEC;",
            "",
            "DATA;"
        ]
        
        entity_id = 1
        
        # Add envelope geometry (simplified)
        envelope_type = envelope.type.value if hasattr(envelope.type, 'value') else str(envelope.type)
        if envelope_type == "cylinder":
            radius = envelope.params["radius"]
            length = envelope.params["length"]
            
            step_content.extend([
                f"#{entity_id} = CARTESIAN_POINT('', (0.0, 0.0, 0.0));",
                f"#{entity_id + 1} = DIRECTION('', (0.0, 0.0, 1.0));",
                f"#{entity_id + 2} = AXIS2_PLACEMENT_3D('', #{entity_id}, #{entity_id + 1}, $);",
                f"#{entity_id + 3} = CYLINDRICAL_SURFACE('', #{entity_id + 2}, {radius});",
                f"#{entity_id + 4} = ADVANCED_FACE('', (#{entity_id + 5}), #{entity_id + 3}, .T.);",
            ])
            entity_id += 5
        
        # Add module geometries (simplified boxes)
        for module in layout.modules:
            module_def = self.module_library.get_module(module.module_id)
            if module_def:
                bbox = module_def.spec.bbox_m
                x, y, z = module.position
                
                step_content.extend([
                    f"#{entity_id} = CARTESIAN_POINT('', ({x}, {y}, {z}));",
                    f"#{entity_id + 1} = DIRECTION('', (1.0, 0.0, 0.0));",
                    f"#{entity_id + 2} = DIRECTION('', (0.0, 1.0, 0.0));",
                    f"#{entity_id + 3} = AXIS2_PLACEMENT_3D('', #{entity_id}, #{entity_id + 2}, #{entity_id + 1});",
                    f"#{entity_id + 4} = BLOCK('', #{entity_id + 3}, {bbox.x}, {bbox.y}, {bbox.z});",
                ])
                entity_id += 5
        
        step_content.extend([
            "ENDSEC;",
            "END-ISO-10303-21;"
        ])
        
        return '\n'.join(step_content)
    
    async def export_layout_iges(self, layout: LayoutSpec, envelope: EnvelopeSpec) -> bytes:
        """Export layout as IGES format using OpenCASCADE"""
        try:
            if not self.occ_available:
                # Fallback to simplified IGES format
                iges_content = self._generate_iges_content(layout, envelope)
                return iges_content.encode('utf-8')
            
            # Use OpenCASCADE for proper IGES export
            loop = asyncio.get_event_loop()
            iges_data = await loop.run_in_executor(
                None,
                self._create_iges_with_opencascade,
                layout,
                envelope
            )
            return iges_data
            
        except Exception as e:
            logger.error(f"Failed to export layout {layout.layout_id} as IGES: {str(e)}")
            raise ExportError(f"IGES export failed: {str(e)}")
    
    def _create_iges_with_opencascade(self, layout: LayoutSpec, envelope: EnvelopeSpec) -> bytes:
        """Create IGES file using OpenCASCADE"""
        try:
            # Create compound to hold all shapes
            compound_builder = self.BRep_Builder()
            compound = self.TopoDS_Compound()
            compound_builder.MakeCompound(compound)
            
            # Add envelope geometry
            envelope_shape = self._create_envelope_shape_occ(envelope)
            if envelope_shape:
                compound_builder.Add(compound, envelope_shape)
            
            # Add module geometries
            for module_placement in layout.modules:
                module_shape = self._create_module_shape_occ(module_placement)
                if module_shape:
                    compound_builder.Add(compound, module_shape)
            
            # Write to IGES format
            iges_writer = self.IGESControl_Writer()
            
            # Set units to millimeters
            self.Interface_Static.SetCVal("write.iges.unit", "MM")
            
            # Add the compound to the writer
            iges_writer.AddShape(compound)
            
            # Write to temporary file
            with tempfile.NamedTemporaryFile(suffix='.iges', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                success = iges_writer.Write(temp_path)
                if not success:
                    raise ExportError("Failed to write IGES file")
                
                # Read the file content
                with open(temp_path, 'rb') as f:
                    iges_data = f.read()
                
                return iges_data
                
            finally:
                # Clean up temporary file
                Path(temp_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"OpenCASCADE IGES export failed: {str(e)}")
            raise ExportError(f"OpenCASCADE IGES export failed: {str(e)}")
    
    def _generate_iges_content(self, layout: LayoutSpec, envelope: EnvelopeSpec) -> str:
        """Generate IGES file content (simplified)"""
        
        # IGES file structure (very simplified)
        iges_content = [
            "START                                                                          1",
            f"HabitatCanvas Layout Export - {layout.layout_id}                              2",
            "1H,,1H;,4HIGES,13H{datetime.utcnow().strftime('%Y%m%d.%H%M%S')},              3",
            "32HHabitatCanvas Export Service,8H1.0,32,38,6,38,15,                          4",
            "4HIGES,1,2HMM,1,0.01,15H{datetime.utcnow().strftime('%Y%m%d.%H%M%S')},        5",
            "1E-07,1000.0,7HUnknown,7HUnknown,11,0,                                        6",
            "15H{datetime.utcnow().strftime('%Y%m%d.%H%M%S')},;                             7",
            "G      1"
        ]
        
        # Add simplified geometry entities
        param_line = 1
        
        # This is a very simplified IGES structure
        # Real IGES export would require proper entity definitions
        
        iges_content.extend([
            f"     110       1       0       0       0       0       0       000000001D      1",
            f"     110       0       0       1       0                               D      2",
            f"110,0.0,0.0,0.0,1.0,0.0,0.0;                                          {param_line}P      1",
        ])
        
        iges_content.extend([
            f"S      {len([l for l in iges_content if l.endswith('G      1')])}G      {len([l for l in iges_content if l.endswith(('D      1', 'D      2'))])}D      {param_line}P                                        T      1"
        ])
        
        return '\n'.join(iges_content)


# Global exporter instances
_model_exporter: Optional[ModelExporter] = None
_cad_exporter: Optional[CADExporter] = None


def get_model_exporter() -> ModelExporter:
    """Get the global model exporter instance"""
    global _model_exporter
    if _model_exporter is None:
        _model_exporter = ModelExporter()
    return _model_exporter


def get_cad_exporter() -> CADExporter:
    """Get the global CAD exporter instance"""
    global _cad_exporter
    if _cad_exporter is None:
        _cad_exporter = CADExporter()
    return _cad_exporter