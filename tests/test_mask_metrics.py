import numpy as np
import pytest

from evaluation.mask_metrics import confusion_counts, evaluate_mask_folders


def test_mask_metrics_hand_computed_counts_and_rates():
    truth = np.array([[1, 1], [0, 0]])
    prediction = np.array([[1, 0], [1, 0]])
    counts = confusion_counts(prediction, truth)
    assert counts == {"tp": 1, "fp": 1, "fn": 1, "tn": 1}


def test_folder_evaluator_groups_by_scene_and_catches_shape_mismatch(tmp_path):
    preds, labels = tmp_path / "pred", tmp_path / "labels"
    preds.mkdir(); labels.mkdir()
    np.save(labels / "sceneA__patch1.npy", np.array([[1, 0], [0, 0]]))
    np.save(preds / "sceneA__patch1.npy", np.array([[1, 1], [0, 0]]))
    np.save(labels / "sceneB__patch1.npy", np.zeros((2, 2), dtype=np.uint8))
    np.save(preds / "sceneB__patch1.npy", np.zeros((2, 2), dtype=np.uint8))
    result = evaluate_mask_folders(preds, labels)
    assert result["scene_count"] == 2
    assert result["micro"]["precision"] == pytest.approx(0.5)
    assert result["per_scene"]["sceneB"]["negative_patch_false_alarm"] == 0.0
    np.save(preds / "sceneA__patch1.npy", np.zeros((3, 3), dtype=np.uint8))
    with pytest.raises(ValueError, match="Mask shapes differ"):
        evaluate_mask_folders(preds, labels)
