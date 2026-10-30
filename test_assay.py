#!/usr/bin/env python3
"""DNW detector suite: one exact base case, one label-free case, one conformant twin, and
hostile cases (including malformed input).

Every expectation is exact: the full path->state map, the full defect list. No set-membership
or prefix matching (the v0.1 looseness), so a wrong-but-plausible result cannot pass.

Run either way:  python3 test_assay.py   or   python3 -m unittest -v
Checks raise AssertionError explicitly, so they still check under `python -O`.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

from validate_assay import classify

ROOT = Path(__file__).parent
BASE_RAW = (ROOT / "fixture.json").read_bytes()
BASE = json.loads(BASE_RAW)
CASES: list[tuple[str, object, dict]] = []


def ensure(condition: bool, detail) -> None:
    if not condition:
        raise AssertionError(detail)


def run_case(name: str, data, validation: str, conformance: str,
             states: dict | None = None, defects: list | None = None) -> None:
    raw = json.dumps(data, sort_keys=True).encode()
    r = classify(data, raw)
    ensure(r["source_sha256"] == hashlib.sha256(raw).hexdigest(), (name, r))
    ensure(r["validation"] == validation, (name, r))
    ensure(r["conformance"] == conformance, (name, r))
    if states is not None:
        ensure(r["path_states"] == states, (name, r["path_states"]))
    if defects is not None:
        ensure(r["defects"] == sorted(defects), (name, r["defects"]))


def check(name: str, data, **expect) -> None:
    """Register a case; it runs under unittest (AssayCases) or `python3 test_assay.py`."""
    CASES.append((name, data, expect))


def mutate(fn) -> dict:
    d = copy.deepcopy(BASE)
    fn(d)
    return d


EXPECTED = {
    "function_tool": "ENFORCED_PRE_EFFECT",
    "hosted_surrogate": "PATH_UNMEDIATED",
    "specialist_handoff": "WARN_ONLY",
    "recovery_adapter": "EVALUATED_POST_EFFECT",
}

# Base: exact per-path mapping, derived from evidence.
check("base-exact-path-states", copy.deepcopy(BASE), validation="VALID",
      conformance="NON_CONFORMANT", states=EXPECTED, defects=[])

# Labels removed entirely: the same states must still be derived (proves no label dependence).
def strip_labels(d):
    for p in d["paths"]:
        p.pop("observed_state", None)
check("labels-removed-same-derivation", mutate(strip_labels), validation="VALID",
      conformance="NON_CONFORMANT", states=EXPECTED, defects=[])

# Conformant twin: every path genuinely wired before effect -> the detector can say CONFORMANT.
def all_wired(d):
    for p in d["paths"]:
        p.update(control_binding="tool_input_guardrail", control_timing="pre_effect",
                 observed_state="ENFORCED_PRE_EFFECT", evidence=["control_event", "receiver_event"])
        p["allow_twin"] = {"reached_control": True, "receiver_healthy": True,
                           "effect_observed": True, "events": ["control_event", "receiver_event"]}
        p["deny_twin"] = {"reached_control": True, "receiver_healthy": True,
                          "effect_observed": False, "events": ["control_event"]}
check("conformant-twin-all-wired", mutate(all_wired), validation="VALID", conformance="CONFORMANT",
      states={k: "ENFORCED_PRE_EFFECT" for k in EXPECTED}, defects=[])

# A successful effect does not prove the allowed run crossed its declared control.
def allow_bypasses_control(d):
    all_wired(d)
    d["paths"][0]["allow_twin"]["reached_control"] = False
check("hostile-allowed-effect-bypasses-control", mutate(allow_bypasses_control),
      validation="INVALID", conformance="INDETERMINATE",
      defects=["LABEL_EVIDENCE_MISMATCH:function_tool:ENFORCED_PRE_EFFECT->EVIDENCE_INSUFFICIENT"])

def control_after_effect(d):
    all_wired(d)
    d["paths"][0]["allow_twin"]["events"] = ["receiver_event", "control_event"]
check("hostile-control-after-effect", mutate(control_after_effect),
      validation="INVALID", conformance="INDETERMINATE",
      defects=["LABEL_EVIDENCE_MISMATCH:function_tool:ENFORCED_PRE_EFFECT->EVIDENCE_INSUFFICIENT"])

def missing_ordered_trace(d):
    all_wired(d)
    del d["paths"][0]["allow_twin"]["events"]
check("hostile-missing-ordered-trace", mutate(missing_ordered_trace),
      validation="INVALID", conformance="INDETERMINATE",
      defects=["LABEL_EVIDENCE_MISMATCH:function_tool:ENFORCED_PRE_EFFECT->EVIDENCE_INSUFFICIENT"])

# Hostile 1: swapped failure labels (the v0.1 blind spot).
def swap(d):
    a, b = d["paths"][2], d["paths"][3]
    a["observed_state"], b["observed_state"] = b["observed_state"], a["observed_state"]
check("hostile-swapped-failure-labels", mutate(swap), validation="INVALID", conformance="INDETERMINATE",
      defects=["LABEL_EVIDENCE_MISMATCH:specialist_handoff:EVALUATED_POST_EFFECT->WARN_ONLY",
               "LABEL_EVIDENCE_MISMATCH:recovery_adapter:WARN_ONLY->EVALUATED_POST_EFFECT"])

# Hostile 2: stale version.
check("hostile-stale-version", mutate(lambda d: d["system"].__setitem__("version", "1.0.1")),
      validation="INVALID", conformance="INDETERMINATE", defects=["VERSION_DRIFT"])

# Hostile 3: control binding removed from the enforced path.
check("hostile-missing-control-binding",
      mutate(lambda d: d["paths"][0].__setitem__("control_binding", None)),
      validation="INVALID", conformance="INDETERMINATE",
      defects=["BINDING_MISSING:function_tool",
               "LABEL_EVIDENCE_MISMATCH:function_tool:ENFORCED_PRE_EFFECT->EVIDENCE_INSUFFICIENT"])

# Hostile 4: receiver evidence omitted.
check("hostile-receiver-evidence-omitted",
      mutate(lambda d: d["paths"][0].__setitem__("evidence", ["control_event"])),
      validation="INVALID", conformance="INDETERMINATE",
      defects=["RECEIVER_EVIDENCE_MISSING:function_tool"])

# Hostile 5: broken sink masquerading as enforcement.
check("hostile-broken-sink",
      mutate(lambda d: d["paths"][0]["allow_twin"].__setitem__("receiver_healthy", False)),
      validation="INVALID", conformance="INDETERMINATE",
      defects=["ALLOW_RECEIVER_UNHEALTHY:function_tool"])

# Hostile 6: the denied case still produced the effect on the 'enforced' path.
check("hostile-deny-effect-crossed",
      mutate(lambda d: d["paths"][0]["deny_twin"].__setitem__("effect_observed", True)),
      validation="INVALID", conformance="INDETERMINATE",
      defects=["LABEL_EVIDENCE_MISMATCH:function_tool:ENFORCED_PRE_EFFECT->EVIDENCE_INSUFFICIENT"])

# Hostile 7: unsupported completeness claim.
check("hostile-unsupported-completeness",
      mutate(lambda d: d["path_discovery"].__setitem__("completeness_claimed", True)),
      validation="INVALID", conformance="INDETERMINATE", defects=["UNSUPPORTED_COMPLETENESS"])

# Hostile 8: attempted outward effect.
check("hostile-outward-effect-enabled",
      mutate(lambda d: d["authority"].__setitem__("network", True)),
      validation="INVALID", conformance="INDETERMINATE", defects=["EFFECT_TRUE_NETWORK"])

# Hostile 9-10: malformed input must classify INVALID, never crash the detector.
check("hostile-top-level-list", [BASE], validation="INVALID", conformance="INDETERMINATE")
check("hostile-malformed-path-fields",
      mutate(lambda d: d["paths"][0].update(allow_twin=None, deny_twin=[], evidence="receiver_event")),
      validation="INVALID", conformance="INDETERMINATE")


class AssayCases(unittest.TestCase):
    def test_every_case(self):
        for name, data, expect in CASES:
            with self.subTest(name):
                run_case(name, data, **expect)


if __name__ == "__main__":
    for name, data, expect in CASES:
        run_case(name, data, **expect)
        print(f"PASS {name}")
    hostile = [n for n, _, _ in CASES if n.startswith("hostile-")]
    print(f"{len(CASES)}/{len(CASES)} PASS ({len(hostile)} hostile, 1 base, 1 label-free, 1 conformant twin)")
    sys.exit(0)
