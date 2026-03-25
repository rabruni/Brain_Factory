from __future__ import annotations

from decimal import Decimal

from write_path.ports import GraphPort


def clamp_methylation(value: Decimal) -> Decimal:
    if value < Decimal("0.0"):
        return Decimal("0.0")
    if value > Decimal("1.0"):
        return Decimal("1.0")
    return value


def _node(graph: GraphPort, node_id: str) -> dict:
    nodes = getattr(graph, "nodes")
    return nodes.setdefault(node_id, {})


def fold_live_event(graph: GraphPort, event: dict) -> None:
    event_type = event["event_type"]
    payload = event["payload"]

    if event_type == "node_creation":
        node = _node(graph, payload["node_id"])
        node["node_type"] = payload["node_type"]
        node["methylation"] = clamp_methylation(Decimal(payload["initial_methylation"]))
        node["base_weight"] = Decimal(payload["base_weight"])
        node.setdefault("signals", {})
        node.setdefault("suppression_masks", set())
        return

    if event_type == "signal_delta":
        node = _node(graph, payload["node_id"])
        node.setdefault("signals", {})
        current = node.get("methylation", Decimal("0.0"))
        delta = Decimal(payload["delta"])
        signal_type = payload["signal_type"]
        node["signals"][signal_type] = node["signals"].get(signal_type, Decimal("0.0")) + delta
        node["methylation"] = clamp_methylation(current + delta)
        return

    if event_type == "methylation_delta":
        node = _node(graph, payload["node_id"])
        current = node.get("methylation", Decimal("0.0"))
        node["methylation"] = clamp_methylation(current + Decimal(payload["delta"]))
        return

    if event_type == "suppression":
        node = _node(graph, payload["node_id"])
        node.setdefault("suppression_masks", set()).add(payload["projection_scope"])
        return

    if event_type == "unsuppression":
        node = _node(graph, payload["node_id"])
        node.setdefault("suppression_masks", set()).discard(payload["projection_scope"])
        return

    if event_type == "mode_change":
        _node(graph, payload["node_id"])["mode"] = payload["mode"]
        return

    if event_type == "consolidation":
        consolidated = _node(graph, payload["consolidated_node_id"])
        consolidated["source_node_ids"] = list(payload["source_node_ids"])
        return

