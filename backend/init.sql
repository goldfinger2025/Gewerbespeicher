-- Gewerbespeicher Planner - Database Schema
-- PostgreSQL 16+

-- Create UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TENANTS TABLE (for multi-tenant/white-label support)
-- ============================================================
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Basic Info
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,

    -- Contact Info
    company_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    address VARCHAR(500),
    postal_code VARCHAR(10),
    city VARCHAR(100),
    country VARCHAR(100) DEFAULT 'Deutschland',

    -- White-Label Branding
    logo_url VARCHAR(500),
    favicon_url VARCHAR(500),
    primary_color VARCHAR(7) DEFAULT '#2563eb',
    secondary_color VARCHAR(7) DEFAULT '#10b981',
    accent_color VARCHAR(7) DEFAULT '#f59e0b',
    font_family VARCHAR(100) DEFAULT 'Inter',

    -- Custom Domain
    custom_domain VARCHAR(255) UNIQUE,

    -- Feature Flags
    features JSONB DEFAULT '{}',

    -- Limits
    max_users DECIMAL DEFAULT 10,
    max_projects DECIMAL DEFAULT 100,
    max_storage_mb DECIMAL DEFAULT 1000,

    -- Subscription / Billing
    subscription_plan VARCHAR(50) DEFAULT 'starter',
    subscription_status VARCHAR(50) DEFAULT 'active',
    trial_ends_at TIMESTAMP,

    -- API Access
    api_enabled BOOLEAN DEFAULT false,
    api_rate_limit DECIMAL DEFAULT 100,

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tenants_slug ON tenants(slug);

-- ============================================================
-- API KEYS TABLE
-- ============================================================
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(10) NOT NULL,

    -- Permissions
    scopes JSONB DEFAULT '["read"]',

    -- Rate Limiting
    rate_limit DECIMAL DEFAULT 100,

    -- Status
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_keys_tenant_id ON api_keys(tenant_id);
CREATE INDEX idx_api_keys_key_prefix ON api_keys(key_prefix);

-- ============================================================
-- USERS TABLE
-- ============================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    company_name VARCHAR(255),
    phone VARCHAR(20),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_tenant_id ON users(tenant_id);

-- ============================================================
-- PROJECTS TABLE
-- ============================================================
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Customer Info
    customer_name VARCHAR(255) NOT NULL,
    customer_email VARCHAR(255),
    customer_phone VARCHAR(20),
    customer_company VARCHAR(255),
    
    -- Location
    address VARCHAR(500) NOT NULL,
    postal_code VARCHAR(10),
    city VARCHAR(100),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    
    -- Project Data
    project_name VARCHAR(255),
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft', -- draft, active, completed, archived
    
    -- PV System
    pv_peak_power_kw DECIMAL(10, 2),
    pv_orientation VARCHAR(50),
    pv_tilt_angle DECIMAL(5, 2),
    roof_area_sqm DECIMAL(10, 2),
    
    -- Battery System
    battery_capacity_kwh DECIMAL(10, 2),
    battery_power_kw DECIMAL(10, 2),
    battery_chemistry VARCHAR(50),
    battery_manufacturer VARCHAR(100),
    
    -- Consumption
    annual_consumption_kwh DECIMAL(10, 2),
    peak_load_kw DECIMAL(10, 2),
    
    -- Cost Parameters
    electricity_price_eur_kwh DECIMAL(6, 4),
    grid_fee_eur_kwh DECIMAL(6, 4),
    feed_in_tariff_eur_kwh DECIMAL(6, 4),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_postal_code ON projects(postal_code);

-- ============================================================
-- SIMULATIONS TABLE
-- ============================================================
CREATE TABLE simulations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    
    -- Parameters
    simulation_type VARCHAR(50) DEFAULT 'standard',
    time_resolution VARCHAR(20) DEFAULT 'hourly',
    
    -- Annual Results
    pv_generation_kwh DECIMAL(12, 2),
    consumed_from_grid_kwh DECIMAL(12, 2),
    self_consumed_kwh DECIMAL(12, 2),
    fed_to_grid_kwh DECIMAL(12, 2),
    battery_discharge_cycles DECIMAL(10, 2),
    
    -- Key Metrics
    autonomy_degree_percent DECIMAL(5, 2),
    self_consumption_ratio_percent DECIMAL(5, 2),
    pv_coverage_percent DECIMAL(5, 2),
    
    -- Financial Results
    annual_savings_eur DECIMAL(10, 2),
    total_savings_eur DECIMAL(12, 2),
    payback_period_years DECIMAL(5, 1),
    npv_eur DECIMAL(12, 2),
    irr_percent DECIMAL(6, 2),
    
    -- Detailed Data (JSON)
    hourly_data JSONB,
    monthly_summary JSONB,
    
    -- Status
    is_latest BOOLEAN DEFAULT true,
    status VARCHAR(50) DEFAULT 'completed',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_simulations_project_id ON simulations(project_id);
