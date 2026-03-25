from decimal import Decimal

from write_path.folds import clamp_methylation, fold_live_event


NODE_ID = "0195b4e0-4f2a-7000-8000-000000000042"


def test_signal_delta_clamps_at_upper_bound(graph_double) -> None:
    graph_double.nodes[NODE_ID] = {"methylation": Decimal("0.95"), "signals": {}}

    fold_live_event(
        graph_double,
        {
            "event_type": "signal_delta",
            "payload": {"node_id": NODE_ID, "signal_type": "entity", "delta": "0.10"},
        },
    )

    assert graph_double.nodes[NODE_ID]["methylation"] == Decimal("1.0")


def test_signal_delta_clamps_at_lower_bound(graph_double) -> None:
    graph_double.nodes[NODE_ID] = {"methylation": Decimal("0.05"), "signals": {}}

    fold_live_event(
        graph_double,
        {
            "event_type": "signal_delta",
            "payload": {"node_id": NODE_ID, "signal_type": "entity", "delta": "-0.10"},
        },
    )

    assert graph_double.nodes[NODE_ID]["methylation"] == Decimal("0.0")


def test_signal_delta_updates_signal_accumulator(graph_double) -> None:
    graph_double.nodes[NODE_ID] = {"methylation": Decimal("0.50"), "signals": {}}

    fold_live_event(
        graph_double,
        {
            "event_type": "signal_delta",
            "payload": {"node_id": NODE_ID, "signal_type": "entity", "delta": "0.10"},
        },
    )

    assert graph_double.nodes[NODE_ID]["signals"]["entity"] == Decimal("0.10")


def test_methylation_delta_updates_value_directly(graph_double) -> None:
    graph_double.nodes[NODE_ID] = {"methylation": Decimal("0.50"), "signals": {}}

    fold_live_event(
        graph_double,
        {"event_type": "methylation_delta", "payload": {"node_id": NODE_ID, "delta": "-0.20"}},
    )

    assert graph_double.nodes[NODE_ID]["methylation"] == Decimal("0.30")


def test_methylation_delta_clamps_at_upper_bound(graph_double) -> None:
    graph_double.nodes[NODE_ID] = {"methylation": Decimal("0.95"), "signals": {}}

    fold_live_event(
        graph_double,
        {"event_type": "methylation_delta", "payload": {"node_id": NODE_ID, "delta": "0.20"}},
    )

    assert graph_double.nodes[NODE_ID]["methylation"] == Decimal("1.0")


def test_suppression_adds_scope_to_mask(graph_double) -> None:
    graph_double.nodes[NODE_ID] = {"suppression_masks": set()}

    fold_live_event(
        graph_double,
        {"event_type": "suppression", "payload": {"node_id": NODE_ID, "projection_scope": "operator"}},
    )

    assert "operator" in graph_double.nodes[NODE_ID]["suppression_masks"]


def test_unsuppression_removes_scope_from_mask(graph_double) -> None:
    graph_double.nodes[NODE_ID] = {"suppression_masks": {"operator"}}

    fold_live_event(
        graph_double,
        {"event_type": "unsuppression", "payload": {"node_id": NODE_ID, "projection_scope": "operator"}},
    )

    assert "operator" not in graph_double.nodes[NODE_ID]["suppression_masks"]


def test_mode_change_sets_node_mode(graph_double) -> None:
    graph_double.nodes[NODE_ID] = {}

    fold_live_event(
        graph_double,
        {"event_type": "mode_change", "payload": {"node_id": NODE_ID, "mode": "deep-work"}},
    )

    assert graph_double.nodes[NODE_ID]["mode"] == "deep-work"


def test_consolidation_creates_traceable_consolidated_node(graph_double) -> None:
    graph_double.nodes["s1"] = {}
    graph_double.nodes["s2"] = {}

    fold_live_event(
        graph_double,
        {
            "event_type": "consolidation",
            "payload": {"source_node_ids": ["s1", "s2"], "consolidated_node_id": "c1"},
        },
    )

    assert graph_double.nodes["c1"]["source_node_ids"] == ["s1", "s2"]


def test_node_creation_creates_initial_node(graph_double) -> None:
    fold_live_event(
        graph_double,
        {
            "event_type": "node_creation",
            "payload": {
                "node_id": NODE_ID,
                "node_type": "memory",
                "initial_methylation": "0.25",
                "base_weight": "1.5",
            },
        },
    )

    assert graph_double.nodes[NODE_ID]["node_type"] == "memory"
    assert graph_double.nodes[NODE_ID]["methylation"] == Decimal("0.25")


def test_system_events_do_not_apply_policy_side_effects(graph_double) -> None:
    graph_double.nodes[NODE_ID] = {"methylation": Decimal("0.5"), "signals": {}}

    fold_live_event(
        graph_double,
        {"event_type": "session_start", "payload": {"session_id": "s1", "actor_id": "u1", "session_type": "operator"}},
    )

    assert graph_double.nodes[NODE_ID]["methylation"] == Decimal("0.5")


def test_clamp_methylation_returns_midpoint_unchanged() -> None:
    assert clamp_methylation(Decimal("0.55")) == Decimal("0.55")


def test_clamp_methylation_clamps_below_zero() -> None:
    assert clamp_methylation(Decimal("-0.01")) == Decimal("0.0")


def test_clamp_methylation_clamps_above_one() -> None:
    assert clamp_methylation(Decimal("1.01")) == Decimal("1.0")
