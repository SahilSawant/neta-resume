-- 0028: Lok Sabha constituency registry + nearest-neighbour adjacency, for the Constituency Report Card.
-- Promotes the 543-PC reference (bundled ECI/DataMeet boundaries in web/src/data/pc-boundaries.json) into the
-- DB so the read layer can join each constituency to its sitting MP's facts and compare it against state /
-- national averages and nearby constituencies. This is REFERENCE geography (not a sourced claim about a
-- person), so it carries no per-row source_ref — same as the house / state registries.
--
-- pc_name_normalized is the upper/space-folded name (non-alphanumerics -> single space) so the mixed-case,
-- hyphenated office_term.constituency strings ("Kangra", "NAINITAL-UDHAMSINGH NAGAR") match a canonical row.
-- state_name is stored UPPER to line up with office_term.ls_state_code (e.g. 'TAMIL NADU').

CREATE TABLE constituency (
    id                 bigserial PRIMARY KEY,
    pc_id              integer NOT NULL UNIQUE,      -- stable id from the boundary set
    pc_no              integer,                      -- number within the state
    state_name         text NOT NULL,               -- UPPER full state name, matches office_term.ls_state_code
    pc_name            text NOT NULL,               -- display name, e.g. 'Kangra'
    pc_name_normalized text NOT NULL,               -- upper + non-alnum folded, for matching office_term
    pc_name_hi         text,                         -- Devanagari name
    pc_category        text,                         -- GEN | SC | ST
    wikidata_qid       text,
    center_lat         double precision,             -- rough centroid (mean of boundary vertices)
    center_lng         double precision
    -- NOTE: (state_name, pc_name_normalized) is NOT unique — a boundary set can carry a near-duplicate
    -- (e.g. two "Mumbai South" rows). pc_id is the identity; the pair below is a match index, not a key.
);

CREATE INDEX constituency_state_idx ON constituency (state_name);
CREATE INDEX constituency_norm_idx  ON constituency (state_name, pc_name_normalized);

-- Text normalisers used to join constituency ↔ office_term at read time (names/states are inconsistent
-- across cycles/sources). nr_norm: upper + non-alnum folded to single spaces (matches pc_name_normalized).
-- nr_canon_state: same, after collapsing the common state-name spelling variants (ORISSA→ODISHA, "&"→"AND",
-- dropping "ISLANDS" / "NATIONAL CAPITAL TERRITORY OF", PONDICHERRY→PUDUCHERRY) so e.g. geojson "DELHI" and
-- office_term "NATIONAL CAPITAL TERRITORY OF DELHI" align.
CREATE OR REPLACE FUNCTION nr_norm(x text) RETURNS text AS $$
  SELECT trim(regexp_replace(upper(coalesce(x, '')), '[^A-Z0-9]+', ' ', 'g'));
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION nr_canon_state(x text) RETURNS text AS $$
  SELECT nr_norm(
    replace(replace(replace(replace(
      replace(upper(coalesce(x, '')), '&', ' AND '),
      'NATIONAL CAPITAL TERRITORY OF ', ''),
      ' ISLANDS', ''),
      'ORISSA', 'ODISHA'),
      'PONDICHERRY', 'PUDUCHERRY'));
$$ LANGUAGE sql IMMUTABLE;

-- Nearest-neighbour edges (by centroid distance, same-state preferred) powering the "nearby constituencies"
-- comparison. Directed rows (rank 1 = nearest); rebuilt idempotently by `neta constituencies`.
CREATE TABLE constituency_adjacency (
    constituency_id bigint   NOT NULL REFERENCES constituency(id) ON DELETE CASCADE,
    neighbor_id     bigint   NOT NULL REFERENCES constituency(id) ON DELETE CASCADE,
    rank            smallint NOT NULL,               -- 1 = nearest
    PRIMARY KEY (constituency_id, neighbor_id)
);
