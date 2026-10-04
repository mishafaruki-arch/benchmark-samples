# CAD: parametric part modeling in FreeCAD

A coding agent gets a text spec of a mechanical part and must write a
**FreeCAD 1.1 Python script** that builds it as an editable PartDesign
feature tree, then run it to save the model. A separate verifier scores the
saved model against a held-back reference. **Bring your own agent and model.**

Tasks use the [Harbor](https://pypi.org/project/harbor/) format and the
[gnucleus-freecad-validator](https://github.com/gNucleus-AI/freecad-validator)
scorer.

```
cad/
├── run_model.sh             run any agent + model on a task and score it
├── tasks/flanged-bushing/   the task (Harbor format)
├── build/                   scripts that built and cross-check the reference
└── runs/                    oracle and no-op runs that validate the verifier
```

## Quick start

Needs Docker and [uv](https://docs.astral.sh/uv/). The first run builds the
task images (FreeCAD via conda, several minutes); later runs reuse them.

```bash
cd cad

# 1. Check the verifier on your machine
./run_model.sh oracle      # copies the reference: should score 1.0
./run_model.sh nop         # does nothing:         should score 0.0

# 2. Test a model: ./run_model.sh <agent> <provider/model>
export OPENAI_API_KEY=...            # or ANTHROPIC_API_KEY, etc., or put them in cad/.env
./run_model.sh codex openai/<model>
./run_model.sh claude-code anthropic/<model>
```

`<agent>` is any agent Harbor supports (`codex`, `claude-code`, `aider`,
`gemini-cli`, …; see `uvx --from harbor==0.23.0 harbor run --help`). Extra
arguments after the model go straight to `harbor run`.

Each run prints:

1. **The verifier's score breakdown**: reward, geometry similarity, spec
   consistency, and the reasons.
2. **An independent overlap check**: the volume inside one solid but not the
   other, compared to the reference (0 mm³ = identical).

Full results land in `jobs/<agent>-<model>-<task>-<time>/` (git-ignored):
the agent's `answer.py` and `answer.FCStd` under `artifacts/app/`, verifier
output under `verifier/`, and the agent's logs under `agent/`.

`run_model.sh` was tested end to end with the oracle, the no-op, and a real
Codex agent.

## The task: `flanged-bushing`

A circular flange with a coaxial sleeve and a plain through bore:
flange 50 mm × 6 mm, sleeve 30 mm × 24 mm, bore 20 mm, overall length 30 mm.

| File | Role | Seen by the agent? |
|---|---|---|
| `instruction.md` | The prompt: part description, 6 key parameters, output contract (`/app/answer.py` + `/app/answer.FCStd`, one PartDesign Body, editable features, path from `__file__`) | Yes |
| `task.toml` | Harbor config: artifacts to collect, timeouts (agent 9000 s, verifier 600 s), resources, separate verifier environment | No |
| `environment/Dockerfile` | Agent image: FreeCAD 1.1.0, Python 3.12, numpy, scipy. No grader or reference inside. | It runs inside it |
| `tests/Dockerfile` | Verifier image: same runtime + `gnucleus-freecad-validator==0.4.0`, with the reference baked in at `/opt/grader` | No |
| `tests/test.sh` | Verifier entry point: checks `/app/answer.FCStd` exists and isn't a symlink, stages it privately, runs the scorer, writes the reward | No |
| `tests/run_scorer.py` | Calls `Validator().validate()` and writes `reward.txt`, `reward.json`, and a `reward_details.json` sidecar | No |
| `tests/grader/reference.FCStd` | The answer key | No |
| `tests/grader/spec.json` | The description + key parameters, for the spec-consistency check | No |
| `tests/grader/param_check.py` | Per-task parameter logic (a stub here: the generic checks are enough) | No |
| `solution/solve.sh` + `reference.FCStd` | Oracle: copies the reference to the answer path, to test the verifier alone | No |
| `*/LICENSES/` | LGPL-2.1, Apache-2.0, and third-party notices for the FreeCAD runtime in the images | — |

### Build scripts (`build/`)

| Script | What it does |
|---|---|
| `make_reference.py` | Builds the reference as a PartDesign Body: flange pad → sleeve pad → through-all bore pocket. Prints solid count, validity, volume, area and bounding box, then saves to `$OUT` (default `/out/reference.FCStd`). |
| `overlap.py` | Independent check outside the validator: the volume that differs between `$REF` and `$CAND` (`ref − cand` + `cand − ref`). 0 means identical solids. `run_model.sh` runs it automatically. |

To rebuild the reference yourself, use any image with `freecadcmd` 1.1.0, for
example the one `run_model.sh` builds:

```bash
docker run --rm -v "$PWD/build:/build:ro" -v "$PWD/out:/out" \
    cad-bench-flanged-bushing-env freecadcmd /build/make_reference.py
# SOLIDS 1 VALID True
# VOLUME 19320.7948 AREA 8388.0524
# BBOX 50.000 x 50.000 x 30.000
```

## How it's graded

The reward is a score in [0, 1]: the **harmonic mean** of two axes, so a
candidate must do well on both.

| Axis | What it grades |
|---|---|
| Geometry similarity | Candidate vs. reference: solid count, surface types, volume, surface area and bounding box, each compared as a % difference |
| CAD spec consistency | Whether each key parameter in `spec.json` can be found and is consistent in the candidate's model (6 for this task) |

Before scoring, `test.sh` gives 0 with a reason if there's no
`answer.FCStd` (and says whether `answer.py` was written but never run) or if
it's a symlink. The scorer itself crashing also gives 0.

## Verifier validation (`runs/`)

These runs aren't model results. They check that the verifier gives full marks
to a correct answer and nothing to an empty one.

| Run | What it does | Reward | Verifier detail |
|---|---|---|---|
| `runs/oracle/` | Copies the reference to the answer path | **1.000** | Geometry 1.000, spec 1.000 (6/6 consistent) |
| `runs/nop/` | Does nothing | **0.000** | "candidate did not produce /app/answer.FCStd (no answer.py at /app/)" |

Each folder has `verifier/` (reward + details), `result.json` (Harbor's trial
record) and `harbor-summary.log`. The oracle folder also has the answer files
it submitted.

## Known gaps

- **The no-op only covers "wrote nothing."** No probe yet checks that a
  wrong-but-valid part (e.g. missing bore, wrong sleeve length) scores
  meaningfully below 1.0. That would test the verifier for false positives.
- **This is an easy part.** Three features, all axis-aligned. A full score
  says the pipeline works, not that it separates strong models from weak ones.
- `LICENSES/NOTICES.freecad-1.1-runtime.md` names validator version 0.1.3,
  but `tests/Dockerfile` installs 0.4.0.
- `task.toml` sets `allow_internet = true` for the agent environment.
