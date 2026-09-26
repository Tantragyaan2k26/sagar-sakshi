"""Prototype run manifest and provenance tracker. Records configuration, source status, model labels, content digests, and outputs. Large source files use an explicitly labeled sampled digest; this is not a signed or immutable chain-of-custody service."""

import hashlib
import json
import os
from typing import Any


def hash_file(filepath: str) -> str:
    """Computes SHA256 hash of a file. Returns empty string if file doesn't exist."""
    if not os.path.exists(filepath):
        return f"file_not_found:{filepath}"
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read in 1MB chunks to handle large files (e.g. 2.9GB GeoTIFF)
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def hash_dict(d: dict[str, Any]) -> str:
    """Computes SHA256 hash of a serialized dictionary."""
    serialized = json.dumps(d, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


class RunManifest:
    """Tracks inputs, configurations, model rungs, random seeds, and outputs for a run."""

    def __init__(self, run_id: str, config: dict[str, Any]):
        self.run_id = run_id
        self.config = config
        self.inputs: dict[str, Any] = {}
        self.models: dict[str, str] = {}
        self.seeds: dict[str, int] = {"drift": 42, "bootstrap": 1337}
        self.outputs: dict[str, Any] = {}

    def record_input(self, name: str, filepath: str | None = None, metadata: dict | None = None):
        """Records an input dataset with its sha256 checksum."""
        entry = metadata.copy() if metadata else {}
        if filepath:
            entry["filepath"] = filepath
            if not os.path.exists(filepath):
                entry["status"] = "missing"
                self.inputs[name] = entry
                return
            # For 2.9GB BigTIFF, record file stat + quick partial header hash for speed or full hash
            file_size = os.path.getsize(filepath)
            entry["status"] = "available"
            entry["size_bytes"] = file_size
            if file_size > 100 * 1024 * 1024:
                # Label the sample explicitly; it is not a full-file checksum.
                h = hashlib.sha256()
                with open(filepath, "rb") as f:
                    h.update(f.read(10 * 1024 * 1024))
                    f.seek(max(0, file_size - 1024 * 1024))
                    h.update(f.read(1024 * 1024))
                entry["sha256"] = {"value": h.hexdigest(), "method": "first_10MiB_plus_last_1MiB_sample"}
            else:
                entry["sha256"] = {"value": hash_file(filepath), "method": "full_file"}
        self.inputs[name] = entry

    def record_value(self, name: str, value: Any, description: str | None = None):
        """Records a serialized in-memory input (for example synthetic AIS or forcing defaults)."""
        entry = {"sha256": hash_dict(value), "value": value}
        if description:
            entry["description"] = description
        self.inputs[name] = entry

    def record_model(self, component: str, rung: str):
        """Records the model ladder rung used (e.g. 'baseline_threshold', 'cfar_only', 'bayesian_hand_weights')."""
        self.models[component] = rung

    def finalize(self, attribution_result: dict[str, Any]) -> str:
        """Finalizes the manifest and computes the run manifest SHA256."""
        self.outputs["attribution"] = attribution_result
        payload = {
            "run_id": self.run_id,
            "config": self.config,
            "inputs": self.inputs,
            "models": self.models,
            "seeds": self.seeds,
            "outputs": self.outputs,
        }
        self.manifest_sha256 = hash_dict(payload)
        return self.manifest_sha256

    def to_dict(self) -> dict[str, Any]:
        result = {
            "run_id": self.run_id,
            "config": self.config,
            "inputs": self.inputs,
            "models": self.models,
            "seeds": self.seeds,
            "outputs": self.outputs,
        }
        if hasattr(self, "manifest_sha256"):
            result["manifest_sha256"] = self.manifest_sha256
        return result
