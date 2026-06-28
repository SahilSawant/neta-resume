-- Lok Sabha members represent a constituency, but the constituency's STATE was parsed from MyNeta and
-- discarded. Store it so we can answer "an MP for state X" (homepage location personalization) and offer
-- a state filter. RS members already carry rs_state_code; this is the LS analogue.
ALTER TABLE office_term ADD COLUMN IF NOT EXISTS ls_state_code text;

-- Lookups by state (the homepage fallback + directory state filter).
CREATE INDEX IF NOT EXISTS office_term_ls_state_idx ON office_term (ls_state_code);
