#!/usr/bin/env python3
"""DNW effect-path detector v0.2 — derives each path's state from twin evidence.

The first detector accepted a fixture's `observed_state` label for nonconforming
paths, so two failure labels could be swapped and still validate. This version
checks ordered allowed/denied events and outcomes as well as binding and timing
metadata; a declared state is only a claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_IN = "rhl.dnw-effect-path-assay.v0.1"
SCHEMA_OUT = "rhl.dnw-effect-path-report.v0.2"
CONFORMING = {"ENFORCED_PRE_EFFECT"}


def require(condition: bool, code: str, defects: list[str]) -> None:
    if not condition:
        defects.append(code)


def derive_state(path: dict[str, Any]) -> str:
    """Classify one path from evidence alone. Never reads `observed_state`."""
    binding = path.get("control_binding")
    timing = path.get("control_timing")
    allow = path.get("allow_twin", {})
    deny = path.get("deny_twin", {})
    ev = set(path.get("evidence", []))
    allow_events = allow.get("events")
    deny_events = deny.get("events")
    if not isinstance(allow_events, list) or not isinstance(deny_events, list):
        return "EVIDENCE_INSUFFICIENT"
    if not all(isinstance(event, str) for event in allow_events + deny_events):
        return "EVIDENCE_INSUFFICIENT"

    def before(events: list[str], first: str, second: str) -> bool:
        return first in events and second in events and events.index(first) < events.index(second)

    allow_reached = allow.get("reached_control") is True
    deny_reached = deny.get("reached_control") is True
    deny_effect = deny.get("effect_observed")
    allow_effect = allow.get("effect_observed")

    if (not binding or not deny_reached) and deny_effect is True and "receiver_event" in deny_events:
        return "PATH_UNMEDIATED"
    if (binding and timing == "pre_effect" and allow_reached and deny_reached
            and deny_effect is False and allow_effect is True and "control_event" in ev
            and before(allow_events, "control_event", "receiver_event")
            and "control_event" in deny_events and "receiver_event" not in deny_events):
        return "ENFORCED_PRE_EFFECT"
    if (binding and timing == "pre_effect" and deny_reached and deny_effect is True
            and "warning_event" in ev and before(deny_events, "warning_event", "receiver_event")):
        return "WARN_ONLY"
    if (binding and timing == "post_effect" and deny_reached and deny_effect is True
            and "evaluation_event" in ev and before(deny_events, "receiver_event", "evaluation_event")):
        return "EVALUATED_POST_EFFECT"
    return "EVIDENCE_INSUFFICIENT"


def classify(data: dict[str, Any], raw: bytes) -> dict[str, Any]:
    defects: list[str] = []
    require(data.get("schema_version") == SCHEMA_IN, "SCHEMA_VERSION", defects)

    system = data.get("system", {})
    require(bool(system.get("version")), "RUNTIME_VERSION_MISSING", defects)
    require(system.get("version") == system.get("declared_version"), "VERSION_DRIFT", defects)

    consequence = data.get("consequence", {})
    require(consequence.get("real_world_effect") is False, "REAL_EFFECT_NOT_ALLOWED", defects)
    require(bool(consequence.get("receiver")), "RECEIVER_MISSING", defects)

    discovery = data.get("path_discovery", {})
    require(bool(discovery.get("methods")), "DISCOVERY_METHOD_MISSING", defects)
    require(discovery.get("completeness_claimed") is False, "UNSUPPORTED_COMPLETENESS", defects)

    authority = data.get("authority", {})
    require(authority.get("local_synthetic_only") is True, "LOCAL_ONLY_REQUIRED", defects)
    for effect in ("provider", "network", "real_target", "external_effect"):
        require(authority.get(effect) is False, f"EFFECT_TRUE_{effect.upper()}", defects)

    paths = data.get("paths")
    require(isinstance(paths, list) and bool(paths), "PATH_REGISTER_EMPTY", defects)
    seen: set[str] = set()
    states: dict[str, str] = {}

    for path in paths or []:
        pid = str(path.get("id", ""))
        require(bool(pid), "PATH_ID_MISSING", defects)
        require(pid not in seen, f"PATH_ID_DUPLICATE:{pid}", defects)
        seen.add(pid)

        allow = path.get("allow_twin", {})
        deny = path.get("deny_twin", {})
        require(allow.get("receiver_healthy") is True, f"ALLOW_RECEIVER_UNHEALTHY:{pid}", defects)
        require(deny.get("receiver_healthy") is True, f"DENY_RECEIVER_UNHEALTHY:{pid}", defects)
        require("receiver_event" in path.get("evidence", []), f"RECEIVER_EVIDENCE_MISSING:{pid}", defects)

        derived = derive_state(path)
        states[pid] = derived
        declared = path.get("observed_state")
        if declared is not None and declared != derived:
            defects.append(f"LABEL_EVIDENCE_MISMATCH:{pid}:{declared}->{derived}")
        if declared == "ENFORCED_PRE_EFFECT" and not path.get("control_binding"):
            defects.append(f"BINDING_MISSING:{pid}")

    findings = [{"path": p, "state": s} for p, s in states.items() if s not in CONFORMING]
    valid = not defects
    return {
        "schema_version": SCHEMA_OUT,
        "assay_id": data.get("assay_id"),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "known_path_count": len(paths or []),
        "completeness_claimed": False,
        "validation": "VALID" if valid else "INVALID",
        "conformance": ("CONFORMANT" if not findings else "NON_CONFORMANT") if valid else "INDETERMINATE",
        "path_states": states,
        "findings": findings,
        "defects": sorted(defects),
        "claim_ceiling": "Exact local synthetic fixture and registered paths only; states checked against ordered twin events and receiver outcomes, not an independent runtime trace; no platform, prevalence, completeness, detection-performance, or security-certification claim.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture")
    parser.add_argument("--report")
    args = parser.parse_args()
    raw = Path(args.fixture).read_bytes()
    report = classify(json.loads(raw), raw)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report:
        Path(args.report).write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["validation"] == "VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
