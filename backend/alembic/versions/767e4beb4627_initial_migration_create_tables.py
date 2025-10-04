"""Initial migration - create tables

Revision ID: 767e4beb4627
Revises: 
Create Date: 2025-10-04 13:13:32.346865

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '767e4beb4627'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create envelopes table
    op.create_table('envelopes',
        sa.Column('id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('params', sa.JSON(), nullable=False),
        sa.Column('coordinate_frame', sa.String(50), nullable=False),
        sa.Column('creator', sa.String(255), nullable=False),
        sa.Column('version', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('min_volume', sa.Float(), nullable=True),
        sa.Column('max_volume', sa.Float(), nullable=True),
        sa.Column('min_dimension', sa.Float(), nullable=True),
        sa.Column('max_dimension', sa.Float(), nullable=True),
        sa.Column('volume', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_envelopes_name'), 'envelopes', ['name'], unique=False)

    # Create module_library table
    op.create_table('module_library',
        sa.Column('module_id', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('bbox_x', sa.Float(), nullable=False),
        sa.Column('bbox_y', sa.Float(), nullable=False),
        sa.Column('bbox_z', sa.Float(), nullable=False),
        sa.Column('mass_kg', sa.Float(), nullable=False),
        sa.Column('power_w', sa.Float(), nullable=False),
        sa.Column('stowage_m3', sa.Float(), nullable=False),
        sa.Column('connectivity_ports', sa.JSON(), nullable=False),
        sa.Column('adjacency_preferences', sa.JSON(), nullable=False),
        sa.Column('adjacency_restrictions', sa.JSON(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('manufacturer', sa.String(255), nullable=True),
        sa.Column('model', sa.String(255), nullable=True),
        sa.Column('certification', sa.String(255), nullable=True),
        sa.Column('volume', sa.Float(), nullable=True),
        sa.Column('density_kg_m3', sa.Float(), nullable=True),
        sa.Column('power_density_w_m3', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('module_id')
    )
    op.create_index(op.f('ix_module_library_type'), 'module_library', ['type'], unique=False)

    # Create layouts table
    op.create_table('layouts',
        sa.Column('layout_id', sa.String(255), nullable=False),
        sa.Column('envelope_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('modules', sa.JSON(), nullable=False),
        sa.Column('explainability', sa.Text(), nullable=False),
        sa.Column('mean_transit_time', sa.Float(), nullable=False),
        sa.Column('egress_time', sa.Float(), nullable=False),
        sa.Column('mass_total', sa.Float(), nullable=False),
        sa.Column('power_budget', sa.Float(), nullable=False),
        sa.Column('thermal_margin', sa.Float(), nullable=False),
        sa.Column('lss_margin', sa.Float(), nullable=False),
        sa.Column('stowage_utilization', sa.Float(), nullable=False),
        sa.Column('connectivity_score', sa.Float(), nullable=True),
        sa.Column('safety_score', sa.Float(), nullable=True),
        sa.Column('efficiency_score', sa.Float(), nullable=True),
        sa.Column('volume_utilization', sa.Float(), nullable=True),
        sa.Column('generation_params', sa.JSON(), nullable=True),
        sa.Column('version', sa.String(50), nullable=True),
        sa.Column('total_mass_constraint', sa.Float(), nullable=True),
        sa.Column('total_power_constraint', sa.Float(), nullable=True),
        sa.Column('min_clearance_constraint', sa.Float(), nullable=True),
        sa.Column('module_count', sa.Integer(), nullable=True),
        sa.Column('module_types_count', sa.JSON(), nullable=True),
        sa.Column('has_airlock', sa.Boolean(), nullable=True),
        sa.Column('layout_bounds', sa.JSON(), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('critical_issues', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['envelope_id'], ['envelopes.id'], ),
        sa.PrimaryKeyConstraint('layout_id')
    )
    op.create_index(op.f('ix_layouts_envelope_id'), 'layouts', ['envelope_id'], unique=False)

    # Create mission_profiles table
    op.create_table('mission_profiles',
        sa.Column('id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('crew_size', sa.Integer(), nullable=False),
        sa.Column('duration_days', sa.Integer(), nullable=False),
        sa.Column('priority_weights', sa.JSON(), nullable=False),
        sa.Column('activity_schedule', sa.JSON(), nullable=False),
        sa.Column('emergency_scenarios', sa.JSON(), nullable=False),
        sa.Column('max_crew_size', sa.Integer(), nullable=True),
        sa.Column('max_duration', sa.Integer(), nullable=True),
        sa.Column('min_safety_margin', sa.Float(), nullable=True),
        sa.Column('total_crew_hours', sa.Float(), nullable=True),
        sa.Column('daily_activity_total', sa.Float(), nullable=True),
        sa.Column('is_template', sa.Boolean(), nullable=False),
        sa.Column('template_category', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mission_profiles_name'), 'mission_profiles', ['name'], unique=False)

    # Create simulation_results table
    op.create_table('simulation_results',
        sa.Column('id', sa.String(255), nullable=False),
        sa.Column('layout_id', sa.String(255), nullable=False),
        sa.Column('simulation_type', sa.String(50), nullable=False),
        sa.Column('simulation_params', sa.JSON(), nullable=True),
        sa.Column('results', sa.JSON(), nullable=False),
        sa.Column('duration_simulated', sa.Float(), nullable=True),
        sa.Column('agents_count', sa.Integer(), nullable=True),
        sa.Column('avg_congestion', sa.Float(), nullable=True),
        sa.Column('max_queue_time', sa.Float(), nullable=True),
        sa.Column('bottleneck_locations', sa.JSON(), nullable=True),
        sa.Column('traffic_heatmap', sa.JSON(), nullable=True),
        sa.Column('occupancy_heatmap', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['layout_id'], ['layouts.layout_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_simulation_results_layout_id'), 'simulation_results', ['layout_id'], unique=False)
    op.create_index(op.f('ix_simulation_results_simulation_type'), 'simulation_results', ['simulation_type'], unique=False)

    # Create export_jobs table
    op.create_table('export_jobs',
        sa.Column('id', sa.String(255), nullable=False),
        sa.Column('layout_id', sa.String(255), nullable=False),
        sa.Column('export_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('progress', sa.Float(), nullable=False),
        sa.Column('export_params', sa.JSON(), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('download_url', sa.String(500), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['layout_id'], ['layouts.layout_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_export_jobs_layout_id'), 'export_jobs', ['layout_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_export_jobs_layout_id'), table_name='export_jobs')
    op.drop_table('export_jobs')
    
    op.drop_index(op.f('ix_simulation_results_simulation_type'), table_name='simulation_results')
    op.drop_index(op.f('ix_simulation_results_layout_id'), table_name='simulation_results')
    op.drop_table('simulation_results')
    
    op.drop_index(op.f('ix_mission_profiles_name'), table_name='mission_profiles')
    op.drop_table('mission_profiles')
    
    op.drop_index(op.f('ix_layouts_envelope_id'), table_name='layouts')
    op.drop_table('layouts')
    
    op.drop_index(op.f('ix_module_library_type'), table_name='module_library')
    op.drop_table('module_library')
    
    op.drop_index(op.f('ix_envelopes_name'), table_name='envelopes')
    op.drop_table('envelopes')
