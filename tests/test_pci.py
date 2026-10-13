"""Independently known answers; fixtures verify software, not clinical validity."""
import json
import math
from pathlib import Path

import pytest

from backend.app.services import pci_service

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize("row,score,category", [
    ({"criteria_count": .008}, .01, "Low"),
    ({"criteria_count": 40, "primary_outcomes": 5, "enrollment": 499.49}, 39.99, "Low"),
    ({"criteria_count": 40, "primary_outcomes": 5, "enrollment": 499.5}, 40, "Medium"),
    ({"criteria_count": 40, "primary_outcomes": 10, "secondary_outcomes": 20, "enrollment": 500}, 70, "Medium"),
    ({"criteria_count": 40, "primary_outcomes": 10, "secondary_outcomes": 20, "enrollment": 500.49}, 70, "Medium"),
    ({"criteria_count": 40, "primary_outcomes": 10, "secondary_outcomes": 20, "enrollment": 500.5}, 70.01, "High"),
])
def test_half_up_rounding_and_categories_use_rounded_score(row, score, category):
    # Catches float/ties-to-even drift and category decisions before rounding.
    actual_score, actual_category, _ = pci_service.calculate_pci(row)
    assert actual_score == score
    assert actual_category == category


def test_decimal_string_just_below_tie_is_not_rounded_as_tie():
    # Precision cannot collapse an exact below-half decimal into a half tie.
    assert pci_service.calculate_pci({"criteria_count": "0.0079999999999999999999999999999999999999"})[0] == 0
    assert pci_service.calculate_pci({"criteria_count": "0.008"})[0] == .01


@pytest.mark.parametrize("invalid", ["1e-321", "0" * 341, "1e309"])
def test_scalar_bounds_reject_out_of_contract_decimal_representations(invalid):
    # A pathological finite underflow exponent must not allocate huge integers.
    result = pci_service.calculate_pci_details({"criteria_count": invalid})
    assert result["score"] == 0
    assert "criteria_count" in result["missing_fields"]


def test_accepted_long_decimal_keeps_finite_components():
    result = pci_service.calculate_pci_details({"criteria_count": "0." + "9" * 319})
    # Its contribution is strictly below .625, so exact half-up yields .62.
    assert result["score"] == .62
    assert result["components"]["Eligibility burden"] == pytest.approx(.625)
    assert "criteria_count" not in result["missing_fields"]


def test_v3_fixture_scores_are_preserved():
    fixture = json.loads((ROOT / "frontend/src/sample.json").read_text())
    expected = [(25.5, "Low"), (55.4, "Medium"), (12.6, "Low"), (41.05, "Medium"), (52.9, "Medium")]
    assert [pci_service.calculate_pci(row)[:2] for row in fixture] == expected


def test_shared_known_answer_cases():
    config = json.loads((ROOT / "configs/formulas.json").read_text())
    for case in config["parity_cases"]:
        result = pci_service.calculate_pci_details(case["row"])
        assert result["score"] == case["expected"]["score"], case["id"]
        assert result["category"] == case["expected"]["category"], case["id"]
        assert result["missing_fields"] == case["expected"]["missing_fields"], case["id"]


@pytest.mark.parametrize("invalid", [None, "", "   ", "bad", "NaN", "Infinity", "-Infinity", float("nan"), float("inf"), -float("inf"), True, False, [], {}, "0x10", "1_000"])
def test_missing_invalid_nonfinite_are_disclosed_and_zero(invalid):
    row = {"criteria_count": invalid, "primary_outcomes": 0, "secondary_outcomes": 0,
           "number_of_arms": 0, "enrollment": 0, "text_complexity": 0}
    result = pci_service.calculate_pci_details(row)
    assert result["score"] == 0
    assert result["components"]["Eligibility burden"] == 0
    assert result["missing_fields"] == ["criteria_count"]
    json.dumps(result, allow_nan=False)


def test_negative_values_clip_without_claiming_missingness():
    row = {"criteria_count": -1, "primary_outcomes": -10, "secondary_outcomes": -20,
           "number_of_arms": -8, "enrollment": -1000, "text_complexity": -20}
    result = pci_service.calculate_pci_details(row)
    assert result["score"] == 0
    assert set(result["components"].values()) == {0}
    assert result["missing_fields"] == []


def test_ceilings_weights_clipping_and_legacy_tuple_contract():
    row = {"criteria_count": 400, "primary_outcomes": 100, "secondary_outcomes": 200,
           "number_of_arms": 80, "enrollment": 10000, "text_complexity": 200}
    score, category, components = pci_service.calculate_pci(row)
    assert score == 100
    assert category == "High"
    assert components == {"Eligibility burden": 25, "Primary outcome burden": 20,
                          "Secondary outcome burden": 20, "Arm complexity": 15,
                          "Enrollment burden": 10, "Text complexity": 10}
    assert sum(components.values()) == 100
    assert all(math.isfinite(value) and 0 <= value <= 25 for value in components.values())


def test_metric_known_answers_and_undefined_r2():
    # SSE=4+4+9=17, absolute errors=2+2+3=7, SST=100+0+100=200.
    from src.clinical_trial_intelligence.research import evaluate_predictions
    result = evaluate_predictions([10, 20, 30], [12, 18, 33], [0, 1, 1], [.2, .8, .6], bootstrap_samples=0)
    assert result["regression"]["mae"] == pytest.approx(7 / 3)
    assert result["regression"]["rmse"] == pytest.approx(math.sqrt(17 / 3))
    assert result["regression"]["r2"] == pytest.approx(.915)
    assert result["classification"]["brier"] == pytest.approx(.08)
    constant = evaluate_predictions([10, 10], [9, 11], [0, 1], [.2, .8], bootstrap_samples=0)
    assert constant["regression"]["r2"] is None
