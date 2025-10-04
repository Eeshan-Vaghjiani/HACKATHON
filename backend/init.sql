-- Initialize HabitatCanvas database

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Envelopes table
CREATE TABLE IF NOT EXISTS envelopes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('cylinder', 'torus', 'box', 'freeform')),
    params JSONB NOT NULL,
    coordinate_frame VARCHAR(10) DEFAULT 'local' CHECK (coordinate_frame IN ('local', 'global')),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Layouts table
CREATE TABLE IF NOT EXISTS layouts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    envelope_id UUID REFERENCES envelopes(id) ON DELETE CASCADE,
    name VARCHAR(255),
    modules JSONB NOT NULL,
    kpis JSONB NOT NULL,
    explainability TEXT,
    generation_params JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Simulation results table
CREATE TABLE IF NOT EXISTS simulation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    layout_id UUID REFERENCES layouts(id) ON DELETE CASCADE,
    simulation_type VARCHAR(50) NOT NULL,
    results JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_envelopes_type ON envelopes(type);
CREATE INDEX IF NOT EXISTS idx_envelopes_created_at ON envelopes(created_at);
CREATE INDEX IF NOT EXISTS idx_layouts_envelope_id ON layouts(envelope_id);
CREATE INDEX IF NOT EXISTS idx_layouts_created_at ON layouts(created_at);
CREATE INDEX IF NOT EXISTS idx_simulation_results_layout_id ON simulation_results(layout_id);
CREATE INDEX IF NOT EXISTS idx_simulation_results_type ON simulation_results(simulation_type);

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_envelopes_updated_at BEFORE UPDATE ON envelopes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_layouts_updated_at BEFORE UPDATE ON layouts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();