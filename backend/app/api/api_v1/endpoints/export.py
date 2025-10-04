"""
Export API endpoints for HabitatCanvas

Provides endpoints for exporting layouts and models in various formats:
- 3D models (GLTF/GLB)
- CAD formats (STEP/IGES)
- JSON specifications
- Batch exports
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io
import json
from datetime import datetime

from app.db.base import get_db
from app.models.base import LayoutSpec, EnvelopeSpec
from app.crud import layout as crud_layout, envelope as crud_envelope
from app.services.export_service import (
    get_model_exporter, get_cad_exporter, ExportFormat, ExportError
)
from app.services.report_generator import get_report_generator, ReportTemplate, ReportError
from app.api.api_v1.endpoints.layouts import db_layout_to_spec

router = APIRouter()


@router.get("/{layout_id}/gltf")
async def export_layout_gltf(
    layout_id: str,
    include_envelope: bool = Query(True, description="Include habitat envelope in export"),
    include_materials: bool = Query(True, description="Include material definitions"),
    db: AsyncSession = Depends(get_db)
):
    """Export layout as GLTF format"""
    try:
        # Get layout from database
        db_layout = await crud_layout.get(db, id=layout_id)
        if not db_layout:
            raise HTTPException(status_code=404, detail="Layout not found")
        
        layout = db_layout_to_spec(db_layout)
        
        # Get envelope
        db_envelope = await crud_envelope.get(db, id=layout.envelope_id)
        if not db_envelope:
            raise HTTPException(status_code=404, detail="Envelope not found")
        
        envelope = EnvelopeSpec(
            id=db_envelope.envelope_id,
            type=db_envelope.type,
            params=db_envelope.params,
            coordinate_frame=db_envelope.coordinate_frame,
            metadata=db_envelope.metadata
        )
        
        # Export as GLTF
        exporter = get_model_exporter()
        gltf_data = await exporter.export_layout_gltf(
            layout, envelope, include_envelope, include_materials
        )
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(gltf_data),
            media_type="model/gltf-binary",
            headers={
                "Content-Disposition": f"attachment; filename={layout_id}.glb"
            }
        )
        
    except HTTPException:
        raise
    except ExportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/{layout_id}/json")
async def export_layout_json(
    layout_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Export layout specification as JSON"""
    try:
        # Get layout from database
        db_layout = await crud_layout.get(db, id=layout_id)
        if not db_layout:
            raise HTTPException(status_code=404, detail="Layout not found")
        
        layout = db_layout_to_spec(db_layout)
        
        # Get envelope
        db_envelope = await crud_envelope.get(db, id=layout.envelope_id)
        if not db_envelope:
            raise HTTPException(status_code=404, detail="Envelope not found")
        
        envelope = EnvelopeSpec(
            id=db_envelope.envelope_id,
            type=db_envelope.type,
            params=db_envelope.params,
            coordinate_frame=db_envelope.coordinate_frame,
            metadata=db_envelope.metadata
        )
        
        # Export as JSON
        exporter = get_model_exporter()
        json_data = await exporter.export_layout_json(layout, envelope)
        
        # Return JSON response
        return Response(
            content=json.dumps(json_data, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={layout_id}.json"
            }
        )
        
    except HTTPException:
        raise
    except ExportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/{layout_id}/step")
async def export_layout_step(
    layout_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Export layout as STEP CAD format"""
    try:
        # Get layout from database
        db_layout = await crud_layout.get(db, id=layout_id)
        if not db_layout:
            raise HTTPException(status_code=404, detail="Layout not found")
        
        layout = db_layout_to_spec(db_layout)
        
        # Get envelope
        db_envelope = await crud_envelope.get(db, id=layout.envelope_id)
        if not db_envelope:
            raise HTTPException(status_code=404, detail="Envelope not found")
        
        envelope = EnvelopeSpec(
            id=db_envelope.envelope_id,
            type=db_envelope.type,
            params=db_envelope.params,
            coordinate_frame=db_envelope.coordinate_frame,
            metadata=db_envelope.metadata
        )
        
        # Export as STEP
        exporter = get_cad_exporter()
        step_data = await exporter.export_layout_step(layout, envelope)
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(step_data),
            media_type="application/step",
            headers={
                "Content-Disposition": f"attachment; filename={layout_id}.step"
            }
        )
        
    except HTTPException:
        raise
    except ExportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/{layout_id}/iges")
async def export_layout_iges(
    layout_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Export layout as IGES CAD format"""
    try:
        # Get layout from database
        db_layout = await crud_layout.get(db, id=layout_id)
        if not db_layout:
            raise HTTPException(status_code=404, detail="Layout not found")
        
        layout = db_layout_to_spec(db_layout)
        
        # Get envelope
        db_envelope = await crud_envelope.get(db, id=layout.envelope_id)
        if not db_envelope:
            raise HTTPException(status_code=404, detail="Envelope not found")
        
        envelope = EnvelopeSpec(
            id=db_envelope.envelope_id,
            type=db_envelope.type,
            params=db_envelope.params,
            coordinate_frame=db_envelope.coordinate_frame,
            metadata=db_envelope.metadata
        )
        
        # Export as IGES
        exporter = get_cad_exporter()
        iges_data = await exporter.export_layout_iges(layout, envelope)
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(iges_data),
            media_type="application/iges",
            headers={
                "Content-Disposition": f"attachment; filename={layout_id}.iges"
            }
        )
        
    except HTTPException:
        raise
    except ExportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/batch")
