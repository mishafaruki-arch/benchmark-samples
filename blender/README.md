# Blender: procedural 3D modeling via code

A model gets a text description of an object and must reply with a
self-contained **Blender 5.0 Python script** that builds it. The script is
executed headless, rendered from 4 fixed cameras, exported as a mesh, and
scored against a hidden reference script.

The task format and scorers follow
[3DCodeBench](https://github.com/gaoypeng/3dcodebench) ([paper](https://arxiv.org/abs/2606.01057)).
This folder adds a new task that is **not** one of 3DCodeBench's 212 categories,
plus scripts for oracle / no-op calibration and an OpenAI-based judge.

```
blender/
├── tasks/Teapot_seed0/        the task (input + answer key)
├── eval/                      evaluation scripts
└── sample_run/                one GPT-5.5 attempt, fully scored
```

## The task: `Teapot_seed0`

| File | Role | Seen by the model? |
|---|---|---|
| `prompt_description.txt` | One-paragraph caption. The default prompt. | Yes |
| `prompt_instruction.txt` | One-sentence build instruction. Alternative prompt. | Yes, if selected |
| `Teapot_seed0.py` | Reference script (answer key). Builds a spun body with foot ring and rolled rim, a domed lid with turned knob, a tapering spout with flared tip, and an oval loop handle. 7 proportions are sampled from seed 0. | **No** |

The model also gets 3DCodeBench's system prompt
(`prompts/text_to_3d_system_prompt.txt`): reply with only Python, Blender 5.0
API, an import whitelist, object at the origin, no ground plane, untextured.

**Reference script checks** (3DCodeBench's `CONTRIBUTING.md` rules):

- Runs headless in Blender 5.0 in ~0.2 s (limit: 5 min).
- Imports only `bpy`, `bmesh`, `mathutils` and the standard library.
- Deterministic: two runs give the same vertex hash (`eval/mesh_hash.py`).
- No file or network access; produces 4 meshes.
- Caption matches the reference: a first judge pass showed the caption promised
  a foot ring the reference barely had, so the reference was fixed.

## Evaluation

`eval/run_eval.sh` scores a candidate script, and scores the **reference**
(oracle: should score near the top) and a **unit cube** (no-op: runs cleanly
but is wrong, so it should score near the bottom) alongside it as calibration.

| Verifier | What it grades | Better |
|---|---|---|
| Executability | Runs in Blender 5.0 with no exception, produces ≥1 mesh, renders 4 views | pass |
| Chamfer distance | 3D surface distance to the reference, after normalizing size and trying 4 rotations | lower |
| DINOv2 image | Embedding similarity of the 4 renders to the reference renders (views re-paired to absorb rotation) | higher |
| SigLIP-2 image | Same, with SigLIP-2 | higher |
| Text-image | SigLIP-2 similarity of the renders to the prompt text | higher |
| Uni3D 3D-3D | Learned 3D-shape embedding similarity to the reference mesh | higher |
| LLM judge | Pairwise verdict on renders using 3DCodeBench's `image_judge.txt` rubric, judged in both A/B orders | wins |

| Script | Purpose |
|---|---|
| `eval/run_eval.sh` | Runs everything above for one task + one candidate |
| `eval/summarize.py` | Collects the scorers' JSON into one table and `scores.json` |
| `eval/openai_judge.py` | 3DCodeBench's judge rubric sent to an OpenAI model (the original only calls Gemini) |
| `eval/noop_cube.py` | The no-op baseline |
| `eval/mesh_hash.py` | Determinism check for reference scripts |

### Setup

```bash
git clone https://github.com/gaoypeng/3dcodebench.git
pip install -r 3dcodebench/requirements.txt torch transformers trimesh scipy
# Optional, for Uni3D: open_clip_torch timm + a clone of github.com/baaivision/Uni3D

export BENCH_ROOT=$PWD/3dcodebench
export BLENDER=/path/to/blender-5.0/blender     # must be 5.0.x
export DEVICE=cpu                               # or mps (Apple GPU) / cuda
export UNI3D_REPO=/path/to/Uni3D                # optional
export OPENAI_API_KEY=...                       # optional, enables the judge
```

### Run

```bash
cd blender
eval/run_eval.sh tasks/Teapot_seed0 sample_run/gpt-5.5/Teapot_seed0.py work
```

To generate a new candidate, copy `tasks/Teapot_seed0/` into
`3dcodebench/benchmark/categories/` and run its `tasks/text_to_3d/run.py`.

## Sample run: GPT-5.5

`sample_run/` holds one single-shot attempt: the prompt sent, the generated
script, the run log (cost $0.29, valid Python on the first try), renders of the
output and of the reference, `compare.png` (reference on top, GPT-5.5 below),
and `scores.json`.

| Verifier | Reference | GPT-5.5 | Cube |
|---|---|---|---|
| Executability | pass | pass | pass |
| Chamfer (lower) | 0.0005 | 0.0035 | 0.1319 |
| DINOv2 image | 1.000 | 0.940 | 0.234 |
| SigLIP-2 image | 1.000 | 0.934 | 0.756 |
| Text-image | 0.200 | 0.212 | 0.057 |
| Uni3D 3D-3D | 0.996 | 0.843 | -0.018 |
| Judge vs. reference | | 1-1 split | |
| Judge vs. cube | | won 2/2 | |

Chamfer and Uni3D sample random surface points, so re-runs vary slightly.

### What the calibration shows

- **Executability passes the cube.** It catches crashes, not wrong objects.
- **SigLIP-2 image similarity has a narrow range:** the cube still scores 0.76.
  DINOv2, Chamfer and Uni3D separate the three far more clearly.
- **The judge flips with A/B order** on GPT-5.5 vs. the reference: either
  position bias or a genuine tie. Both teapots fit the caption, and a
  text-to-3D caption can't pin down every proportion of one specific reference.
- No graded verifier has a pass threshold; scores are only meaningful relative
  to the oracle and no-op rows.