CREATE INDEX idx_simulations_latest ON simulations(project_id, is_latest);

-- ============================================================
-- OFFERS TABLE
-- ============================================================
CREATE TABLE offers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id UUID NOT NULL REFERENCES simulations(id),
    project_id UUID NOT NULL REFERENCES projects(id),

    -- Offer Metadata
    offer_number VARCHAR(50) UNIQUE,
    offer_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_until DATE,

    -- Content
    offer_text TEXT,
    technical_specs JSONB,
    components_bom JSONB,
    pricing_breakdown JSONB,

    -- Professional Offer Details
    warranty_info JSONB,
    subsidy_info JSONB,
    payment_terms TEXT,
    terms_reference VARCHAR(255),
    service_package JSONB,

    -- E-Signature
    signature_link VARCHAR(500),
    is_signed BOOLEAN DEFAULT false,
    signed_at TIMESTAMP,
    signer_name VARCHAR(255),

    -- PDF
    pdf_path VARCHAR(500),
    pdf_generated_at TIMESTAMP,

    -- CRM Integration
    hubspot_deal_id VARCHAR(100),
    crm_sync_status VARCHAR(50) DEFAULT 'pending',

    -- Status
    status VARCHAR(50) DEFAULT 'draft',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_offers_simulation_id ON offers(simulation_id);
CREATE INDEX idx_offers_project_id ON offers(project_id);
CREATE INDEX idx_offers_status ON offers(status);

-- ============================================================
-- COMPONENTS TABLE
-- ============================================================
CREATE TABLE components (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Classification
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(50),
    
    -- Product Info
    manufacturer VARCHAR(100) NOT NULL,
    model VARCHAR(150) NOT NULL,
    description TEXT,
    specification JSONB,
    
    -- Pricing
    unit_price_eur DECIMAL(10, 2),
    supplier_sku VARCHAR(100),
    availability_status VARCHAR(50),
    
    -- Compatibility
    compatible_with JSONB,
    
    -- Admin
    is_active BOOLEAN DEFAULT true,
    data_source VARCHAR(100),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_components_category ON components(category);
CREATE INDEX idx_components_manufacturer ON components(manufacturer);

-- ============================================================
-- AUDIT LOG TABLE
-- ============================================================
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    entity_type VARCHAR(50),
    entity_id UUID,
    action VARCHAR(50),
    changes JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);

-- ============================================================
-- DEMO USER
-- ============================================================
INSERT INTO users (email, hashed_password, first_name, last_name, company_name, role, is_admin)
VALUES (
    'demo@ews-gmbh.de',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VttYVfQPNK8WGO', -- password: demo123
    'Demo',
    'User',
    'EWS GmbH',
    'owner',
    true
);

-- ============================================================
-- SAMPLE COMPONENTS
-- ============================================================
INSERT INTO components (category, subcategory, manufacturer, model, description, specification, unit_price_eur, availability_status)
VALUES 
    ('battery', 'commercial', 'BYD', 'Battery-Box Premium HVS 12.8', 'Hochvolt-Speicher für Gewerbe', 
     '{"capacity_kwh": 12.8, "voltage_v": 409.6, "cycles": 6000, "chemistry": "LFP", "warranty_years": 10}', 
     5500.00, 'in_stock'),
    ('battery', 'commercial', 'Huawei', 'LUNA2000-15-S0', 'Modularer Gewerbespeicher',
     '{"capacity_kwh": 15.0, "voltage_v": 600, "cycles": 4000, "chemistry": "LFP", "warranty_years": 10}',
     6200.00, 'in_stock'),
    ('inverter', 'hybrid', 'Fronius', 'Symo GEN24 10.0 Plus', 'Hybrid-Wechselrichter',
     '{"power_kw": 10.0, "efficiency_percent": 97.6, "mppt_count": 2, "phases": 3}',
     3200.00, 'in_stock'),
    ('inverter', 'commercial', 'Huawei', 'SUN2000-50KTL-M3', 'Gewerbewechselrichter 50kW',
     '{"power_kw": 50.0, "efficiency_percent": 98.6, "mppt_count": 6, "phases": 3}',
     4800.00, 'in_stock'),
    ('pv_module', 'monocrystalline', 'Trina Solar', 'Vertex S+ TSM-445NEG9R.28', 'n-Type TOPCon Modul 445W',
     '{"power_w": 445, "efficiency_percent": 22.0, "bifacial": true, "warranty_years": 25}',
     165.00, 'in_stock');
