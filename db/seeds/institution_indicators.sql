-- India Dashboard — public-institution counts (idempotent catalog). Verified national statistics
-- transcribed from official ministry/agency reports (trust tier 1). These extend the same
-- macro_indicator_def catalog as the World Bank series; their VALUES are written by
-- `neta institution-stats` (curated figures + the data.gov.in OGD subset), not the World Bank pipeline.
-- Codes use a readable IN.<domain>.<metric> scheme (the code PK is free-text, not a World Bank id).
-- format 'count_in' renders Indian units (…, "14.72 lakh", "4.5 crore"); polarity drives the change chip.
-- note names the exact source report + vintage — every figure is one click from its official release.
--
-- These are filed under the SAME thematic categories as the matching World Bank series (so the rail has
-- one "Health"/"Education"/"Infrastructure & Access" tab, not two): each institutional metric sits after
-- its category's World Bank outcomes (higher ind_order). Justice & Safety has no World Bank counterpart,
-- so it is a standalone category (order 10, after Environment).

INSERT INTO macro_indicator_def (code, name, unit, format, category, category_order, ind_order, polarity, note) VALUES
    -- Education (UDISE+ 2023-24 for schools; AISHE 2023-24 for higher education) — after WB education (ind 1-3)
    ('IN.EDU.SCHOOLS',       'Schools (all managements)',              'schools',      'count_in', 'Education',                6,  4, 0, 'UDISE+ 2023-24; pre-primary to higher secondary'),
    ('IN.EDU.TEACHERS',      'School teachers',                        'teachers',     'count_in', 'Education',                6,  5, 1, 'UDISE+ 2023-24'),
    ('IN.EDU.STUDENTS',      'School students (enrolment)',            'students',     'count_in', 'Education',                6,  6, 0, 'UDISE+ 2023-24; pre-primary to higher secondary'),
    ('IN.EDU.UNIVERSITIES',  'Universities',                           'universities', 'count_in', 'Education',                6,  7, 1, 'AISHE 2023-24'),
    ('IN.EDU.COLLEGES',      'Colleges',                               'colleges',     'count_in', 'Education',                6,  8, 1, 'AISHE 2023-24'),
    ('IN.EDU.STANDALONE',    'Standalone institutions',                'institutions', 'count_in', 'Education',                6,  9, 0, 'AISHE 2023-24'),
    ('IN.EDU.HE.ENROLMENT',  'Higher-education enrolment',             'students',     'count_in', 'Education',                6, 10, 1, 'AISHE 2023-24'),
    ('IN.EDU.HE.FACULTY',    'Higher-education faculty',               'teachers',     'count_in', 'Education',                6, 11, 1, 'AISHE 2023-24'),
    -- Health (Health Dynamics of India 2022-23, MoHFW — facility counts) — after WB health outcomes (ind 1-4)
    ('IN.HLTH.SUBCENTRES',   'Sub-centres',                            'facilities',   'count_in', 'Health',                   5,  5, 1, 'Health Dynamics of India 2022-23'),
    ('IN.HLTH.PHC',          'Primary Health Centres (PHCs)',          'facilities',   'count_in', 'Health',                   5,  6, 1, 'Health Dynamics of India 2022-23'),
    ('IN.HLTH.CHC',          'Community Health Centres (CHCs)',        'facilities',   'count_in', 'Health',                   5,  7, 1, 'Health Dynamics of India 2022-23'),
    ('IN.HLTH.SDH',          'Sub-divisional hospitals',               'facilities',   'count_in', 'Health',                   5,  8, 1, 'Health Dynamics of India 2022-23'),
    ('IN.HLTH.DISTRICT.HOSP','District hospitals',                     'facilities',   'count_in', 'Health',                   5,  9, 1, 'Health Dynamics of India 2022-23'),
    -- Infrastructure & Access (India Post, RBI, Indian Railways — physical network) — after WB access (ind 1-2)
    ('IN.CONN.POSTOFFICES',  'Post offices',                           'offices',      'count_in', 'Infrastructure & Access',  7,  3, 1, 'India Post; ~90% rural — world''s largest postal network'),
    ('IN.CONN.BANK.BRANCHES','Scheduled commercial bank branches',     'branches',     'count_in', 'Infrastructure & Access',  7,  4, 1, 'RBI; functioning offices, Sep 2024'),
    ('IN.CONN.RAIL.STATIONS','Railway stations',                       'stations',     'count_in', 'Infrastructure & Access',  7,  5, 0, 'Indian Railways, 2023-24'),
    -- Justice & Safety (BPR&D Data on Police Organisations; NCRB Prison Statistics India 2022) — standalone
    ('IN.JUS.POLICE.SANCTIONED', 'Police sanctioned strength (state)', 'personnel',    'count_in', 'Justice & Safety',        10, 1, 0, 'BPR&D DoPO, as on 1 Jan 2024; state police'),
    ('IN.JUS.POLICE.ACTUAL', 'Police actual strength (state)',         'personnel',    'count_in', 'Justice & Safety',        10, 2, 1, 'BPR&D DoPO, as on 1 Jan 2024; ~21% vacancy vs sanctioned'),
    ('IN.JUS.PRISON.POP',    'Prison population',                      'prisoners',    'count_in', 'Justice & Safety',        10, 3, 0, 'NCRB Prison Statistics India 2022; 75.8% undertrials'),
    ('IN.JUS.PRISON.CAPACITY','Prison capacity',                       'prisoners',    'count_in', 'Justice & Safety',        10, 4, 1, 'NCRB Prison Statistics India 2022'),
    ('IN.JUS.PRISON.OCCUPANCY','Prison occupancy rate',                '% of capacity','pct',      'Justice & Safety',        10, 5, -1, 'NCRB Prison Statistics India 2022')
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name, unit = EXCLUDED.unit, format = EXCLUDED.format,
    category = EXCLUDED.category, category_order = EXCLUDED.category_order, ind_order = EXCLUDED.ind_order,
    polarity = EXCLUDED.polarity, note = EXCLUDED.note;