async def export_batch_layouts(
    layout_ids: List[str],
    format: str = Query(ExportFormat.GLB, description="Export format for 3D models"),
    include_json: bool = Query(True, description="Include JSON specifications"),
    db: AsyncSession = Depends(get_db)
):
    """Export multiple layouts as a ZIP archive"""
    try:
        if not layout_ids:
            raise HTTPException(status_code=400, detail="No layout IDs provided")
        
        if len(layout_ids) > 50:
            raise HTTPException(status_code=400, detail="Too many layouts (max 50)")
        
        # Validate format
        valid_formats = [ExportFormat.GLTF, ExportFormat.GLB]
        if format not in valid_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid format. Supported formats: {valid_formats}"
            )
        
        # Get layouts from database
        layouts = []
        envelopes = {}
        
        for layout_id in layout_ids:
            db_layout = await crud_layout.get(db, id=layout_id)
            if not db_layout:
                raise HTTPException(status_code=404, detail=f"Layout {layout_id} not found")
            
            layout = db_layout_to_spec(db_layout)
            layouts.append(layout)
            
            # Get envelope if not already cached
            if layout.envelope_id not in envelopes:
                db_envelope = await crud_envelope.get(db, id=layout.envelope_id)
                if db_envelope:
                    envelopes[layout.envelope_id] = EnvelopeSpec(
                        id=db_envelope.envelope_id,
                        type=db_envelope.type,
                        params=db_envelope.params,
                        coordinate_frame=db_envelope.coordinate_frame,
                        metadata=db_envelope.metadata
                    )
        
        # Export batch
        exporter = get_model_exporter()
        zip_data = await exporter.export_batch_layouts(
            layouts, envelopes, format, include_json
        )
        
        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"habitat_layouts_{timestamp}.zip"
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(zip_data),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except ExportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch export failed: {str(e)}")


@router.get("/formats")
async def get_supported_formats():
    """Get list of supported export formats"""
    return {
        "3d_formats": [
            {
                "format": ExportFormat.GLTF,
                "description": "GL Transmission Format (text-based)",
                "extension": ".gltf",
                "mime_type": "model/gltf+json"
            },
            {
                "format": ExportFormat.GLB,
                "description": "GL Transmission Format (binary)",
                "extension": ".glb",
                "mime_type": "model/gltf-binary"
            }
        ],
        "cad_formats": [
            {
                "format": ExportFormat.STEP,
                "description": "Standard for Exchange of Product Data",
                "extension": ".step",
                "mime_type": "application/step"
            },
            {
                "format": ExportFormat.IGES,
                "description": "Initial Graphics Exchange Specification",
                "extension": ".iges",
                "mime_type": "application/iges"
            }
        ],
        "data_formats": [
            {
                "format": ExportFormat.JSON,
                "description": "Layout specification in JSON format",
                "extension": ".json",
                "mime_type": "application/json"
            }
        ],
        "archive_formats": [
            {
                "format": ExportFormat.ZIP,
                "description": "ZIP archive for batch exports",
                "extension": ".zip",
                "mime_type": "application/zip"
            }
        ]
    }


@router.get("/{layout_id}/preview")
async def get_export_preview(
    layout_id: str,
    format: str = Query(ExportFormat.JSON, description="Format to preview"),
    db: AsyncSession = Depends(get_db)
):
    """Get preview information for export without generating the full file"""
    try:
        # Get layout from database
        db_layout = await crud_layout.get(db, id=layout_id)
        if not db_layout:
            raise HTTPException(status_code=404, detail="Layout not found")
        
        layout = db_layout_to_spec(db_layout)
        
        # Get envelope
        db_envelope = await crud_envelope.get(db, id=layout.envelope_id)
        if not db_envelope:
            raise HTTPException(status_code=404, detail="Envelope not found")
        
        # Generate preview information
        preview_info = {
            "layout_id": layout_id,
            "format": format,
            "estimated_size": "Unknown",
            "module_count": len(layout.modules),
            "envelope_type": db_envelope.type,
            "export_timestamp": datetime.utcnow().isoformat(),
            "includes": []
        }
        
        if format in [ExportFormat.GLTF, ExportFormat.GLB]:
            preview_info["includes"] = [
                "3D geometry for all modules",
                "Habitat envelope geometry",
                "Material definitions",
                "Scene hierarchy"
            ]
            preview_info["estimated_size"] = f"{len(layout.modules) * 50 + 100}KB"
            
        elif format == ExportFormat.JSON:
            preview_info["includes"] = [
                "Complete layout specification",
                "Module placements and rotations",
                "Performance metrics",
                "Module library references"
            ]
            preview_info["estimated_size"] = f"{len(layout.modules) * 2 + 10}KB"
            
        elif format in [ExportFormat.STEP, ExportFormat.IGES]:
            preview_info["includes"] = [
                "CAD-compatible geometry",
                "Parametric module definitions",
                "Assembly structure"
            ]
            preview_info["estimated_size"] = f"{len(layout.modules) * 20 + 50}KB"
        
        return preview_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")


