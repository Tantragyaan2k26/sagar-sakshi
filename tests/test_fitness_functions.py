"""
SAGAR-SAKSHI Fitness Functions Test Suite (tests/test_fitness_functions.py)
Automated architectural fitness functions guarding mathematical and integrity requirements (§9, §12).
"""

import pytest
from fusion.grading import compute_attribution
from evidence.manifest import RunManifest


def test_posterior_sums_to_one():
    """Fitness Function 1: Posterior must always sum to 1.0 across the hypothesis set."""
    unnorm = {"V_01": 0.45, "V_02": 0.20, "D_01": 0.10, "U": 0.15}
    evidence = {
        "V_01": {"drift_consistency": 0.8, "head_proximity": 0.7, "behaviour": 0.6},
        "V_02": {"drift_consistency": 0.4},
        "D_01": {"drift_consistency": 0.3},
    }
    result = compute_attribution(unnorm, evidence, [], "run_test_001")

    total_prob = sum(result["posteriors"].values())
    assert pytest.approx(total_prob, abs=1e-4) == 1.0, f"Posteriors sum to {total_prob}, expected 1.0"


def test_unknown_hypothesis_u_always_present():
    """Fitness Function 2: Hypothesis 'U' (unknown/natural) must ALWAYS be present in the output."""
    # Even if caller omits U completely
    unnorm = {"V_01": 0.80, "V_02": 0.20}
    evidence = {"V_01": {"drift_consistency": 0.9}}
    result = compute_attribution(unnorm, evidence, [], "run_test_002")

    assert "U" in result["posteriors"], "Null hypothesis 'U' was omitted from output posteriors!"
    assert result["posteriors"]["U"] > 0.0, "'U' posterior must be strictly positive"


def test_manifest_reproducibility():
    """Fitness Function 3: A run is byte-identical and produces identical SHA256 when re-executed from same manifest."""
    config = {"aoi": [75.5, 8.8, 76.8, 10.2], "scene_id": "S1A_TEST"}
    manifest1 = RunManifest("run_001", config)
    manifest1.record_model("perception", "baseline_threshold")
    manifest1.record_model("drift", "ensemble_24h")
    hash1 = manifest1.finalize({"grade": "B", "posteriors": {"V_01": 0.65, "U": 0.35}})

    manifest2 = RunManifest("run_001", config)
    manifest2.record_model("perception", "baseline_threshold")
    manifest2.record_model("drift", "ensemble_24h")
    hash2 = manifest2.finalize({"grade": "B", "posteriors": {"V_01": 0.65, "U": 0.35}})

    assert hash1 == hash2, "Manifest hashes for identical runs must be byte-identical"
