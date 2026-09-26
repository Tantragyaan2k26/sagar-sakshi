"""
SAGAR-SAKSHI Prototype Ranking Policy & Wording Rules (fusion/grading.py)
Implements normalized ranking weights, heuristic evidence-grade classification,
shortlist pruning, and legal wording rules (§9, §10).
"""

from typing import Literal, Any


BANNED_WORDS = ["responsible", "guilty", "perpetrator", "culprit", "offender"]


def validate_wording(text: str):
    """Enforces the strict business-logic rule that accusatory words are never emitted."""
    lower = text.lower()
    for word in BANNED_WORDS:
        if word in lower:
            raise ValueError(f"Strict business-logic violation: Banned word '{word}' found in headline/text: '{text}'")


def assign_grade(
    candidate_id: str,
    posterior: float,
    evidence_terms: dict[str, float],
    threshold_a: float = 0.70,
    threshold_b: float = 0.60,
) -> tuple[Literal["A", "B", "C", "None"], str]:
    """
    Assigns an evidence grade and enforced headline wording based on §9 rules:
    - Grade A: vessel at slick head at image time + consistent drift + posterior above threshold
      Allowed wording: "Strong lead; consistent with discharge by {vessel}"
    - Grade B: consistent drift + behaviour + >=2 independent evidence classes + posterior > 0.6
      Allowed wording: "Lead; consistent with {vessel}"
    - Grade C: proximity/timing only
      Allowed wording: "Vessels in the area" (no vessel named in headline)
    - Grade None: U above 0.5, or slick classified as likely look-alike, or insufficient score
      Allowed wording: "Insufficient evidence"
    """
    if candidate_id == "U":
        return "None", "Insufficient evidence"

    head_prox = evidence_terms.get("head_proximity", 0.0)
    drift_score = evidence_terms.get("drift_consistency", 0.0)
    behaviour_score = evidence_terms.get("behaviour", 0.0)
    geometry_score = evidence_terms.get("slick_geometry", 0.0)

    # Count independent evidence classes with significant support (Likelihood Ratio > 1.1)
    evidence_classes_present = sum([
        1 if drift_score >= 1.2 else 0,
        1 if behaviour_score >= 1.2 else 0,
        1 if geometry_score >= 1.1 else 0,
        1 if head_prox >= 1.5 else 0,
    ])

    # Grade A requirements: at head + consistent drift + high posterior
    if head_prox >= 2.0 and drift_score >= 1.2 and posterior >= threshold_a:
        grade = "A"
        headline = f"Strong lead; consistent with discharge by {candidate_id}"
    # Grade B requirements: consistent drift + behaviour + >= 2 independent classes + posterior >= threshold_b
    elif drift_score >= 1.2 and behaviour_score >= 1.2 and evidence_classes_present >= 2 and posterior >= threshold_b:
        grade = "B"
        headline = f"Lead; consistent with {candidate_id}"
    # Grade C requirements (proximity or timing only, or lower posterior)
    elif posterior > 0.20 and (drift_score >= 1.0 or head_prox >= 1.0):
        grade = "C"
        headline = "Vessels in the area"
    else:
        grade = "None"
        headline = "Insufficient evidence"

    # Enforce non-accusatory wording verification
    validate_wording(headline)
    return grade, headline


def compute_attribution(
    unnormalized_posteriors: dict[str, float],
    evidence_terms: dict[str, dict[str, float]],
    exclusions: list[dict[str, Any]],
    run_id: str,
    threshold_a: float = 0.70,
    threshold_b: float = 0.60,
) -> dict[str, Any]:
    """
    Normalizes posteriors, checks the Null hypothesis 'U', selects top candidates,
    and assigns grade + headline according to §9.
    """
    # 1. Ensure U is present
    if "U" not in unnormalized_posteriors:
        unnormalized_posteriors["U"] = 0.15

    # 2. Normalize posteriors so they sum exactly to 1.0
    total = sum(unnormalized_posteriors.values())
    if total <= 0:
        total = 1.0
    normalized_posteriors = {k: float(v / total) for k, v in unnormalized_posteriors.items()}

    # Ensure precision sum is 1.0
    sum_norm = sum(normalized_posteriors.values())
    diff = 1.0 - sum_norm
    # Absorb any tiny floating point discrepancy into 'U'
    normalized_posteriors["U"] += diff

    # 3. If U > 0.5, headline is strictly "Insufficient evidence", Grade None
    u_prob = normalized_posteriors["U"]
    sorted_hypotheses = sorted(
        [(k, v) for k, v in normalized_posteriors.items() if k != "U"],
        key=lambda item: item[1],
        reverse=True,
    )

    if u_prob > 0.5 or not sorted_hypotheses:
        grade = "None"
        headline = "Insufficient evidence"
    else:
        top_cand, top_post = sorted_hypotheses[0]
        terms = evidence_terms.get(top_cand, {})
        grade, headline = assign_grade(
            top_cand,
            top_post,
            terms,
            threshold_a=threshold_a,
            threshold_b=threshold_b,
        )

    # 4. Shortlist: at most 5 hypotheses, or smallest set covering 90% mass. U is always shown.
    all_sorted = sorted(normalized_posteriors.items(), key=lambda x: x[1], reverse=True)
    cumulative = 0.0
    shortlist_keys = set()
    for h, p in all_sorted:
        shortlist_keys.add(h)
        cumulative += p
        if len(shortlist_keys) >= 5 or cumulative >= 0.90:
            break
    # U is always shown
    shortlist_keys.add("U")

    final_posteriors = {k: round(normalized_posteriors[k], 4) for k in normalized_posteriors}
    # Absorb any 4-decimal rounding discrepancy into 'U' so sum is exactly 1.0000
    round_sum = sum(final_posteriors.values())
    round_diff = round(1.0 - round_sum, 4)
    final_posteriors["U"] = round(final_posteriors["U"] + round_diff, 4)

    # Wording check
    validate_wording(headline)

    return {
        "schema_version": "1.0",
        "run_id": run_id,
        "posteriors": final_posteriors,
        "evidence_terms": evidence_terms,
        "grade": grade,
        "exclusions": exclusions,
        "headline": headline,
    }