@router.post("/report/pdf")
async def generate_pdf_report(
    layout_ids: List[str],
    template: str = Query(ReportTemplate.TECHNICAL, description="Report template type"),
    include_3d_snapshots: bool = Query(True, description="Include 3D visualization snapshots"),
    db: AsyncSession = Depends(get_db)
):
    """Generate comprehensive PDF report for layouts"""
    try:
        if not layout_ids:
            raise HTTPException(status_code=400, detail="No layout IDs provided")
        
        if len(layout_ids) > 10:
            raise HTTPException(status_code=400, detail="Too many layouts for report (max 10)")
        
        # Validate template
        valid_templates = [ReportTemplate.EXECUTIVE, ReportTemplate.TECHNICAL, 
                          ReportTemplate.STAKEHOLDER, ReportTemplate.COMPARISON]
        if template not in valid_templates:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid template. Supported templates: {valid_templates}"
            )
        
        # Get layouts from database
        layouts = []
        envelopes = {}
        
        for layout_id in layout_ids:
            db_layout = await crud_layout.get(db, id=layout_id)
            if not db_layout:
                raise HTTPException(status_code=404, detail=f"Layout {layout_id} not found")
            
            layout = db_layout_to_spec(db_layout)
            layouts.append(layout)
            
            # Get envelope if not already cached
            if layout.envelope_id not in envelopes:
                db_envelope = await crud_envelope.get(db, id=layout.envelope_id)
                if db_envelope:
                    envelopes[layout.envelope_id] = EnvelopeSpec(
                        id=db_envelope.envelope_id,
                        type=db_envelope.type,
                        params=db_envelope.params,
                        coordinate_frame=db_envelope.coordinate_frame,
                        metadata=db_envelope.metadata
                    )
        
        # Generate PDF report
        report_generator = get_report_generator()
        pdf_data = await report_generator.generate_pdf_report(
            layouts, envelopes, template, include_3d_snapshots
        )
        
        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        if len(layouts) == 1:
            filename = f"habitat_report_{layouts[0].layoutId}_{timestamp}.pdf"
        else:
            filename = f"habitat_comparison_report_{timestamp}.pdf"
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(pdf_data),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except ReportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("/{layout_id}/snapshot")
async def generate_layout_snapshot(
    layout_id: str,
    width: int = Query(1920, description="Image width in pixels"),
    height: int = Query(1080, description="Image height in pixels"),
    view_angle: str = Query("top", description="View angle (top, side, isometric)"),
    db: AsyncSession = Depends(get_db)
):
    """Generate PNG snapshot of layout for presentations"""
    try:
        # Get layout from database
        db_layout = await crud_layout.get(db, id=layout_id)
        if not db_layout:
            raise HTTPException(status_code=404, detail="Layout not found")
        
        layout = db_layout_to_spec(db_layout)
        
        # Get envelope
        db_envelope = await crud_envelope.get(db, id=layout.envelope_id)
        if not db_envelope:
            raise HTTPException(status_code=404, detail="Envelope not found")
        
        envelope = EnvelopeSpec(
            id=db_envelope.envelope_id,
            type=db_envelope.type,
            params=db_envelope.params,
            coordinate_frame=db_envelope.coordinate_frame,
            metadata=db_envelope.metadata
        )
        
        # Validate parameters
        if width < 100 or width > 4000:
            raise HTTPException(status_code=400, detail="Width must be between 100 and 4000 pixels")
        
        if height < 100 or height > 4000:
            raise HTTPException(status_code=400, detail="Height must be between 100 and 4000 pixels")
        
        if view_angle not in ["top", "side", "isometric"]:
            raise HTTPException(status_code=400, detail="View angle must be 'top', 'side', or 'isometric'")
        
        # Generate PNG snapshot
        report_generator = get_report_generator()
        png_data = await report_generator.generate_png_snapshot(
            layout, envelope, width, height, view_angle
        )
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(png_data),
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename={layout_id}_snapshot.png"
            }
        )
        
    except HTTPException:
        raise
    except ReportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Snapshot generation failed: {str(e)}")


