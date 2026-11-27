from app.agents.reasoning.claim_matcher import (
    assign_metric_keys,
    detect_code_conflicts,
    extract_figures,
    figure_window,
    lexical_similarity,
    same_metric,
)


def _values(text):
    return [(f["value_text"], f["number"], f["unit"], f["range"], f["bound"]) for f in extract_figures(text, 1)]


def test_extracts_units_ranges_and_bounds():
    got = _values("We cut settlement time from 4 hours to 35 minutes, an 87% reduction, and p99 stayed under 50 ms.")
    assert ("from 4 hours to 35 minutes", 2100.0, "s", True, None) in got
    assert ("87%", 87.0, "%", False, None) in got
    assert ("under 50 ms", 0.05, "s", False, "upper") in got
    assert not any(v[0].startswith("99") for v in got)  # "p99" is a name, not a figure


def test_skips_years_versions_and_bare_numbers():
    assert _values("In 2019 we moved 3 of them to Python 3.11 and step 2 was a rewrite.") == []


def test_counts_money_and_thousands_separators():
    got = _values("We handle 4 million daily transactions, 1 000 concurrent tasks and save $20k a month.")
    assert ("4 million daily transactions", 4_000_000.0, "transactions", False, None) in got
    assert any(v[1] == 1000.0 and v[2] == "tasks" for v in got)
    assert any(v[1] == 20_000.0 and v[2] == "usd" for v in got)


def test_and_joins_a_range_only_after_between():
    got = _values("Latency 87% and load 40% lower; between 3 and 5 nodes handled it.")
    assert [v[0] for v in got] == ["87%", "40%", "between 3 and 5 nodes"]


def test_window_is_the_figures_own_clause():
    s = "By enforcing a 0.5 s per-request SLA, the saga rolls back in under 300 ms, cutting errors to 0.01%."
    figs = extract_figures(s, 1)
    windows = {f["value_text"]: f["window"] for f in figs}
    assert windows["0.5 s"] == "By enforcing a 0.5 s per-request SLA"
    assert "rolls back" in windows["under 300 ms"] and "SLA" not in windows["under 300 ms"]
    assert figure_window("Cache hits: 98%", 12, 15).startswith("Cache hits")


def test_same_metric_needs_comparable_units_and_a_shared_word():
    a = extract_figures("Our cache hit rate was 98% after the change.", 1)[0]
    b = extract_figures("The cache hit rate reached 99.5% in production.", 2)[0]
    c = extract_figures("Infrastructure cost dropped 40%.", 3)[0]
    d = extract_figures("The job finished in 35 minutes.", 4)[0]
    assert same_metric(a, b, lexical_similarity, threshold=0.3)[0]
    assert not same_metric(a, c, lexical_similarity, threshold=0.3)[0]  # different metric
    assert not same_metric(a, d, lexical_similarity, threshold=0.0)[0]  # % vs seconds


def test_changed_figure_becomes_a_conflict_under_the_ledgers_rules():
    figures = (
        extract_figures("Our cache hit rate was 98% after the change.", 2)
        + extract_figures("The cache hit rate reached 93% in production.", 6)
        + extract_figures("The cache hit rate stayed at 98.4% overall.", 9)
    )
    keyed = assign_metric_keys(figures, lexical_similarity, threshold=0.3)
    assert len({f["metric_key"] for f in keyed}) == 1
    conflicts = detect_code_conflicts(keyed)
    pairs = [((c["first"]["question_number"]), c["second"]["question_number"]) for c in conflicts]
    assert pairs == [(2, 6), (6, 9)]  # 98 -> 93 and 93 -> 98.4 changed; each judged against the latest earlier figure
    assert all(c["kind"] == "changed_value" for c in conflicts)


def test_figures_in_one_answer_never_merge():
    figures = extract_figures("Hit rate was 98% at peak and the hit rate was 90% off-peak.", 1)
    keyed = assign_metric_keys(figures, lexical_similarity, threshold=0.0)
    assert len({f["metric_key"] for f in keyed}) == 2
    assert detect_code_conflicts(keyed) == []
