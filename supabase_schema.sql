-- FounderReach AI: Supabase Database Schema
-- Run this in your Supabase Project Dashboard -> SQL Editor (https://xsumvcqeqknshjwdnypy.supabase.co)

-- 1. Opportunities Table
CREATE TABLE IF NOT EXISTS public.opportunities (
    id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    platform TEXT NOT NULL,
    original_url TEXT NOT NULL UNIQUE,
    discussion_date TEXT,
    author TEXT,
    classification TEXT NOT NULL DEFAULT 'RESEARCH_INSIGHT',
    source_status TEXT NOT NULL DEFAULT 'SOURCE_UNVERIFIED',
    intent_status TEXT NOT NULL DEFAULT 'CUSTOMER_INTENT_UNVERIFIED',
    direct_problem_evidence TEXT,
    rejection_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    customer_problem TEXT NOT NULL,
    why_relevant TEXT NOT NULL,
    evidence_excerpt TEXT NOT NULL,
    total_score NUMERIC(5, 2) NOT NULL,
    score_json JSONB NOT NULL,
    suggested_response TEXT NOT NULL,
    verification_json JSONB NOT NULL,
    feedback TEXT,
    feedback_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.opportunities ADD COLUMN IF NOT EXISTS classification TEXT NOT NULL DEFAULT 'RESEARCH_INSIGHT';
ALTER TABLE public.opportunities ADD COLUMN IF NOT EXISTS source_status TEXT NOT NULL DEFAULT 'SOURCE_UNVERIFIED';
ALTER TABLE public.opportunities ADD COLUMN IF NOT EXISTS intent_status TEXT NOT NULL DEFAULT 'CUSTOMER_INTENT_UNVERIFIED';
ALTER TABLE public.opportunities ADD COLUMN IF NOT EXISTS direct_problem_evidence TEXT;
ALTER TABLE public.opportunities ADD COLUMN IF NOT EXISTS rejection_reasons JSONB NOT NULL DEFAULT '[]'::jsonb;

-- Index for fast score sorting and product filtering
CREATE INDEX IF NOT EXISTS idx_opportunities_product_score ON public.opportunities (product_name, total_score DESC);

-- 2. Cost Ledger Table
CREATE TABLE IF NOT EXISTS public.cost_ledger (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    service TEXT NOT NULL,
    model TEXT,
    operation TEXT NOT NULL,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cost_usd NUMERIC(10, 6) DEFAULT 0.0,
    cost_inr NUMERIC(10, 2) DEFAULT 0.0,
    cached BOOLEAN DEFAULT FALSE,
    notes TEXT
);

-- 3. Cache Table (Guarantees zero repeat cost and rapid lookup)
CREATE TABLE IF NOT EXISTS public.cache (
    cache_key TEXT PRIMARY KEY,
    cache_value TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Content Hashes Table for Deduplication
CREATE TABLE IF NOT EXISTS public.content_hashes (
    content_hash TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    original_url TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Deny client roles. Only a server-held service role may bypass RLS.
ALTER TABLE public.opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cost_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_hashes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public all access on opportunities" ON public.opportunities;
DROP POLICY IF EXISTS "Allow public all access on cost_ledger" ON public.cost_ledger;
DROP POLICY IF EXISTS "Allow public all access on cache" ON public.cache;
DROP POLICY IF EXISTS "Allow public all access on content_hashes" ON public.content_hashes;
REVOKE ALL ON public.opportunities, public.cost_ledger, public.cache, public.content_hashes FROM anon, authenticated;
