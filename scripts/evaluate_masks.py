"""Calculate pixel and per-scene mask metrics for a held-out benchmark folder."""

from __future__ import annotations

import argparse
import json

from evaluation.mask_metrics import evaluate_mask_folders


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", required=True, help="Folder of prediction .npy masks")
    parser.add_argument("--labels", required=True, help="Folder of reference .npy masks")
    parser.add_argument("--output", help="Optional JSON metrics output path")
    args = parser.parse_args()
    result = evaluate_mask_folders(args.predictions, args.labels)
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()
