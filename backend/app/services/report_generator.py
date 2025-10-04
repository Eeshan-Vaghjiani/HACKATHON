"""
Report Generation Service for HabitatCanvas

This service handles generating comprehensive reports for habitat layouts including:
- PDF reports with visualizations and metrics
- PNG snapshots for presentations
- Executive summaries with key findings
- Customizable report templates for different stakeholders
"""

import io
import os
import tempfile
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, BinaryIO
from datetime import datetime
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from app.models.base import LayoutSpec, EnvelopeSpec, ModulePlacement, ModuleType, PerformanceMetrics
from app.models.module_library import get_module_library
from app.services.export_service import get_model_exporter

logger = logging.getLogger(__name__)


class ReportTemplate:
    """Report template definitions"""
    EXECUTIVE = "executive"
    TECHNICAL = "technical"
    STAKEHOLDER = "stakeholder"
    COMPARISON = "comparison"


class ReportError(Exception):
    """Report generation error"""
    pass


class ReportGenerator:
    """Report generation functionality"""
    
    def __init__(self):
        self.module_library = get_module_library()
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.model_exporter = get_model_exporter()
    
    async def generate_pdf_report(
        self,
        layouts: List[LayoutSpec],
        envelopes: Dict[str, EnvelopeSpec],
        template: str = ReportTemplate.TECHNICAL,
        include_3d_snapshots: bool = True,
        custom_sections: Optional[List[str]] = None
    ) -> bytes:
        """
        Generate comprehensive PDF report for layouts
        
        Args:
            layouts: List of layout specifications
            envelopes: Dictionary mapping envelope IDs to envelope specs
            template: Report template type
            include_3d_snapshots: Whether to include 3D visualization snapshots
            custom_sections: Custom sections to include
            
        Returns:
            PDF report as bytes
        """
        try:
            loop = asyncio.get_event_loop()
            pdf_data = await loop.run_in_executor(
                self.executor,
                self._create_pdf_report,
                layouts,
                envelopes,
                template,
                include_3d_snapshots,
                custom_sections
            )
            return pdf_data
            
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {str(e)}")
            raise ReportError(f"PDF report generation failed: {str(e)}")
    
    def _create_pdf_report(
        self,
        layouts: List[LayoutSpec],
        envelopes: Dict[str, EnvelopeSpec],
        template: str,
        include_3d_snapshots: bool,
        custom_sections: Optional[List[str]]
    ) -> bytes:
        """Create PDF report (runs in thread pool)"""
        
        # Create temporary file for PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Create PDF document
            doc = SimpleDocTemplate(temp_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Add title and metadata
            story.extend(self._create_title_section(layouts, template, styles))
            
            # Add executive summary
            if template in [ReportTemplate.EXECUTIVE, ReportTemplate.STAKEHOLDER]:
                story.extend(self._create_executive_summary(layouts, envelopes, styles))
            
            # Add layout overview
            story.extend(self._create_layout_overview(layouts, envelopes, styles))
            
            # Add performance metrics
            story.extend(self._create_metrics_section(layouts, styles))
            
            # Add detailed analysis
            if template == ReportTemplate.TECHNICAL:
                story.extend(self._create_technical_analysis(layouts, envelopes, styles))
            
            # Add comparison section if multiple layouts
            if len(layouts) > 1:
                story.extend(self._create_comparison_section(layouts, styles))
            
            # Add 3D snapshots if requested
            if include_3d_snapshots:
                story.extend(self._create_visualization_section(layouts, envelopes, styles))
            
            # Add recommendations
            story.extend(self._create_recommendations_section(layouts, styles))
            
            # Add appendices
            if template == ReportTemplate.TECHNICAL:
                story.extend(self._create_appendices(layouts, envelopes, styles))
            
            # Build PDF
            doc.build(story)
            
            # Read the generated PDF
            with open(temp_path, 'rb') as f:
                pdf_data = f.read()
            
            return pdf_data
            
        finally:
            # Clean up temporary file
            Path(temp_path).unlink(missing_ok=True)
    
    def _create_title_section(self, layouts: List[LayoutSpec], template: str, styles) -> List:
        """Create title section"""
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        if len(layouts) == 1:
            title = f"Habitat Layout Analysis Report"
            subtitle = f"Layout: {layouts[0].layout_id}"
        else:
            title = f"Habitat Layout Comparison Report"
            subtitle = f"{len(layouts)} Layout Configurations"
        
        story.append(Paragraph(title, title_style))
        story.append(Paragraph(subtitle, styles['Heading2']))
        story.append(Spacer(1, 20))
        
        # Metadata table
        metadata = [
            ['Report Type', template.title()],
            ['Generated', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')],
            ['Layouts Analyzed', str(len(layouts))],
            ['Generator', 'HabitatCanvas Report Service']
        ]
        
        metadata_table = Table(metadata, colWidths=[2*inch, 3*inch])
        metadata_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(metadata_table)
        story.append(Spacer(1, 30))
        
        return story
    
    def _create_executive_summary(self, layouts: List[LayoutSpec], envelopes: Dict[str, EnvelopeSpec], styles) -> List:
        """Create executive summary section"""
        story = []
        
        story.append(Paragraph("Executive Summary", styles['Heading1']))
        story.append(Spacer(1, 12))
        
        if len(layouts) == 1:
            layout = layouts[0]
            envelope = envelopes.get(layout.envelope_id)
            
            envelope_type = envelope.type.value if envelope and hasattr(envelope.type, 'value') else str(envelope.type) if envelope else "unknown"
            summary_text = f"""
            This report analyzes a habitat layout configuration with {len(layout.modules)} modules 
            within a {envelope_type} envelope. 
            The layout achieves a mean transit time of {layout.kpis.mean_transit_time:.1f} seconds 
            and emergency egress time of {layout.kpis.egress_time:.1f} seconds.
            
            Key findings include:
            • Total system mass: {layout.kpis.mass_total:.0f} kg
            • Power budget: {layout.kpis.power_budget:.0f} W
            • LSS margin: {layout.kpis.lss_margin*100:.1f}%
            • Stowage utilization: {layout.kpis.stowage_utilization*100:.1f}%
            """
        else:
            # Multi-layout summary
            avg_modules = np.mean([len(layout.modules) for layout in layouts])
            best_transit = min([layout.kpis.mean_transit_time for layout in layouts])
            
            summary_text = f"""
            This report compares {len(layouts)} habitat layout configurations with an average of 
            {avg_modules:.1f} modules per layout. The analysis identifies optimal configurations 
            for different mission priorities and operational requirements.
            
            Best performing metrics across all layouts:
            • Shortest transit time: {best_transit:.1f} seconds
            • Configuration diversity: {len(set(len(l.modules) for l in layouts))} different module counts
            • Analysis scope: Multiple envelope types and arrangements
            """
        
        story.append(Paragraph(summary_text, styles['Normal']))
        story.append(Spacer(1, 20))
        
        return story
    
    def _create_layout_overview(self, layouts: List[LayoutSpec], envelopes: Dict[str, EnvelopeSpec], styles) -> List:
        """Create layout overview section"""
        story = []
        
        story.append(Paragraph("Layout Overview", styles['Heading1']))
        story.append(Spacer(1, 12))
        
        for i, layout in enumerate(layouts):
            envelope = envelopes.get(layout.envelope_id)
            
            story.append(Paragraph(f"Layout {i+1}: {layout.layout_id}", styles['Heading2']))
            
            # Layout details table
            details = [
                ['Property', 'Value'],
                ['Layout ID', layout.layout_id],
                ['Envelope Type', envelope.type.value if envelope and hasattr(envelope.type, 'value') else str(envelope.type) if envelope else 'Unknown'],
                ['Module Count', str(len(layout.modules))],
                ['Envelope ID', layout.envelope_id]
            ]
            
            if envelope:
                details.extend([
                    ['Envelope Dimensions', self._format_envelope_dimensions(envelope)],
                    ['Coordinate Frame', envelope.coordinate_frame]
                ])
            
            details_table = Table(details, colWidths=[2*inch, 3*inch])
            details_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(details_table)
            story.append(Spacer(1, 12))
            
            # Module breakdown
            module_counts = {}
            for module in layout.modules:
                module_type = module.type.value if hasattr(module.type, 'value') else str(module.type)
                module_counts[module_type] = module_counts.get(module_type, 0) + 1
            
            story.append(Paragraph("Module Breakdown:", styles['Heading3']))
            
            module_data = [['Module Type', 'Count']]
            for module_type, count in sorted(module_counts.items()):
                module_data.append([module_type.replace('_', ' ').title(), str(count)])
            
            module_table = Table(module_data, colWidths=[2*inch, 1*inch])
            module_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(module_table)
            story.append(Spacer(1, 20))
        
        return story
    
    def _create_metrics_section(self, layouts: List[LayoutSpec], styles) -> List:
        """Create performance metrics section"""
        story = []
        
        story.append(Paragraph("Performance Metrics", styles['Heading1']))
        story.append(Spacer(1, 12))
        
        # Create metrics comparison table
        if len(layouts) == 1:
            layout = layouts[0]
            metrics_data = [
                ['Metric', 'Value', 'Unit'],
                ['Mean Transit Time', f"{layout.kpis.mean_transit_time:.1f}", 'seconds'],
                ['Emergency Egress Time', f"{layout.kpis.egress_time:.1f}", 'seconds'],
                ['Total Mass', f"{layout.kpis.mass_total:.0f}", 'kg'],
                ['Power Budget', f"{layout.kpis.power_budget:.0f}", 'W'],
                ['Thermal Margin', f"{layout.kpis.thermal_margin*100:.1f}", '%'],
                ['LSS Margin', f"{layout.kpis.lss_margin*100:.1f}", '%'],
                ['Stowage Utilization', f"{layout.kpis.stowage_utilization*100:.1f}", '%']
            ]
        else:
            # Multi-layout comparison
            metrics_data = [['Metric'] + [f"Layout {i+1}" for i in range(len(layouts))] + ['Unit']]
            
            metric_names = [
                ('Mean Transit Time', 'mean_transit_time', 'seconds'),
                ('Emergency Egress Time', 'egress_time', 'seconds'),
                ('Total Mass', 'mass_total', 'kg'),
                ('Power Budget', 'power_budget', 'W'),
                ('Thermal Margin', 'thermal_margin', '%'),
                ('LSS Margin', 'lss_margin', '%'),
                ('Stowage Utilization', 'stowage_utilization', '%')
            ]
            
            for name, key, unit in metric_names:
                row = [name]
                for layout in layouts:
                    value = getattr(layout.kpis, key)
                    if key in ['thermal_margin', 'lss_margin', 'stowage_utilization']:
                        row.append(f"{value*100:.1f}")
                    else:
                        row.append(f"{value:.1f}")
                row.append(unit)
                metrics_data.append(row)
        
        metrics_table = Table(metrics_data)
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(metrics_table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _create_technical_analysis(self, layouts: List[LayoutSpec], envelopes: Dict[str, EnvelopeSpec], styles) -> List:
        """Create technical analysis section"""
        story = []
        
        story.append(Paragraph("Technical Analysis", styles['Heading1']))
        story.append(Spacer(1, 12))
        
        for layout in layouts:
            story.append(Paragraph(f"Analysis: {layout.layout_id}", styles['Heading2']))
            
            # Explainability text
            if layout.explainability:
                story.append(Paragraph("Design Rationale:", styles['Heading3']))
                story.append(Paragraph(layout.explainability, styles['Normal']))
                story.append(Spacer(1, 12))
            
            # Technical details
            story.append(Paragraph("Technical Details:", styles['Heading3']))
            
            technical_text = f"""
            This layout configuration demonstrates specific design choices optimized for the given 
            mission parameters. The arrangement of {len(layout.modules)} modules follows established 
            habitat design principles while addressing unique operational requirements.
            
            Key technical considerations:
            • Module connectivity ensures pressurized pathways between all functional areas
            • Emergency egress paths meet safety requirements with {layout.kpis.egress_time:.1f} second evacuation time
            • Life support systems maintain {layout.kpis.lss_margin*100:.1f}% safety margin
            • Power distribution supports {layout.kpis.power_budget:.0f} W total load
            """
            
            story.append(Paragraph(technical_text, styles['Normal']))
            story.append(Spacer(1, 20))
        
        return story
    
    def _create_comparison_section(self, layouts: List[LayoutSpec], styles) -> List:
        """Create layout comparison section"""
        story = []
        
        story.append(Paragraph("Layout Comparison", styles['Heading1']))
        story.append(Spacer(1, 12))
        
        # Identify best and worst performing layouts for each metric
        metrics = ['mean_transit_time', 'egress_time', 'mass_total', 'power_budget']
        
        comparison_text = "Comparative Analysis:\n\n"
        
        for metric in metrics:
            values = [(i, getattr(layout.kpis, metric)) for i, layout in enumerate(layouts)]
            
            if values:
                if metric in ['mean_transit_time', 'egress_time', 'mass_total']:
                    # Lower is better
                    best_idx, best_val = min(values, key=lambda x: x[1])
                    worst_idx, worst_val = max(values, key=lambda x: x[1])
                else:
                    # Higher is better (for power budget, we want efficiency)
                    best_idx, best_val = max(values, key=lambda x: x[1])
                    worst_idx, worst_val = min(values, key=lambda x: x[1])
                
                metric_name = metric.replace('_', ' ').replace('Time', ' Time').title()
                comparison_text += f"• {metric_name}: Best - Layout {best_idx+1} ({best_val:.1f}), "
                comparison_text += f"Worst - Layout {worst_idx+1} ({worst_val:.1f})\n"
        
        story.append(Paragraph(comparison_text, styles['Normal']))
        story.append(Spacer(1, 20))
        
        return story
    
    def _create_visualization_section(self, layouts: List[LayoutSpec], envelopes: Dict[str, EnvelopeSpec], styles) -> List:
        """Create visualization section with layout diagrams"""
        story = []
        
        story.append(Paragraph("Layout Visualizations", styles['Heading1']))
        story.append(Spacer(1, 12))
        
        for i, layout in enumerate(layouts):
            story.append(Paragraph(f"Layout {i+1} Visualization", styles['Heading2']))
            
            # Create a simple 2D layout diagram
            diagram_path = self._create_layout_diagram(layout, envelopes.get(layout.envelope_id))
            if diagram_path:
                try:
                    img = RLImage(diagram_path, width=5*inch, height=4*inch)
                    story.append(img)
                    story.append(Spacer(1, 12))
                    
                    # Clean up temporary file
                    Path(diagram_path).unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Failed to add diagram to report: {e}")
            
            story.append(Spacer(1, 20))
        
        return story
    
    def _create_recommendations_section(self, layouts: List[LayoutSpec], styles) -> List:
        """Create recommendations section"""
        story = []
        
        story.append(Paragraph("Recommendations", styles['Heading1']))
        story.append(Spacer(1, 12))
        
        if len(layouts) == 1:
            layout = layouts[0]
            recommendations = self._generate_single_layout_recommendations(layout)
        else:
            recommendations = self._generate_multi_layout_recommendations(layouts)
        
        for i, rec in enumerate(recommendations, 1):
            story.append(Paragraph(f"{i}. {rec}", styles['Normal']))
            story.append(Spacer(1, 8))
        
        story.append(Spacer(1, 20))
        
        return story
    
    def _create_appendices(self, layouts: List[LayoutSpec], envelopes: Dict[str, EnvelopeSpec], styles) -> List:
        """Create appendices section"""
        story = []
        
        story.append(Paragraph("Appendices", styles['Heading1']))
        story.append(Spacer(1, 12))
        
        # Appendix A: Module Specifications
        story.append(Paragraph("Appendix A: Module Specifications", styles['Heading2']))
        
        # Get all unique module types
        all_module_types = set()
        for layout in layouts:
            for module in layout.modules:
                all_module_types.add(module.type)
        
        for module_type in sorted(all_module_types):
            module_defs = self.module_library.get_modules_by_type(module_type)
            module_def = module_defs[0] if module_defs else None
            if module_def:
                module_type_str = module_type.value if hasattr(module_type, 'value') else str(module_type)
                story.append(Paragraph(f"{module_type_str.replace('_', ' ').title()}", styles['Heading3']))
                
                spec_text = f"""
                Dimensions: {module_def.spec.bbox_m.x} × {module_def.spec.bbox_m.y} × {module_def.spec.bbox_m.z} m
                Mass: {module_def.spec.mass_kg} kg
                Power: {module_def.spec.power_w} W
                Stowage: {module_def.spec.stowage_m3} m³
                """
                
                story.append(Paragraph(spec_text, styles['Normal']))
                story.append(Spacer(1, 8))
        
        story.append(Spacer(1, 20))
        
        return story
    
    def _format_envelope_dimensions(self, envelope: EnvelopeSpec) -> str:
        """Format envelope dimensions for display"""
        if envelope.type == "cylinder":
            return f"R={envelope.params.get('radius', 'N/A')}m, L={envelope.params.get('length', 'N/A')}m"
        elif envelope.type == "box":
            return f"{envelope.params.get('width', 'N/A')} × {envelope.params.get('height', 'N/A')} × {envelope.params.get('depth', 'N/A')} m"
        elif envelope.type == "torus":
            return f"R1={envelope.params.get('major_radius', 'N/A')}m, R2={envelope.params.get('minor_radius', 'N/A')}m"
        else:
            return "Custom geometry"
    
    def _create_layout_diagram(self, layout: LayoutSpec, envelope: Optional[EnvelopeSpec]) -> Optional[str]:
        """Create a simple 2D layout diagram"""
        try:
            fig, ax = plt.subplots(1, 1, figsize=(8, 6))
            
            # Draw envelope outline
            if envelope:
                if envelope.type == "cylinder":
                    radius = envelope.params.get('radius', 3.0)
                    circle = plt.Circle((0, 0), radius, fill=False, color='black', linewidth=2)
                    ax.add_patch(circle)
                    ax.set_xlim(-radius*1.2, radius*1.2)
                    ax.set_ylim(-radius*1.2, radius*1.2)
                elif envelope.type == "box":
                    width = envelope.params.get('width', 6.0)
                    height = envelope.params.get('height', 6.0)
                    rect = plt.Rectangle((-width/2, -height/2), width, height, 
                                       fill=False, color='black', linewidth=2)
                    ax.add_patch(rect)
                    ax.set_xlim(-width*0.6, width*0.6)
                    ax.set_ylim(-height*0.6, height*0.6)
            
            # Draw modules
            colors_map = {
                'sleep_quarter': 'lightblue',
                'galley': 'orange',
                'laboratory': 'lightgreen',
                'airlock': 'red',
                'mechanical': 'gray',
                'medical': 'yellow',
                'exercise': 'purple',
                'storage': 'cyan'
            }
            
            for module in layout.modules:
                x, y = module.position[0], module.position[1]
                module_type = module.type.value if hasattr(module.type, 'value') else str(module.type)
                color = colors_map.get(module_type, 'lightgray')
                
                # Draw module as rectangle
                rect = plt.Rectangle((x-0.5, y-0.5), 1.0, 1.0, 
                                   facecolor=color, edgecolor='black', alpha=0.7)
                ax.add_patch(rect)
                
                # Add module label
                ax.text(x, y, module_type.replace('_', '\n'), 
                       ha='center', va='center', fontsize=8, weight='bold')
            
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            ax.set_title(f'Layout: {layout.layout_id}')
            ax.set_xlabel('X Position (m)')
            ax.set_ylabel('Y Position (m)')
            
            # Save to temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix='.png')
            try:
                plt.savefig(temp_path, dpi=150, bbox_inches='tight')
                plt.close()
                return temp_path
            finally:
                os.close(temp_fd)
            
        except Exception as e:
            logger.error(f"Failed to create layout diagram: {e}")
            return None
    
    def _generate_single_layout_recommendations(self, layout: LayoutSpec) -> List[str]:
        """Generate recommendations for a single layout"""
        recommendations = []
        
        # Analyze metrics and provide recommendations
        if layout.kpis.mean_transit_time > 30:
            recommendations.append(
                "Consider relocating frequently accessed modules closer together to reduce transit times."
            )
        
        if layout.kpis.egress_time > 60:
            recommendations.append(
                "Review emergency egress paths and consider additional airlocks or wider corridors."
            )
        
        if layout.kpis.lss_margin < 0.2:
            recommendations.append(
                "Life support system margin is low. Consider adding redundant LSS components or reducing crew size."
            )
        
        if layout.kpis.stowage_utilization < 0.7:
            recommendations.append(
                "Stowage utilization is below optimal. Consider adding storage modules or optimizing existing storage."
            )
        
        if not recommendations:
            recommendations.append(
                "This layout demonstrates good performance across all key metrics. Consider minor optimizations based on specific mission requirements."
            )
        
        return recommendations
    
    def _generate_multi_layout_recommendations(self, layouts: List[LayoutSpec]) -> List[str]:
        """Generate recommendations for multiple layouts"""
        recommendations = []
        
        # Find best performing layout for each metric
        best_transit = min(layouts, key=lambda l: l.kpis.mean_transit_time)
        best_egress = min(layouts, key=lambda l: l.kpis.egress_time)
        
        recommendations.append(
            f"For optimal crew efficiency, consider Layout {layouts.index(best_transit)+1} "
            f"which achieves the shortest mean transit time of {best_transit.kpis.mean_transit_time:.1f} seconds."
        )
        
        recommendations.append(
            f"For emergency preparedness, Layout {layouts.index(best_egress)+1} "
            f"provides the fastest egress time of {best_egress.kpis.egress_time:.1f} seconds."
        )
        
        recommendations.append(
            "Consider hybrid approaches that combine the best features from multiple layouts "
            "to achieve balanced performance across all mission objectives."
        )
        
        return recommendations
    
    async def generate_png_snapshot(
        self,
        layout: LayoutSpec,
        envelope: EnvelopeSpec,
        width: int = 1920,
        height: int = 1080,
        view_angle: str = "top"
    ) -> bytes:
        """
        Generate PNG snapshot of layout for presentations
        
        Args:
            layout: Layout specification
            envelope: Envelope specification
            width: Image width in pixels
            height: Image height in pixels
            view_angle: View angle ("top", "side", "isometric")
            
        Returns:
            PNG image as bytes
        """
        try:
            loop = asyncio.get_event_loop()
            png_data = await loop.run_in_executor(
                self.executor,
                self._create_png_snapshot,
                layout,
                envelope,
                width,
                height,
                view_angle
            )
            return png_data
            
        except Exception as e:
            logger.error(f"Failed to generate PNG snapshot: {str(e)}")
            raise ReportError(f"PNG snapshot generation failed: {str(e)}")
    
    def _create_png_snapshot(
        self,
        layout: LayoutSpec,
        envelope: EnvelopeSpec,
        width: int,
        height: int,
        view_angle: str
    ) -> bytes:
        """Create PNG snapshot (runs in thread pool)"""
        
        # Create high-resolution matplotlib figure
        dpi = 150
        fig_width = width / dpi
        fig_height = height / dpi
        
        fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height), dpi=dpi)
        
        # Set background color
        fig.patch.set_facecolor('white')
        ax.set_facecolor('white')
        
        # Draw envelope
        if envelope.type == "cylinder":
            radius = envelope.params.get('radius', 3.0)
            circle = plt.Circle((0, 0), radius, fill=False, color='navy', linewidth=3)
            ax.add_patch(circle)
            ax.set_xlim(-radius*1.1, radius*1.1)
            ax.set_ylim(-radius*1.1, radius*1.1)
        elif envelope.type == "box":
            width_env = envelope.params.get('width', 6.0)
            height_env = envelope.params.get('height', 6.0)
            rect = plt.Rectangle((-width_env/2, -height_env/2), width_env, height_env,
                               fill=False, color='navy', linewidth=3)
            ax.add_patch(rect)
            ax.set_xlim(-width_env*0.55, width_env*0.55)
            ax.set_ylim(-height_env*0.55, height_env*0.55)
        
        # Draw modules with better styling
        colors_map = {
            'sleep_quarter': '#87CEEB',  # Sky blue
            'galley': '#FFA500',        # Orange
            'laboratory': '#90EE90',    # Light green
            'airlock': '#FF6B6B',       # Light red
            'mechanical': '#D3D3D3',    # Light gray
            'medical': '#FFD700',       # Gold
            'exercise': '#DDA0DD',      # Plum
            'storage': '#40E0D0'        # Turquoise
        }
        
        for module in layout.modules:
            x, y = module.position[0], module.position[1]
            module_type = module.type.value if hasattr(module.type, 'value') else str(module.type)
            color = colors_map.get(module_type, '#F0F0F0')
            
            # Draw module with rounded corners effect
            rect = plt.Rectangle((x-0.8, y-0.8), 1.6, 1.6,
                               facecolor=color, edgecolor='black', linewidth=2, alpha=0.8)
            ax.add_patch(rect)
            
            # Add module label with better formatting
            label = module_type.replace('_', ' ').title()
            ax.text(x, y, label, ha='center', va='center', 
                   fontsize=10, weight='bold', color='black')
        
        # Style the plot
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.2, linestyle='--')
        ax.set_title(f'Habitat Layout: {layout.layout_id}', fontsize=16, weight='bold', pad=20)
        ax.set_xlabel('X Position (m)', fontsize=12)
        ax.set_ylabel('Y Position (m)', fontsize=12)
        
        # Remove top and right spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Save to bytes
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=dpi, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        img_buffer.seek(0)
        return img_buffer.getvalue()
    
    async def generate_executive_summary(
        self,
        layouts: List[LayoutSpec],
        envelopes: Dict[str, EnvelopeSpec],
        max_length: int = 500
    ) -> str:
        """
        Generate executive summary with key findings
        
        Args:
            layouts: List of layout specifications
            envelopes: Dictionary mapping envelope IDs to envelope specs
            max_length: Maximum summary length in words
            
        Returns:
            Executive summary text
        """
        try:
            if len(layouts) == 1:
                return self._generate_single_layout_summary(layouts[0], envelopes.get(layouts[0].envelope_id), max_length)
            else:
                return self._generate_multi_layout_summary(layouts, envelopes, max_length)
                
        except Exception as e:
            logger.error(f"Failed to generate executive summary: {str(e)}")
            raise ReportError(f"Executive summary generation failed: {str(e)}")
    
    def _generate_single_layout_summary(self, layout: LayoutSpec, envelope: Optional[EnvelopeSpec], max_length: int) -> str:
        """Generate summary for single layout"""
        
        summary_parts = []
        
        # Basic layout info
        envelope_type = envelope.type.value if envelope and hasattr(envelope.type, 'value') else str(envelope.type) if envelope else "unknown"
        envelope_type = envelope.type.value if envelope and hasattr(envelope.type, 'value') else str(envelope.type) if envelope else "unknown"
        summary_parts.append(
            f"Analysis of habitat layout '{layout.layout_id}' with {len(layout.modules)} modules "
            f"in a {envelope_type} envelope configuration."
        )
        
        # Key performance metrics
        transit_time = layout.kpis.mean_transit_time
        egress_time = layout.kpis.egress_time
        lss_margin = layout.kpis.lss_margin
        
        summary_parts.append(
            f"Performance highlights include {transit_time:.1f}s mean transit time, "
            f"{egress_time:.1f}s emergency egress, and {lss_margin*100:.1f}% LSS safety margin."
        )
        
        # Key findings
        if layout.explainability:
            summary_parts.append(layout.explainability[:200] + "...")
        
        # Recommendations
        if lss_margin < 0.2:
            summary_parts.append("Recommend increasing life support redundancy.")
        elif transit_time > 30:
            summary_parts.append("Consider optimizing module placement for efficiency.")
        else:
            summary_parts.append("Layout demonstrates strong performance across key metrics.")
        
        full_summary = " ".join(summary_parts)
        
        # Truncate if too long
        words = full_summary.split()
        if len(words) > max_length:
            full_summary = " ".join(words[:max_length]) + "..."
        
        return full_summary
    
    def _generate_multi_layout_summary(self, layouts: List[LayoutSpec], envelopes: Dict[str, EnvelopeSpec], max_length: int) -> str:
        """Generate summary for multiple layouts"""
        
        summary_parts = []
        
        # Basic comparison info
        summary_parts.append(
            f"Comparative analysis of {len(layouts)} habitat layout configurations "
            f"with varying module arrangements and performance characteristics."
        )
        
        # Performance comparison
        transit_times = [l.kpis.mean_transit_time for l in layouts]
        best_transit = min(t for t in transit_times if t != float('inf'))
        worst_transit = max(t for t in transit_times if t != float('inf'))
        
        summary_parts.append(
            f"Transit time performance ranges from {best_transit:.1f}s to {worst_transit:.1f}s, "
            f"indicating significant optimization opportunities."
        )
        
        # Key recommendation
        best_layout_idx = transit_times.index(best_transit)
        summary_parts.append(
            f"Layout {best_layout_idx + 1} demonstrates optimal efficiency characteristics "
            f"and is recommended for crew productivity-focused missions."
        )
        
        full_summary = " ".join(summary_parts)
        
        # Truncate if too long
        words = full_summary.split()
        if len(words) > max_length:
            full_summary = " ".join(words[:max_length]) + "..."
        
        return full_summary


# Global report generator instance
_report_generator: Optional[ReportGenerator] = None


def get_report_generator() -> ReportGenerator:
    """Get the global report generator instance"""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator