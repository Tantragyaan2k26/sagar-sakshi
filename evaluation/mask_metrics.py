"""Scene-level segmentation metrics; scores are descriptive, not validation claims."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


def confusion_counts(prediction: np.ndarray, truth: np.ndarray) -> dict[str, int]:
    pred = np.asarray(prediction) > 0
    target = np.asarray(truth) > 0
    if pred.shape != target.shape:
        raise ValueError(f"Mask shapes differ: prediction {pred.shape}, truth {target.shape}")
    return {
        "tp": int(np.count_nonzero(pred & target)),
        "fp": int(np.count_nonzero(pred & ~target)),
        "fn": int(np.count_nonzero(~pred & target)),
        "tn": int(np.count_nonzero(~pred & ~target)),
    }


def _scores(counts: dict[str, int]) -> dict[str, float]:
    tp, fp, fn, tn = (counts[key] for key in ("tp", "fp", "fn", "tn"))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        **counts,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "iou": tp / (tp + fp + fn) if tp + fp + fn else 0.0,
        "false_positive_pixel_rate": fp / (fp + tn) if fp + tn else 0.0,
        "negative_patch_false_alarm": float(tp + fn == 0 and fp > 0),
    }


def evaluate_mask_folders(prediction_dir: str | Path, truth_dir: str | Path) -> dict[str, Any]:
    """Evaluate matching ``.npy`` masks; ``scene__patch.npy`` groups by scene."""
    prediction_dir, truth_dir = Path(prediction_dir), Path(truth_dir)
    predicted = {p.stem: p for p in prediction_dir.glob("*.npy")}
    truth = {p.stem: p for p in truth_dir.glob("*.npy")}
    if not truth:
        raise ValueError(f"No .npy ground-truth masks found in {truth_dir}")
    if predicted.keys() != truth.keys():
        missing = sorted(truth.keys() - predicted.keys())
        extra = sorted(predicted.keys() - truth.keys())
        raise ValueError(f"Prediction/label patch names differ; missing predictions={missing[:5]}, extra predictions={extra[:5]}")

    totals = {key: 0 for key in ("tp", "fp", "fn", "tn")}
    per_scene: dict[str, dict[str, int]] = defaultdict(lambda: {key: 0 for key in totals})
    per_patch_f1: list[float] = []
    for name in sorted(truth):
        pred_mask = np.load(predicted[name], allow_pickle=False)
        true_mask = np.load(truth[name], allow_pickle=False)
        counts = confusion_counts(pred_mask, true_mask)
        for key, value in counts.items():
            totals[key] += value
        # Prefix filenames with a scene/product ID and '__' to avoid patch leakage.
        scene_id = name.split("__", 1)[0]
        for key, value in counts.items():
            per_scene[scene_id][key] += value
        per_patch_f1.append(_scores(counts)["f1"])

    return {
        "patch_count": len(truth),
        "scene_count": len(per_scene),
        "split_warning": "Keep all patches from one source scene in a single train/validation/test split.",
        "micro": _scores(totals),
        "macro_patch_f1": float(np.mean(per_patch_f1)),
        "per_scene": {scene: _scores(counts) for scene, counts in sorted(per_scene.items())},
    }
