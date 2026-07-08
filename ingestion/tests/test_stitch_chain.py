"""Chain-aware merge: union-find + clique verification in _resolve_components (pure, no DB).

Also covers `_hard_negative` — the recall-safe geography band that pre-filters cross-state namesakes
before scoring (twin of the SQL band in `_candidate_pairs`).
"""

from neta_core.transform.names import normalize_name

from neta_ingest.pipelines.identity.stitch_identities import _hard_negative, _resolve_components


def _p(state=None, birth=None, rel=None):
    return {"home_state": state, "birth_year": birth, "relative_name": rel}


class TestHardNegative:
    def test_same_state_kept(self):
        assert _hard_negative(_p("BIHAR"), _p("BIHAR")) is False

    def test_cross_state_no_corroboration_dropped(self):
        # Two "Ram Kumar"s in different states with nothing tying them -> a hard negative.
        assert _hard_negative(_p("ANDHRA PRADESH"), _p("TAMIL NADU")) is True

    def test_null_state_is_kept(self):
        # Signal-poor record (municipal / old backfill): unknown state must never be dropped here.
        assert _hard_negative(_p(None, birth=1970), _p("TAMIL NADU", birth=1985)) is False
        assert _hard_negative(_p("", ), _p("TAMIL NADU")) is False

    def test_cross_state_same_birth_year_recovered(self):
        # MLA in one state -> RS from another: same person, same birth year -> keep for scoring.
        assert _hard_negative(_p("KARNATAKA", birth=1962), _p("MAHARASHTRA", birth=1962)) is False

    def test_cross_state_matching_relative_recovered(self):
        assert _hard_negative(
            _p("KARNATAKA", rel="Basavaraj Hitnal"), _p("MAHARASHTRA", rel="Basavaraj Hitnal")
        ) is False

    def test_cross_state_conflicting_signals_dropped(self):
        # Different states, different birth years, different fathers -> confidently different people.
        assert _hard_negative(
            _p("KARNATAKA", birth=1962, rel="Shyam Singh"),
            _p("MAHARASHTRA", birth=1985, rel="Mohan Yadav"),
        ) is True

    def test_state_comparison_case_insensitive(self):
        assert _hard_negative(_p("Bihar"), _p("bihar")) is False


def person(name, birth, state, rel, latest, gender=None, parties=(1,)):
    return {
        "display_name": name, "normalized_name": normalize_name(name), "birth_year": birth,
        "home_state": state, "relative_name": rel, "gender": gender, "native_name": None,
        "party_ids": parties, "latest_term": latest,
    }


def test_three_record_clique_merges_to_one_survivor():
    # councillor -> MLA -> MP: three records that pairwise all auto-merge -> one component, one survivor.
    sig = {
        1: person("RAM PRASAD SINGH", 1970, "BIHAR", "Shyam Singh", "2024-06-01"),
        2: person("RAM PRASAD SINGH", 1970, "BIHAR", "Shyam Singh", "2019-05-01"),
        3: person("RAM PRASAD SINGH", 1970, "BIHAR", "Shyam Singh", "2014-05-01"),
    }
    scored = [(1, 2, 0.93, {}), (1, 3, 0.93, {}), (2, 3, 0.93, {})]
    remap, automerges, reviews = _resolve_components(scored, sig)
    assert remap == {2: 1, 3: 1}          # survivor = most-recent term (2024) = id 1
    assert reviews == []
    assert len(automerges) == 3           # every fused edge recorded for the audit


def test_inconsistent_triad_routes_to_review():
    # 1~2 and 1~3 auto-merge (id 1 has no gender to conflict), but 2~3 is a gender veto -> not a clique.
    sig = {
        1: person("RAM PRASAD SINGH", 1970, "BIHAR", "Shyam Singh", "2024", gender=None),
        2: person("RAM PRASAD SINGH", 1970, "BIHAR", "Shyam Singh", "2019", gender="M"),
        3: person("RAM PRASAD SINGH", 1970, "BIHAR", "Shyam Singh", "2014", gender="F"),
    }
    scored = [(1, 2, 0.93, {}), (1, 3, 0.93, {})]
    remap, automerges, reviews = _resolve_components(scored, sig)
    assert remap == {}                    # nothing merged
    assert automerges == []
    assert len(reviews) == 2              # the whole component -> review


def test_two_disjoint_pairs_merge_independently():
    sig = {
        1: person("RAM SINGH", 1970, "BIHAR", "A", "2024"),
        2: person("RAM SINGH", 1970, "BIHAR", "A", "2019"),
        3: person("GEETA PATEL", 1980, "GUJARAT", "B", "2024"),
        4: person("GEETA PATEL", 1980, "GUJARAT", "B", "2019"),
    }
    scored = [(1, 2, 0.93, {}), (3, 4, 0.93, {})]
    remap, automerges, reviews = _resolve_components(scored, sig)
    assert remap == {2: 1, 4: 3}          # two survivors
    assert reviews == []
