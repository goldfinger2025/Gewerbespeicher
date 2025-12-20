-- Migration: Add professional offer fields to offers table
-- Run this on your production database to add missing offer columns
-- Date: 2025-12-20

-- ============================================================
-- ADD PROFESSIONAL OFFER FIELDS TO OFFERS TABLE
-- These columns are required for complete offer generation
-- ============================================================

-- Add warranty_info column (JSONB for warranty details)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='offers' AND column_name='warranty_info') THEN
        ALTER TABLE offers ADD COLUMN warranty_info JSONB;
    END IF;
END $$;

-- Add subsidy_info column (JSONB for KfW/Länder subsidies)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='offers' AND column_name='subsidy_info') THEN
        ALTER TABLE offers ADD COLUMN subsidy_info JSONB;
    END IF;
END $$;

-- Add payment_terms column (TEXT for payment conditions)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='offers' AND column_name='payment_terms') THEN
        ALTER TABLE offers ADD COLUMN payment_terms TEXT;
    END IF;
END $$;

-- Add terms_reference column (VARCHAR for AGB reference)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='offers' AND column_name='terms_reference') THEN
        ALTER TABLE offers ADD COLUMN terms_reference VARCHAR(255);
    END IF;
END $$;

-- Add service_package column (JSONB for maintenance/service packages)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='offers' AND column_name='service_package') THEN
        ALTER TABLE offers ADD COLUMN service_package JSONB;
    END IF;
END $$;

-- ============================================================
-- DONE
-- ============================================================
-- Migration complete. The offers table now has all required professional fields.
