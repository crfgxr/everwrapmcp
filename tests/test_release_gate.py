"""Run separately after the experiment. Failures intentionally block integration."""
import json
from pathlib import Path
import pytest

REPORT = Path(__file__).resolve().parents[1] / "docs/baseline-results.json"

@pytest.mark.parametrize("case", [
    "english_person", "email", "turkish_phone", "turkish_person",
    "turkish_birthday", "openai_key", "password", "bearer",
    "connection_string", "useful_text",
])
def test_baseline_release_gate(case):
    assert REPORT.exists(), "Run python -m experiments.baseline first"
    report = json.loads(REPORT.read_text())
    row = next(r for r in report["results"] if r["case"] == case)
    assert row["passed"], f"Baseline privacy/utility failure: {case}"
