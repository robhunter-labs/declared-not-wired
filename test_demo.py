import importlib.util
import json
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from demo import build_fixture, main


DETECTOR = Path(__file__).resolve().parent / "validate_assay.py"


def load_detector():
    spec = importlib.util.spec_from_file_location("dnw_detector", DETECTOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DemoTests(unittest.TestCase):
    def test_checked_in_fixture_matches_observed_twins(self):
        checked_in = json.loads((DETECTOR.parent / "fixture.json").read_text())
        generated = build_fixture()
        self.assertEqual(len(checked_in["paths"]), len(generated["paths"]))
        for expected, observed in zip(checked_in["paths"], generated["paths"]):
            self.assertEqual(expected["id"], observed["id"])
            for field in ("allow_twin", "deny_twin", "evidence"):
                self.assertEqual(expected[field], observed[field], (expected["id"], field))

    def test_classify_cli_distinguishes_unwired_and_all_wired(self):
        for options, expected in ((["--classify"], "NON_CONFORMANT"),
                                  (["--all-wired", "--classify"], "CONFORMANT")):
            output = StringIO()
            with patch("sys.argv", ["demo.py", *options]), redirect_stdout(output):
                self.assertEqual(main(), 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report["validation"], "VALID")
            self.assertEqual(report["conformance"], expected)

    def test_unwired_routes_are_observed_at_receiver(self):
        fixture = build_fixture()
        paths = {path["id"]: path for path in fixture["paths"]}
        self.assertEqual(len(paths), 4)
        self.assertFalse(paths["function_tool"]["deny_twin"]["effect_observed"])
        for name in ("hosted_surrogate", "specialist_handoff", "recovery_adapter"):
            self.assertTrue(paths[name]["deny_twin"]["effect_observed"])
        self.assertTrue(all(path["allow_twin"]["receiver_healthy"] for path in paths.values()))

    def test_detector_classifies_observed_traces_without_labels(self):
        detector = load_detector()
        fixture = build_fixture()
        report = detector.classify(fixture, json.dumps(fixture).encode())
        self.assertEqual(report["validation"], "VALID")
        self.assertEqual(report["path_states"], {
            "function_tool": "ENFORCED_PRE_EFFECT",
            "hosted_surrogate": "PATH_UNMEDIATED",
            "specialist_handoff": "WARN_ONLY",
            "recovery_adapter": "EVALUATED_POST_EFFECT",
        })

    def test_all_wired_twin_is_conformant(self):
        detector = load_detector()
        fixture = build_fixture(all_wired=True)
        report = detector.classify(fixture, json.dumps(fixture).encode())
        self.assertEqual(report["validation"], "VALID")
        self.assertEqual(report["conformance"], "CONFORMANT")
        self.assertEqual(report["findings"], [])


if __name__ == "__main__":
    unittest.main()
