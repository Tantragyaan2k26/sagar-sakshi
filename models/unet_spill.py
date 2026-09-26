"""
Compact 2-level U-Net for SAR dark-patch segmentation.
Trained on synthetic C-band-like patches; weights in models/weights/unet_spill.npz.
Phase-1 ML rung — DeepLabv3+ remains the optional accuracy-layer upgrade.
"""

from __future__ import annotations
import os
import numpy as np

WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "weights", "unet_spill.npz")


def _conv2d(x: np.ndarray, k: np.ndarray, b: np.ndarray) -> np.ndarray:
    kh, kw, cin, cout = k.shape
    pad = kh // 2
    xp = np.pad(x, ((pad, pad), (pad, pad), (0, 0)), mode="edge")
    h, w, _ = x.shape
    out = np.empty((h, w, cout), dtype=np.float32)
    for oy in range(cout):
        acc = np.zeros((h, w), dtype=np.float32)
        for iy in range(cin):
            for dy in range(kh):
                for dx in range(kw):
                    acc += k[dy, dx, iy, oy] * xp[dy:dy + h, dx:dx + w, iy]
        out[:, :, oy] = acc + b[oy]
    return out


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(x, 0.0)


def _pool2(x: np.ndarray) -> np.ndarray:
    h, w, c = x.shape
    h2, w2 = h // 2, w // 2
    x = x[: h2 * 2, : w2 * 2]
    return x.reshape(h2, 2, w2, 2, c).max(axis=(1, 3))


def _upsample2(x: np.ndarray, shape_hw: tuple[int, int]) -> np.ndarray:
    y = np.repeat(np.repeat(x, 2, axis=0), 2, axis=1)
    h, w = shape_hw
    return y[:h, :w]


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -20.0, 20.0)))


class TinyUNet:
    def __init__(self, weights: dict[str, np.ndarray]):
        self.w = weights

    @classmethod
    def load_or_train(cls, path: str = WEIGHTS_PATH) -> "TinyUNet":
        if os.path.exists(path):
            data = np.load(path)
            return cls({k: data[k] for k in data.files})
        weights = train_tiny_unet()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        np.savez(path, **weights)
        return cls(weights)

    def encode(self, patch: np.ndarray) -> np.ndarray:
        x = patch.astype(np.float32)
        if x.ndim == 2:
            x = x[..., None]
        w = self.w
        e1 = _relu(_conv2d(x, w["e1k"], w["e1b"]))
        e2 = _relu(_conv2d(_pool2(e1), w["e2k"], w["e2b"]))
        btm = _relu(_conv2d(_pool2(e2), w["bk"], w["bb"]))
        d2 = _relu(_conv2d(np.concatenate([_upsample2(btm, e2.shape[:2]), e2], axis=2), w["d2k"], w["d2b"]))
        d1 = _relu(_conv2d(np.concatenate([_upsample2(d2, e1.shape[:2]), e1], axis=2), w["d1k"], w["d1b"]))
        return d1

    def predict_logits(self, patch: np.ndarray) -> np.ndarray:
        d1 = self.encode(patch)
        return _conv2d(d1, self.w["ok"], self.w["ob"])[:, :, 0]

    def predict_mask(self, crop_db: np.ndarray, threshold: float = 0.45) -> np.ndarray:
        h, w = crop_db.shape[:2]
        tile = 64
        finite = crop_db[np.isfinite(crop_db)]
        mu = float(np.mean(finite)) if finite.size else 0.0
        sd = float(np.std(finite)) if finite.size else 1.0
        norm = ((np.nan_to_num(crop_db, nan=mu) - mu) / max(1e-3, sd)).astype(np.float32)
        if h <= tile and w <= tile:
            pad = np.zeros((tile, tile), dtype=np.float32)
            pad[:h, :w] = norm
            return _sigmoid(self.predict_logits(pad))[:h, :w] >= threshold
        prob = np.zeros((h, w), dtype=np.float32)
        wt = np.zeros((h, w), dtype=np.float32)
        step = tile // 2
        for r in range(0, h, step):
            for c in range(0, w, step):
                r1, c1 = min(h, r + tile), min(w, c + tile)
                pad = np.zeros((tile, tile), dtype=np.float32)
                sl = norm[r:r1, c:c1]
                pad[: sl.shape[0], : sl.shape[1]] = sl
                p = _sigmoid(self.predict_logits(pad))
                prob[r:r1, c:c1] += p[: r1 - r, : c1 - c]
                wt[r:r1, c:c1] += 1.0
        return (prob / np.maximum(wt, 1e-6)) >= threshold


def _synthetic_patch(rng: np.random.Generator, size: int = 64) -> tuple[np.ndarray, np.ndarray]:
    img = rng.normal(0.0, 1.0, size=(size, size)).astype(np.float32)
    mask = np.zeros((size, size), dtype=np.float32)
    if rng.random() > 0.2:
        cy, cx = int(rng.integers(16, 48)), int(rng.integers(16, 48))
        a, b = float(rng.uniform(6, 18)), float(rng.uniform(3, 8))
        ang = float(rng.uniform(0, np.pi))
        yy, xx = np.ogrid[:size, :size]
        x = (xx - cx) * np.cos(ang) + (yy - cy) * np.sin(ang)
        y = -(xx - cx) * np.sin(ang) + (yy - cy) * np.cos(ang)
        ell = (x / a) ** 2 + (y / b) ** 2 <= 1.0
        img[ell] -= float(rng.uniform(1.8, 4.0))
        mask[ell] = 1.0
    return img, mask


def _init_weights(rng: np.random.Generator) -> dict[str, np.ndarray]:
    def k(shape):
        return rng.normal(0, 0.12, size=shape).astype(np.float32)

    return {
        "e1k": k((3, 3, 1, 4)), "e1b": np.zeros(4, np.float32),
        "e2k": k((3, 3, 4, 8)), "e2b": np.zeros(8, np.float32),
        "bk": k((3, 3, 8, 8)), "bb": np.zeros(8, np.float32),
        "d2k": k((3, 3, 16, 8)), "d2b": np.zeros(8, np.float32),
        "d1k": k((3, 3, 12, 4)), "d1b": np.zeros(4, np.float32),
        "ok": k((1, 1, 4, 1)), "ob": np.zeros(1, np.float32),
    }


def train_tiny_unet(n_samples: int = 40, epochs: int = 6, lr: float = 0.05, seed: int = 7) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    w = _init_weights(rng)
    net = TinyUNet(w)
    patches = [_synthetic_patch(rng) for _ in range(n_samples)]
    for _ in range(epochs):
        rng.shuffle(patches)
        for img, mask in patches:
            feats = net.encode(img)  # H,W,4
            logits = _conv2d(feats, w["ok"], w["ob"])[:, :, 0]
            pred = _sigmoid(logits)
            err = (pred - mask).astype(np.float32)
            # dL/dW = feat^T * err  (MSE)
            fh, fw, fc = feats.shape
            f = feats.reshape(fh * fw, fc)
            e = err.reshape(fh * fw, 1)
            grad_k = (f.T @ e) / (fh * fw)
            w["ok"] -= (lr * grad_k.reshape(1, 1, 4, 1)).astype(np.float32)
            w["ob"] -= np.array([lr * float(err.mean())], dtype=np.float32)
            net.w = w
    return w


def ensure_weights(path: str = WEIGHTS_PATH) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        np.savez(path, **train_tiny_unet())
    return path
