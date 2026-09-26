"""
SAGAR-SAKSHI Legal & Wording Safeguard Tests (tests/test_wording_rules.py)
Automated tests enforcing strict headline wording rules, grade assignments,
and prevention of accusatory language (§9, §10).
"""

import pytest
from fusion.grading import assign_grade, compute_attribution, validate_wording


def test_grade_a_wording():
    """Grade A requires vessel at slick head + consistent drift + high posterior -> 'Strong lead; consistent with discharge by {vessel}'."""
    terms = {"head_proximity": 5.0, "drift_consistency": 2.5, "behaviour": 1.8, "slick_geometry": 1.4}
    grade, headline = assign_grade("MSC ELSA 3", 0.78, terms, threshold_a=0.70)

    assert grade == "A"
    assert headline == "Strong lead; consistent with discharge by MSC ELSA 3"


def test_grade_b_wording():
    """Grade B requires consistent drift + behaviour + >=2 classes + posterior > 0.6 -> 'Lead; consistent with {vessel}'."""
    terms = {"drift_consistency": 2.2, "behaviour": 1.8, "slick_geometry": 1.4, "head_proximity": 0.5}
    grade, headline = assign_grade("MSC ELSA 3", 0.65, terms, threshold_a=0.70, threshold_b=0.60)

    assert grade == "B"
    assert headline == "Lead; consistent with MSC ELSA 3"


def test_grade_c_no_vessel_named():
    """Grade C (proximity or timing only) must NEVER name a vessel in the headline."""
    terms = {"drift_consistency": 1.0, "head_proximity": 1.0}
    grade, headline = assign_grade("MSC ELSA 3", 0.35, terms)

    assert grade == "C"
    assert headline == "Vessels in the area"
    assert "MSC ELSA 3" not in headline, "Grade C headline must not name any specific vessel!"


def test_grade_none_insufficient_evidence():
    """When U > 0.5 or evidence is weak, headline must be 'Insufficient evidence'."""
    unnorm = {"V_01": 0.2, "U": 0.8}
    evidence = {"V_01": {"drift_consistency": 0.2}}
    result = compute_attribution(unnorm, evidence, [], "run_003")

    assert result["grade"] == "None"
    assert result["headline"] == "Insufficient evidence"


def test_banned_words_prevention():
    """Verify that terms like 'responsible', 'guilty', 'culprit' are strictly forbidden."""
    with pytest.raises(ValueError, match="Banned word 'responsible'"):
        validate_wording("Vessel MSC ELSA 3 is responsible for the spill")

    with pytest.raises(ValueError, match="Banned word 'guilty'"):
        validate_wording("MSC ELSA 3 is guilty")
