"""Create an implementation-honest copy of the supplied SIH deck.

Usage: python scripts/update_pitch_deck.py input.pptx output.pptx
Only existing slide text runs are changed; media, layout, and relationships are copied.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


REPLACEMENTS: dict[int, dict[str, str]] = {
    2: {
        "RANK SUSPECTS": "RANK LEADS",
        "Satellites can spot a slick, but tying it to one ship is the bottleneck: slicks drift, ships move, and AIS can be switched off.": "Slicks drift and AIS can be incomplete; coverage must be known before interpreting a missing match.",
        "Sentinel-1 radar separates real spills from look-alikes (wind slicks, algal blooms).": "Prototype: dark-pixel candidates plus heuristic look-alike checks.",
        "A parallel ship detector finds vessels in the scene, even those with AIS off.": "An experimental bright-target detector proposes SAR ship candidates.",
        "Slick traced back in time, AIS tracks forward, using ocean currents + wind.": "Custom drift approximation with constant configured forcing.",
        "Space-time match, AIS gaps and behaviour give a ranked list with evidence + confidence.": "Hand-set evidence ratios produce a shortlist; scores are not calibrated probabilities.",
        "A ship with AIS off is invisible": "SAR target has no AIS match",
        "SAR still sees it; the AIS gap becomes a red flag": "Unverified unless independent receiver-coverage evidence is available",
        "Timestamped evidence card + confidence score": "Evidence card + source manifest + stated uncertainty",
        "spill/look-alike model and ship detector are separate, so each improves without retraining the other.": "Separate spill and ship branches support independent evaluation.",
        "slick traced back + AIS tracks forward; a match score beats one-way back-tracking (Mar. Pollut. Bull. 2024).": "Custom two-way drift approximation; forcing and skill remain unvalidated.",
        "ships seen by SAR but missing from AIS are ranked as high suspicion.": "SAR-only targets are dark only when independent coverage evidence passes threshold.",
        "dual-pol Sentinel-1 baseline; replay Ennore 2017; cross-check INCOIS OOSA.": "Synthetic demo inputs today; real-data replay and Indian validation are planned.",
    },
    3: {
        "(VV + VH bands)": "(one configured band in current run)",
        "AIS tracks, last 24 h": "Synthetic AIS scenario (default)",
        "Radiometric calibration": "Load configured GeoTIFF band",
        "Refined-Lee despeckle": "No despeckling in current run",
        "Land mask": "AOI crop",
        "256 x 256 tiles": "Synthetic 256x256 fallback",
        "U-Net: spill / look-alike / sea": "Threshold + experimental synthetic-patch U-Net",
        "CFAR + CNN: vessel positions": "Global threshold + clustering (experimental)",
        "Back-track slick,": "Custom backward/forward drift approximation",
        "forward-track AIS": "No OpenDrift or particle ensemble",
        "Currents + wind": "Configured constant forcing (no live fetch)",
        "AIS gap = dark-vessel flag": "Coverage >=90% required; unknown = unverified",
        "Score + confidence": "Hand-set likelihood ratios + null U",
        "dual-pol Sentinel-1, always on.   ": "Current demo: synthetic AIS; SAR file optional.   ",
        "Sample output: ranked suspect vessels (illustrative dummy data)": "Illustrative synthetic output (values are not calibrated probabilities)",
        "AIS off 3.5 h · drift match 0.91": "Synthetic track · heuristic drift term",
        "PyTorch": "NumPy prototype",
        "U-Net": "Experimental U-Net",
        "OpenCV (CFAR)": "Pixel clustering",
        "OpenDrift / GNOME": "Planned: OpenDrift",
        "CMEMS + HYCOM currents": "Planned: gridded currents",
        "ERA5 winds": "Planned: replay wind data",
        "PostgreSQL + PostGIS": "Local SQLite prototype",
        "React": "Static HTML mockups",
        "Kepler.gl / MapLibre": "Planned: live map layers",
    },
    4: {
        "Sentinel-1, CMEMS, ERA5 are free and global; AIS via public feeds + synthetic tracks for the demo.": "Data sources are feasible; the current demo uses synthetic AIS and constant configured forcing.",
        "Runs on one GPU workstation or cloud VM; outputs a map + report.": "Prototype runs locally; deployment performance has not been measured.",
        "AIS gap = high-suspicion flag; SAR-only ships listed as dark vessels.": "Require measured receiver coverage; otherwise label SAR-only targets unverified.",
        "Own look-alike class, Dice / weighted loss, wind context.": "Validate look-alike handling on labeled scenes across wind conditions.",
        "Cap window at about 24 h; particle ensemble; cross-check INCOIS OOSA.": "Planned: evaluate drift with gridded forcing and known-source replays.",
        "Sentinel-1 baseline, twin-branch models, drift + AIS ranking on one replayed case.": "Complete one replay with verified inputs, source labels, and end-to-end provenance.",
        "Validate on Indian incidents (Ennore 2017) and INCOIS OOSA; tune scoring.": "Planned: validate on known-source cases and report calibration and false accusations.",
    },
    5: {
        "Ranked suspects": "Ranked candidates",
        "MARPOL enforcement. Evidence-grade lead list for penalty and cost recovery.": "Decision support only; prototype output is not a regulatory finding.",
        "Adds vessel attribution to the Online Oil Spill Advisory.": "Potential future extension: vessel-attribution decision support.",
        "Maritime domain awareness; dark-vessel flags from SAR alone.": "Coverage-aware SAR-only candidates when independent coverage data is available.",
        "How success will be measured (design targets, validated in prototype)": "Proposed evaluation metrics (targets only; not yet measured)",
        "< 1 h": "ECE <=0.05",
        "scene to ranked list": "OSSE target; not measured",
        "≤ 5": "FAR <=5%",
        "vessels in final shortlist": "OSSE target; not measured",
        "IoU · F1": "IoU / F1",
        "per class, held-out scenes": "held-out labeled scenes",
        "Top-3": "Top-3",
        "hit rate on replayed incidents": "known-source replay hit rate",
    },
}


def update_text(xml: bytes, replacements: dict[str, str], slide_no: int) -> bytes:
    text = xml.decode("utf-8")
    changed: set[str] = set()

    def replace_run(match: re.Match[str]) -> str:
        old = html.unescape(match.group(2))
        new = replacements.get(old)
        if new is None:
            return match.group(0)
        changed.add(old)
        return match.group(1) + html.escape(new, quote=False) + match.group(3)

    result = re.sub(r"(<a:t\b[^>]*>)(.*?)(</a:t>)", replace_run, text, flags=re.S)
    missing = set(replacements) - changed
    if missing:
        raise ValueError(f"Slide {slide_no}: text runs not found: {sorted(missing)}")
    return result.encode("utf-8")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    src, dst = map(Path, sys.argv[1:])
    dst.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(src, "r") as source, ZipFile(dst, "w", ZIP_DEFLATED) as output:
        for item in source.infolist():
            data = source.read(item.filename)
            match = re.fullmatch(r"ppt/slides/slide(\d+)\.xml", item.filename)
            if match:
                slide_no = int(match.group(1))
                if slide_no in REPLACEMENTS:
                    data = update_text(data, REPLACEMENTS[slide_no], slide_no)
            output.writestr(item, data)
    print(f"Wrote {dst}")


if __name__ == "__main__":
    main()