@router.get("/{layout_id}/summary")
async def generate_executive_summary(
    layout_id: str,
    max_length: int = Query(500, description="Maximum summary length in words"),
    db: AsyncSession = Depends(get_db)
):
    """Generate executive summary with key findings"""
    try:
        # Get layout from database
        db_layout = await crud_layout.get(db, id=layout_id)
        if not db_layout:
            raise HTTPException(status_code=404, detail="Layout not found")
        
        layout = db_layout_to_spec(db_layout)
        
        # Get envelope
        db_envelope = await crud_envelope.get(db, id=layout.envelope_id)
        envelope = None
        if db_envelope:
            envelope = EnvelopeSpec(
                id=db_envelope.envelope_id,
                type=db_envelope.type,
                params=db_envelope.params,
                coordinate_frame=db_envelope.coordinate_frame,
                metadata=db_envelope.metadata
            )
        
        # Validate parameters
        if max_length < 50 or max_length > 2000:
            raise HTTPException(status_code=400, detail="Max length must be between 50 and 2000 words")
        
        # Generate executive summary
        report_generator = get_report_generator()
        summary = await report_generator.generate_executive_summary(
            [layout], {layout.envelope_id: envelope} if envelope else {}, max_length
        )
        
        return {
            "layout_id": layout_id,
            "summary": summary,
            "word_count": len(summary.split()),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except ReportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")


@router.post("/report/comparison")
async def generate_comparison_summary(
    layout_ids: List[str],
    max_length: int = Query(800, description="Maximum summary length in words"),
    db: AsyncSession = Depends(get_db)
):
    """Generate comparison summary for multiple layouts"""
    try:
        if not layout_ids:
            raise HTTPException(status_code=400, detail="No layout IDs provided")
        
        if len(layout_ids) < 2:
            raise HTTPException(status_code=400, detail="At least 2 layouts required for comparison")
        
        if len(layout_ids) > 10:
            raise HTTPException(status_code=400, detail="Too many layouts for comparison (max 10)")
        
        # Get layouts from database
        layouts = []
        envelopes = {}
        
        for layout_id in layout_ids:
            db_layout = await crud_layout.get(db, id=layout_id)
            if not db_layout:
                raise HTTPException(status_code=404, detail=f"Layout {layout_id} not found")
            
            layout = db_layout_to_spec(db_layout)
            layouts.append(layout)
            
            # Get envelope if not already cached
            if layout.envelope_id not in envelopes:
                db_envelope = await crud_envelope.get(db, id=layout.envelope_id)
                if db_envelope:
                    envelopes[layout.envelope_id] = EnvelopeSpec(
                        id=db_envelope.envelope_id,
                        type=db_envelope.type,
                        params=db_envelope.params,
                        coordinate_frame=db_envelope.coordinate_frame,
                        metadata=db_envelope.metadata
                    )
        
        # Validate parameters
        if max_length < 100 or max_length > 3000:
            raise HTTPException(status_code=400, detail="Max length must be between 100 and 3000 words")
        
        # Generate comparison summary
        report_generator = get_report_generator()
        summary = await report_generator.generate_executive_summary(
            layouts, envelopes, max_length
        )
        
        return {
            "layout_ids": layout_ids,
            "layout_count": len(layouts),
            "summary": summary,
            "word_count": len(summary.split()),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except ReportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison summary generation failed: {str(e)}")


@router.get("/templates")
async def get_report_templates():
    """Get available report templates"""
    return {
        "templates": [
            {
                "id": ReportTemplate.EXECUTIVE,
                "name": "Executive Summary",
                "description": "High-level overview for decision makers",
                "sections": ["Executive Summary", "Key Metrics", "Recommendations"],
                "target_audience": "Executives, Program Managers"
            },
            {
                "id": ReportTemplate.TECHNICAL,
                "name": "Technical Analysis",
                "description": "Detailed technical analysis for engineers",
                "sections": ["Technical Analysis", "Performance Metrics", "Design Rationale", "Appendices"],
                "target_audience": "Engineers, Technical Staff"
            },
            {
                "id": ReportTemplate.STAKEHOLDER,
                "name": "Stakeholder Report",
                "description": "Balanced report for diverse stakeholders",
                "sections": ["Overview", "Key Findings", "Visual Summary", "Next Steps"],
                "target_audience": "Mixed Stakeholder Groups"
            },
            {
                "id": ReportTemplate.COMPARISON,
                "name": "Layout Comparison",
                "description": "Side-by-side comparison of multiple layouts",
                "sections": ["Comparison Matrix", "Performance Analysis", "Trade-offs", "Recommendations"],
                "target_audience": "Decision Makers, Design Teams"
            }
        ]
    }