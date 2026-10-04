#!/usr/bin/env python3
"""Validator entrypoint for the Harbor verifier.

Wraps `freecad_validator.Validator.validate()` (geometry similarity +
spec consistency, harmonic-mean combined). Emits the Harbor reward
contract: a float in [0, 1] at --reward-txt, and a single-key
`{"reward": <score>}` JSON at --reward-json. Per-axis sub-scores and
reasons are written to a `reward_details.json` sidecar so they are not
parsed as the reward.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path


def main() -> int:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, help="ground-truth .FCStd")
    parser.add_argument("--candidate", required=True, help="candidate .FCStd")
    parser.add_argument("--spec", required=True, help="per-case spec .json (name, description, key_parameters)")
    parser.add_argument("--reward-txt", required=True)
    parser.add_argument("--reward-json", required=True)
    args = parser.parse_args()

    from freecad_validator import Validator

    result = Validator().validate(
        candidate_fcstd=args.candidate,
        reference_fcstd=args.reference,
        spec_json=args.spec,
    )

    score = max(0.0, min(1.0, float(result.combined)))
    Path(args.reward_txt).write_text(f"{score:.6f}\n")

    # Harbor reward contract: reward.json carries the single-key reward.
    Path(args.reward_json).write_text(json.dumps({"reward": score}, indent=2) + "\n")

    # Sub-scores + reasons go to a sidecar so debugging info isn't lost and
    # isn't mistaken for the reward by the verifier's result parser.
    details_path = Path(args.reward_json).with_name("reward_details.json")
    details_path.write_text(json.dumps({
        "score": score,
        "geometry_similarity": result.geometry_similarity,
        "cad_spec_consistency": result.cad_spec_consistency,
        "combined": result.combined,
        "geometry_similarity_reason": result.geometry_similarity_reason,
        "cad_spec_consistency_reason": result.cad_spec_consistency_reason,
    }, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
