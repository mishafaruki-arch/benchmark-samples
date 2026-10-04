"""Pairwise LLM judge over rendered views, using 3DCodeBench's rubric via OpenAI.

3DCodeBench's own judge (metrics/llm_judge/judge.py) only calls Gemini. This
sends the same rubric (metrics/llm_judge/prompts/image_judge.txt) to an OpenAI
model instead. Every pair is judged in both A/B orders, so a verdict that flips
with the order shows up as position bias or a tie rather than a win.

    python eval/openai_judge.py --bench-root ../3dcodebench \
        --results-root work/results --instance Teapot_seed0 \
        --pair candidate reference --pair candidate noop_cube

Needs OPENAI_API_KEY in the environment.
"""
import argparse
import base64
import json
from pathlib import Path

from openai import OpenAI

VIEWS = ["Image_005.png", "Image_015.png", "Image_025.png", "Image_035.png"]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bench-root", type=Path, required=True,
                   help="Path to a 3DCodeBench clone (for the judge rubric).")
    p.add_argument("--results-root", type=Path, required=True,
                   help="Holds <system>/<instance>/renders/Image_0*.png and prompt.txt.")
    p.add_argument("--instance", required=True)
    p.add_argument("--pair", nargs=2, action="append", required=True,
                   metavar=("SYSTEM_A", "SYSTEM_B"))
    p.add_argument("--judge", default="gpt-5.4")
    p.add_argument("--effort", default="medium")
    p.add_argument("--out", type=Path, default=None)
    return p.parse_args()


def image_parts(results_root, system, instance):
    d = results_root / system / instance / "renders"
    return [{"type": "image_url",
             "image_url": {"url": "data:image/png;base64,"
                           + base64.b64encode((d / v).read_bytes()).decode()}}
            for v in VIEWS]


def parse_verdict(text):
    text = text.strip().strip("`").strip()
    if text.startswith("json"):
        text = text[4:]
    return json.loads(text)


def judge(client, args, rubric, prompt, a, b):
    content = [
        {"type": "text", "text": "--- ORIGINAL PROMPT ---\n" + prompt},
        {"type": "text", "text": "\n--- SYSTEM A: 4 renders ---"},
        *image_parts(args.results_root, a, args.instance),
        {"type": "text", "text": "\n--- SYSTEM B: 4 renders ---"},
        *image_parts(args.results_root, b, args.instance),
        {"type": "text", "text": "\nReturn the JSON verdict now."},
    ]
    resp = client.chat.completions.create(
        model=args.judge, reasoning_effort=args.effort,
        messages=[{"role": "system", "content": rubric},
                  {"role": "user", "content": content}])
    return parse_verdict(resp.choices[0].message.content)


def main():
    args = parse_args()
    rubric = (args.bench_root / "metrics/llm_judge/prompts/image_judge.txt").read_text()
    client = OpenAI()

    results = []
    for x, y in args.pair:
        prompt = (args.results_root / x / args.instance / "prompt.txt").read_text().strip()
        for a, b in [(x, y), (y, x)]:
            v = judge(client, args, rubric, prompt, a, b)
            winner = {"a": a, "b": b}.get(v["winner"], v["winner"])
            results.append({"A": a, "B": b, "winner": winner,
                            "reasoning": v["reasoning"]})
            print(f"A={a:<12} B={b:<12} -> {winner}\n    {v['reasoning']}")

    out = args.out or args.results_root.parent / "llm_judge.json"
    out.write_text(json.dumps({"judge": args.judge, "instance": args.instance,
                               "verdicts": results}, indent=2) + "\n")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
