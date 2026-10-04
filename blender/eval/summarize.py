"""Collect run_eval.sh's per-scorer JSON into one table and scores.json.

    python eval/summarize.py <out_dir>
"""
import json
import sys
from pathlib import Path

SYSTEMS = ["reference", "candidate", "noop_cube"]

# (label, metrics file, path to the value, which direction is better)
METRICS = [
    ("Executability",       "executability.json",                 ["pass_rate"],                               "higher"),
    ("Chamfer (yaw-min)",   "shape_chamfer.json",                 ["cd_yawmin", "conditional_mean"],           "lower"),
    ("DINOv2 image",        "image_similarity_dinov2.json",       ["best_assignment", "conditional_mean"],     "higher"),
    ("SigLIP-2 image",      "image_similarity_siglip2.json",      ["best_assignment", "conditional_mean"],     "higher"),
    ("Text-image (SigLIP)", "text_image_similarity_siglip2.json", ["render", "conditional_mean_of_view_mean"], "higher"),
    ("Uni3D 3D-3D",         "shape_uni3d.json",                   ["cos_3d_3d", "conditional_mean"],           "higher"),
]


def lookup(out, system, fname, path):
    f = out / "results" / system / "_metrics" / fname
    if not f.exists():
        return None
    v = json.loads(f.read_text())
    for key in path:
        v = v.get(key) if isinstance(v, dict) else None
    return v


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "work")
    scores = {}
    for label, fname, path, better in METRICS:
        scores[label] = {"better": better,
                         **{s: lookup(out, s, fname, path) for s in SYSTEMS}}

    judge_file = out / "llm_judge.json"
    if judge_file.exists():
        scores["LLM judge"] = json.loads(judge_file.read_text())

    (out / "scores.json").write_text(json.dumps(scores, indent=2) + "\n")

    def fmt(v):
        return "--" if v is None else f"{v:.4f}"

    print(f"\n{'Metric':<22}{'reference':>12}{'candidate':>12}{'noop_cube':>12}   better")
    for label, *_ in METRICS:
        row = scores[label]
        print(f"{label:<22}" + "".join(f"{fmt(row[s]):>12}" for s in SYSTEMS)
              + f"   {row['better']}")
    if "LLM judge" in scores:
        print(f"\nLLM judge ({scores['LLM judge']['judge']}):")
        for v in scores["LLM judge"]["verdicts"]:
            print(f"  A={v['A']:<10} B={v['B']:<10} -> {v['winner']}")
    print(f"\nWrote {out / 'scores.json'}")


if __name__ == "__main__":
    main()
