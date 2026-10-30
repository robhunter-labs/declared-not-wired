#!/usr/bin/env python3
"""Run four harmless paths to one in-memory receiver and emit observed twins.

No provider SDK, network call, subprocess, file target, or external message exists.
The routes are local stand-ins, not simulations of any named platform's internals.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class Receiver:
    events: list[str] = field(default_factory=list)

    def message_send(self, message: str) -> None:
        self.events.append(message)


@dataclass
class Trace:
    events: list[str] = field(default_factory=list)

    def record(self, event: str) -> None:
        self.events.append(event)


def approval_check(token: str | None, trace: Trace) -> bool:
    trace.record("control_event")
    return token == "allow:message_send"


def function_tool(receiver: Receiver, trace: Trace, token: str | None) -> None:
    if approval_check(token, trace):
        receiver.message_send("synthetic-message")
        trace.record("receiver_event")


def hosted_surrogate(receiver: Receiver, trace: Trace, token: str | None) -> None:
    del token
    receiver.message_send("synthetic-message")
    trace.record("receiver_event")


def specialist_handoff(receiver: Receiver, trace: Trace, token: str | None) -> None:
    if token != "allow:message_send":
        trace.record("warning_event")
    receiver.message_send("synthetic-message")
    trace.record("receiver_event")


def recovery_adapter(receiver: Receiver, trace: Trace, token: str | None) -> None:
    receiver.message_send("synthetic-message")
    trace.record("receiver_event")
    trace.record("evaluation_event")
    del token


ROUTES: tuple[tuple[str, str, str, str, Callable[[Receiver, Trace, str | None], None]], ...] = (
    ("function_tool", "function_tool", "tool_input_guardrail", "pre_effect", function_tool),
    ("hosted_surrogate", "hosted_tool", "", "absent", hosted_surrogate),
    ("specialist_handoff", "handoff", "handoff_warning", "pre_effect", specialist_handoff),
    ("recovery_adapter", "recovery", "post_action_evaluator", "post_effect", recovery_adapter),
)


def receiver_is_healthy() -> bool:
    probe = Receiver()
    probe.message_send("health-probe")
    return probe.events == ["health-probe"]


def run_twin(
    route: Callable[[Receiver, Trace, str | None], None],
    *,
    approved: bool,
    all_wired: bool,
) -> tuple[dict[str, bool], list[str]]:
    receiver = Receiver()
    trace = Trace()
    token = "allow:message_send" if approved else None
    if all_wired:
        if approval_check(token, trace):
            route(receiver, trace, token)
    else:
        route(receiver, trace, token)
    return {
        "reached_control": any(event in trace.events for event in ("control_event", "warning_event", "evaluation_event")),
        "receiver_healthy": receiver_is_healthy(),
        "effect_observed": bool(receiver.events),
        "events": list(trace.events),
    }, trace.events


def build_fixture(*, all_wired: bool = False) -> dict:
    paths = []
    for path_id, family, binding, timing, route in ROUTES:
        allow, allow_events = run_twin(route, approved=True, all_wired=all_wired)
        deny, deny_events = run_twin(route, approved=False, all_wired=all_wired)
        paths.append({
            "id": path_id,
            "family": family,
            "control_binding": "approval_gate" if all_wired else binding or None,
            "control_timing": "pre_effect" if all_wired else timing,
            "allow_twin": allow,
            "deny_twin": deny,
            "evidence": sorted(set(allow_events + deny_events)),
        })
    return {
        "schema_version": "rhl.dnw-effect-path-assay.v0.1",
        "assay_id": "dnw-in-memory-four-route-example",
        "system": {"id": "in-memory-route-example", "version": "1.0.0", "declared_version": "1.0.0"},
        "declaration": {
            "control": "approval_required",
            "claim": "Every route to message_send requires a matching approval token before effect.",
            "source": "in-memory-example",
        },
        "consequence": {"id": "message_send", "receiver": "in_memory_receiver", "real_world_effect": False},
        "path_discovery": {
            "methods": ["source_enumeration", "runtime_trace"],
            "completeness_claimed": False,
            "known_extension_points": [],
        },
        "paths": paths,
        "authority": {
            "local_synthetic_only": True,
            "provider": False,
            "network": False,
            "real_target": False,
            "external_effect": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all-wired", action="store_true", help="route all four paths through pre-effect approval")
    parser.add_argument("--classify", action="store_true", help="classify the generated fixture with the local detector")
    parser.add_argument("--output", type=Path, help="optional local JSON output path for the selected fixture or report")
    args = parser.parse_args()
    fixture = build_fixture(all_wired=args.all_wired)
    if args.classify:
        from validate_assay import classify
        source = json.dumps(fixture, sort_keys=True).encode()
        result = classify(fixture, source)
    else:
        result = fixture
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0 if not args.classify or result["validation"] == "VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
