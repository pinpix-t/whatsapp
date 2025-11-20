-- Migration: Add email column to analytics table
-- Run this if the analytics table already exists

-- Add email column if it doesn't exist
ALTER TABLE analytics 
ADD COLUMN IF NOT EXISTS email VARCHAR(255);

-- Add index for email queries
CREATE INDEX IF NOT EXISTS idx_analytics_email ON analytics(email);

