# Spec — `ma_gatekeeper/scripts/render_climax_plots.py`

**Status**: ready for [feature-build-loop](../../.claude/skills/feature-build-loop/SKILL.md) dispatch.
**Owner track**: product (`ma_gatekeeper/`). No design-team sign-off required (see Q8).
**Cross-references**: [demo_script.md L157](demo_script.md#L157), [reflector.py L461-870](../agent/reflector.py#L461), [calibrate.py L184](../scripts/calibrate.py#L184), [tokens.ts](../../design/tokens.ts), [PROJECT_LOG.md "Pre-commitments locked"](../../PROJECT_LOG.md), [devpost.md](devpost.md).

---

## 1. Goal & scope

A matplotlib (Agg) script that consumes the promotion-gate diagnostics emitted by a Reflector nightly run and renders a polished 2560×1440 PNG — the picture-in-picture visual that docks next to the live Phoenix Experiments view during the demo's climax beat (2:30–3:00, per [demo_script.md L157](demo_script.md#L157)). The PNG visualizes the paired-bootstrap CI promotion gate (`reflector.py:508 should_promote`). MP4 reveal animation is deferred to a follow-up issue; the script's API leaves an `output_mode="mp4"` shape in place that raises `NotImplementedError` for now.

**In scope**: PNG renderer, JSON input contract, mock fixtures (both PROMOTED and BLOCKED), test suite, font-bundling mitigation.
**Out of scope**: MP4 ffmpeg integration, motion choreography implementation, Phoenix MCP integration (the script reads JSON, not Phoenix), After-Effects compositing.

---

## 2. Open Question resolutions

| # | Question | Resolution | Owner |
|---|---|---|---|
| Q1 | PNG vs MP4? | **PNG primary; MP4 deferred** to follow-up issue. MP4 introduces ffmpeg as a build-time dep, encoder non-determinism (breaks byte-identity test), and a second test track. After Effects can author motion on top of the PNG cheaply. | Technical |
| Q2 | Input format? | **JSON file** matching `should_promote` diag shape + raw paired delta arrays. Log-line parsing rejected (format drift = silent breakage). Python API kept as the in-process test entry. | Technical |
| Q3 | One panel vs two? | **Two panels.** Single panel would force CI bar (delta-score axis) and ε distribution (frequency axis) to share an axis they don't share — honors "one thing to read per panel". | Visual |
| Q4 | PROMOTED affirmation placement? | **Figure-level pill in top-band negative space**, ~480px × 56px, `lane-clear` fill, rendered **only when the script's recomputed `should_promote` returns `True`** — gated on data, not on a CLI flag. | Visual + Honesty (joint) |
| Q5 | Mono-attribution footer content? | **Single mono line**: `reflector.py:461 paired_bootstrap_ci_lb \| :503 epsilon_fold5 \| :508 should_promote  ·  commit {git_sha_short}  ·  input {input_source}  ·  n_resamples={n_resamples}, alpha={alpha}, floor={floor}`. Overflow **aborts** (wrap/truncate are dishonest). | Honesty |
| Q6 | Fallback when gate fails? | **Render labeled "PROMOTION BLOCKED" variant; do not raise.** Script raises only on malformed input. Banner copy spells out which gate(s) failed; LB/ε/means stay visible; PROMOTED pill is absent. | Technical (behavior) + Honesty (content) |
| Q7 | MP4 reveal choreography? | **Specced for the follow-up issue** (3-beat reveal, 1600ms total, durations from `durationComponent`/`durationHero`). `durationMoneymomentSpan` explicitly forbidden. See §6.7. | Visual |
| Q8 | Design-team Supervisor escalation? | **No.** Product-track artifact (`ma_gatekeeper/scripts/`) consumed in After Effects, visualizing `reflector.py` output. Token references are one-way borrows; no landing-page surface impact. Token-level conflicts (§7) are filed separately as design-system gaps, not governance blockers. | Honesty |

---

## 3. CLI signature

```
python -m scripts.render_climax_plots \
  [--input PATH] [--out PATH] [--mode {png,mp4}] \
  [--use-mock / --no-use-mock] [--mock-variant {promoted,blocked}] \
  [--seed INT] [--dpi INT]
```

| Flag | Type | Default | Purpose |
|---|---|---|---|
| `--input` | Path | None | JSON file matching §4 contract. Required under `--no-use-mock`. Mutually exclusive with `--use-mock`. |
| `--out` | Path | `climax_plot.png` | Output file path. Parent dirs auto-created. |
| `--mode` | `{png,mp4}` | `png` | `mp4` raises `NotImplementedError` until the follow-up issue lands. |
| `--use-mock` | flag | `True` | Render deterministic mock fixture. Ignored when `--input` is set. |
| `--mock-variant` | `{promoted,blocked}` | `promoted` | Which mock fixture `--use-mock` emits. |
| `--seed` | int | `42` | Seeds numpy + matplotlib RNGs. |
| `--dpi` | int | `144` | Resolution. Floor enforced at `max(--dpi, 144)` to keep 2560×1440. |

Examples:
```bash
python -m scripts.render_climax_plots                                            # mock PROMOTED preview
python -m scripts.render_climax_plots --mock-variant blocked --out blocked.png   # mock fallback preview
python -m scripts.render_climax_plots --input nightly_diag.json --out climax.png # real Reflector run
```

---

## 4. Input contract (JSON)

```json
{
  "regression_ci_lb": 0.087,
  "epsilon_fold5": 0.041,
  "fold5_candidate_mean": 0.823,
  "fold5_production_mean": 0.804,
  "fold5_non_regression_ok": 1.0,
  "regression_gate_ok": 1.0,
  "regression_deltas": [0.12, -0.04, 0.18, 0.07, 0.09],
  "fold5_deltas":      [0.03,  0.01, 0.04, -0.02, 0.06],
  "candidate_version_id": "v_a1b2c3",
  "production_version_id": "v_9z8y7x",
  "source": "reflector.run_id=2026-05-26T03:00Z"
}
```

**Required keys**: the six `diag` fields ([`reflector.py:522-529`](../agent/reflector.py#L522)) plus the two delta arrays. Optional keys: `candidate_version_id`, `production_version_id`, `source` (rendered into the footer if present).

**Validation**:
- Missing required key → `KeyError("render_climax_plots: required input field 'X' missing")`.
- Empty delta array → `ValueError("render_climax_plots: 'regression_deltas' must be non-empty; got 0 entries")`.
- **Internal-consistency check**: the script imports `reflector.paired_bootstrap_ci_lb` / `reflector.epsilon_fold5` / `reflector.should_promote` and recomputes them on the input arrays; if the recomputed `diag` differs from the input `diag` on any field by `> 1e-9`, raise `ValueError("diag stale: field X input=… recomputed=…")`. Catches the "Hugo edited one field and forgot the array" bug.

Producer-side: Hugo emits this JSON by adding one `json.dump({**diag, "regression_deltas": reg_deltas.tolist(), "fold5_deltas": fold5_deltas.tolist(), "source": run_id}, fh)` line adjacent to [`reflector.py:851`](../agent/reflector.py#L851).

---

## 5. Output contract

- **Path**: as `--out`. Parent dirs auto-created.
- **Format**: PNG, RGBA, **2560×1440 minimum**, dpi `max(--dpi, 144)`.
- **Color profile**: sRGB (matplotlib default).
- **Determinism**: `metadata={"Software": None, "Creation Time": None}` passed to `fig.savefig` to strip timestamp-bearing PNG chunks. Seeded RNGs (`np.random.default_rng(seed)`, `matplotlib.rcParams["pdf.compression"] = 0` to avoid zlib non-determinism is unnecessary for PNG — PNG zlib is deterministic at a fixed compression level; pin via savefig `pil_kwargs={"optimize": False, "compress_level": 6}`).
- **savefig kwargs**: `bbox_inches="tight"`, `pad_inches=0.4`, `transparent=False`, `facecolor=fig.get_facecolor()`, `dpi=144` (or higher).

---

## 6. Visual Specification

### 6.1 Canvas

- **figsize**: `(17.78, 10.0)` inches → at **dpi=144** yields exactly **2560×1440 px** (After Effects 1440p clean).
- **Background**: `colors["neutral-900"]` → `#0B1311` ([tokens.ts L98](../../design/tokens.ts#L98)). Set `fig.patch.set_facecolor` AND every `ax.set_facecolor`. Matches the demo's lower-third scrim ([demo_script.md L110](demo_script.md#L110)).
- **Backend**: `matplotlib.use("Agg")` per [calibrate.py L204](../scripts/calibrate.py#L204) convention.

### 6.2 Panel layout

- `gridspec.GridSpec(1, 2, width_ratios=[1.0, 1.0])`.
- Outer margins: `left=0.06, right=0.96, top=0.82, bottom=0.16`. Top 18% reserved for figure-level Fraunces title + PROMOTED affirmation; bottom 16% for mono-attribution footer.
- Inter-panel spacing: `wspace=0.20` (≈ `spacing.10` 64px at 144dpi; [tokens.ts L203](../../design/tokens.ts#L203)).
- Each panel inset: `ax.margins(x=0.08, y=0.10)`. **Spines off** top/right always; left/bottom drawn at `colors["neutral-500-decorative"]` `#4A5F55` ([tokens.ts L94](../../design/tokens.ts#L94), linewidth 0.6). Ticks `neutral-400` `#7A8F83` ([tokens.ts L90](../../design/tokens.ts#L90)). No minor ticks. **Grid OFF**.

### 6.3 Panel A — Paired-bootstrap CI on regression set

- **Title**: `"Regression-set gate"` — Fraunces (`fontFamily.display`, [tokens.ts L148](../../design/tokens.ts#L148)), 32px (`fontSize.display-md`, L164), `colors["neutral-50"]` `#F4F6F3` (L86), weight 500, left-aligned.
- **Subtitle**: `"paired-bootstrap CI, 1000 resamples, α=0.05"` — Inter (`fontFamily.body`, L149), 16px (`fontSize.body`, L166), `colors["neutral-400"]`, weight 400, 12px (`spacing.3`, L198) below title.
- **X-axis**: paired delta accuracy (candidate − production). Range `[-0.02, +0.06]` fixed. Tick format `"{:+.2f}"`, JetBrains Mono (`fontFamily.mono`, L150) at 14px (`fontSize.small`, L175), color `neutral-400`. No y-axis label or ticks.
- **Plot element**: one **horizontal CI bar** via `ax.barh(y=0, width=ci_upper-ci_lb, left=ci_lb, height=0.30)`, fill `colors["text-interactive"]` `#4A9D7E` ([tokens.ts L67](../../design/tokens.ts#L67)) at alpha 0.85, edgecolor `text-interactive` alpha 1.0, linewidth 1.4. **Point estimate** as a 6-px vertical tick in `colors["neutral-50"]` inside the bar.
- **LB annotation**: `"LB = {lb:+.3f}"` (3 decimals), JetBrains Mono 24px (`fontSize.body-lg`, L165), `colors["lane-clear"]` `#4D936F` ([tokens.ts L109](../../design/tokens.ts#L109)), placed at `(ci_lb, 0.55)`, `ha="center"`. Thin 1-px leader in `neutral-500-decorative` from text to bar edge.
- **Zero reference line**: `ax.axvline(0, color=colors["accent-clay"], linewidth=1.2, linestyle="--", dashes=(4, 3), alpha=0.9)` ([tokens.ts L63](../../design/tokens.ts#L63)). Clay marks the gate threshold.
- **Sample-size annotation**: `"n_resamples = 1000  ·  n_regression = {N}"` in JetBrains Mono 14px `neutral-400`, bottom-left, 8px (`spacing.2`) above spine.

### 6.4 Panel B — fold-5 score-delta distribution

- **Title**: `"Frozen fold-5 non-regression"` — Fraunces 32px `neutral-50`.
- **Subtitle**: `"per-example score delta · ε non-regression band shaded"` — Inter 16px `neutral-400`.
- **Histogram**: `ax.hist(deltas, bins=20, range=(-0.10, +0.10))`. Fill `colors["neutral-500"]` `#8A9E94` ([tokens.ts L91](../../design/tokens.ts#L91)) at alpha 0.55; edgecolor `colors["neutral-300"]` `#A8B8AE` (L89), linewidth 0.8.
- **ε band**: `ax.axvspan(-epsilon, +epsilon, color=colors["lane-clear"], alpha=0.18, zorder=0)`.
- **ε label**: `"ε = {epsilon:.3f}"`, JetBrains Mono 24px `lane-clear`, top-center of the band at `(0, 0.95)` in axes-fraction coords.
- **Candidate / production means**: two short vertical tick marks at the top spine, JetBrains Mono 14px labels `"μ_cand"` (in `text-interactive`) and `"μ_prod"` (in `neutral-300`). No mean-line crossing the histogram body.
- **X-axis**: `"{:+.2f}"` JetBrains Mono 14px `neutral-400`. **Y-axis hidden** (frequency is shape, not number).
- **n annotation**: `"n_fold5 = {N}"` bottom-right, JetBrains Mono 14px `neutral-400`.

### 6.5 PROMOTED affirmation

- **Placement**: figure-level pill, centered horizontally, y=0.93. ~480px × 56px, `borderRadius.lg` 12px ([tokens.ts L257](../../design/tokens.ts#L257)). Drawn via `FancyBboxPatch` on `fig.add_axes(...)` with `boxstyle="round,pad=0.4,rounding_size=0.10"`.
- **Fill**: `colors["lane-clear"]` `#4D936F` ([tokens.ts L109](../../design/tokens.ts#L109)). **Text**: `"PROMOTED"`, JetBrains Mono 14px (`fontSize.mono-badge`, L168), letter-spacing tracked +0.08em (per-character `ax.text` calls — see §7 escalation), uppercase, color `colors["text-on-lane-clear"]` `#0B1311` (L81; verified 5.13:1).
- **Right of pill**, 16px gap (`spacing.4`): caption `"regression_gate_ok = True   ·   fold5_non_regression_ok = True"` in JetBrains Mono 14px `neutral-300` — proves the pill is wired to data.
- **Visibility logic** (load-bearing): the pill renders ONLY when the script's **recomputed** `should_promote(...)` returns `True` on the input deltas. Not on a CLI flag. Not on `diag["regression_gate_ok"]` alone. See [Honesty rule §8.1.3](#81-honest-numbers-compliance-rules).
- **Blocked variant**: when recomputation returns `False`, pill becomes `"PROMOTION BLOCKED"` in `colors["accent-clay"]` fill / `colors["text-on-accent-clay"]` text at the same coordinates. See §8.4 for textual content rules.

### 6.6 Mono-attribution footer (typography)

- **Placement**: bottom margin, figure y=0.04, left-aligned to left panel.
- **Font**: JetBrains Mono (L150). **Size**: 16px (`fontSize.mono-attribution`, L167). **Color**: `colors["neutral-500"]` `#8A9E94` (L91). **Max width**: 75ch (`containerMaxWidth.prose`, L232). **Line-height**: 1.4.
- Content owned by §8.3.

### 6.7 Motion sequence (deferred to MP4 follow-up issue)

Three-beat reveal, 1600ms total, easing `easePrimary` ([tokens.ts L266](../../design/tokens.ts#L266)) throughout. `durationMoneymomentSpan` (L298) **forbidden** — `@policy noreuse`.

1. **0 → 400ms** (`durationComponent`, L274): Panel A CI bar grows from `x=0` (anchored at the zero reference line, not from `ci_lb`) outward to its full `[ci_lb, ci_upper]` extent. LB annotation and sample-size annotation fade in.
2. **400 → 800ms** (`durationComponent`): Panel B histogram bars fade in left-to-right, 30ms per-bar stagger. ε band crossfades to alpha 0.18. ε label fades. μ ticks last.
3. **800 → 1600ms** (`durationHero`, L275): PROMOTED pill drops from y=0.95 → y=0.93, fade 0→1, scale 0.96→1.00. Boolean-flag caption fades 200ms after pill settles. Mono-attribution footer fades across the full hero window.

**Reduced-motion fallback**: the static PNG is itself the reduced-motion deliverable. State this in the script docstring.

---

## 7. Mock data shape

Two in-module fixtures, both built from `numpy.random.default_rng(42)`:

**`_MOCK_PROMOTED`** — exercises the PROMOTED path:
- `regression_deltas = rng.normal(0.09, 0.05, size=30)` → mean ~0.09, CI LB ~0.07 > 0.
- `fold5_deltas      = rng.normal(0.02, 0.04, size=20)` → ε ~0.04, μ_cand − μ_prod ~ +0.02.
- Both gates pass.

**`_MOCK_BLOCKED`** — exercises the fallback variant:
- `regression_deltas = rng.normal(-0.02, 0.06, size=30)` → CI LB < 0 → `regression_gate_ok=0.0`.
- `fold5_deltas      = rng.normal(-0.08, 0.05, size=20)` → `fold5_non_regression_ok=0.0`.

**Critical rule**: mock fixtures are deterministic **arrays**, not deterministic **numbers**. The script calls `paired_bootstrap_ci_lb`, `epsilon_fold5`, `should_promote` on the mock arrays and renders what they return. No hardcoded LB/ε literals. (See §8.1.4.)

Mock outputs land at `ma_gatekeeper/scripts/_mock_climax/{promoted,blocked}.png` — gitignored.

---

## 8. Procedural-Honesty Compliance

### 8.1 Honest-numbers compliance rules

1. Every number on the PNG traces to (a) a return value of a [`ma_gatekeeper/agent/reflector.py`](../agent/reflector.py) function invoked inside the script, or (b) an input-JSON field whose provenance is documented in the script docstring. No literals.
2. The script recomputes `should_promote(regression_deltas, fold5_candidate_scores, fold5_production_scores)` on input arrays and asserts the returned `diag` matches input `diag` across all six keys to within `1e-9`. Mismatch raises (see §4).
3. The PROMOTED pill renders iff `promote` from **recomputation** is `True` — not a `--promoted` flag, not `diag["regression_gate_ok"]` alone, not operator claim.
4. `--use-mock` is **deterministic-arrays**, not deterministic-numbers. Calls `paired_bootstrap_ci_lb`, `epsilon_fold5`, `should_promote` on mock arrays and renders the return values. Hardcoded outputs forbidden.
5. Echoed parameters (`n_resamples`, `alpha`, `floor`) are read from live kwarg defaults of the imported revision, not hardcoded in the footer template.
6. LB uses the alpha-th (5th) percentile, one-sided, per [`reflector.py:468-474`](../agent/reflector.py#L468). "97.5%" or "alpha/2" = regression to v1 bug; surfaces if seen.
7. No Phoenix UI affordance is depicted. The PNG is a matplotlib raster of `reflector.py` output; Phoenix Experiments ships results tables + comparison summaries, not custom paired-bootstrap CI plots ([demo_script.md L157](demo_script.md#L157) honest-framing).

### 8.2 Cross-deliverable consistency checklist

- [ ] [demo_script.md L157](demo_script.md#L157) — six `diag` keys in LEFT-pane log-line match keys the PNG renders.
- [ ] [demo_script.md L157](demo_script.md#L157) honest-framing — no custom Phoenix CI-bar visualization depicted.
- [ ] [demo_script.md L167](demo_script.md#L167) fallback row 3 — variant renderable from same entry-point + schema; blocked text unambiguous.
- [ ] [demo_script.md L179-189](demo_script.md#L179) — PNG silent about deal count.
- [ ] [devpost.md](devpost.md) Reflector pre-seeding — numbers consistent with weaker-production-seed + unchanged-loop-logic disclosure.
- [ ] [PROJECT_LOG.md](../../PROJECT_LOG.md) "Pre-commitments locked" — no number modifies the achieved Block-recall cluster-bootstrap 95% LB (headline statistic post Fix 10; Wilson LB retained only as exploratory per-finding-IID cross-check); this PNG is the promotion gate, not headline recall.
- [ ] [PROJECT_LOG.md](../../PROJECT_LOG.md) "What failed" (fabricated SDK signatures, contrast-lie) — cited line numbers verified at render time against the imported module via `inspect.getsourcelines` (see test #11).
- [ ] [design/tokens.ts](../../design/tokens.ts) — every color/font/size/easing/duration cited; any borrow is one-way (no token edits).

### 8.3 Mono-attribution footer content

Single mono line template:

```
reflector.py:461 paired_bootstrap_ci_lb | :503 epsilon_fold5 | :508 should_promote  ·  commit {git_sha_short}  ·  input {input_source}  ·  n_resamples={n_resamples}, alpha={alpha}, floor={floor}
```

- `{git_sha_short}` from `git rev-parse --short HEAD` captured at render time.
- `{input_source}` from JSON `source` field (e.g. `reflector.run_id=2026-05-26T03:00Z`, or `mock` for `--use-mock`).
- Parameters from live kwarg defaults of imported functions, not literals.

PROMOTED example: `reflector.py:461 paired_bootstrap_ci_lb | :503 epsilon_fold5 | :508 should_promote · commit fc5ccf4 · input reflector.run_id=2026-05-26T03:00Z · n_resamples=1000, alpha=0.05, floor=0.03`.

Fallback example: **identical footer** (audit trail is constant; pass/fail lives in the pill, not the footer).

**Overflow rule**: width = figure width − 2× outer margin, single line. If the rendered string exceeds available width, **abort** with `RuntimeError("attribution footer overflow at width=…px; refusing to truncate or wrap citations")`. Truncation hides references; wrapping breaks the freeze-frame scan.

### 8.4 Fallback variant content

Rendered when recomputed `should_promote` returns `False`:

- **"PROMOTED" appears nowhere.**
- Pill text in same slot: `"PROMOTION BLOCKED"` in `colors["accent-clay"]` fill.
- Mechanical reason text (mono caption right of pill), derived from booleans:
  - `regression_gate_ok == 0.0` → `"regression CI lower bound did not clear zero"`
  - `fold5_non_regression_ok == 0.0` → `"candidate regressed on frozen fold 5 beyond epsilon"`
  - both → joined by `" and "`.
- Numbers visible: `regression_ci_lb`, `epsilon_fold5`, `fold5_candidate_mean`, `fold5_production_mean` — the audit surface for WHY the gate blocked.
- Footer unchanged (§8.3).
- No color, glyph, or typography reads aesthetically similar to PROMOTED. A freeze-framing judge reads "blocked" in two seconds.

### 8.5 Failure patterns to actively avoid

1. **Fabricated SDK signatures** ([PROJECT_LOG.md](../../PROJECT_LOG.md) "What failed") — citing a `reflector.py` function or line that does not exist at the imported revision. Mitigation: test #11 asserts `inspect.getsourcelines` line numbers against cited values.
2. **Phoenix UI fabrication** (PROJECT_LOG.md Phase 6.5) — the PNG must never depict a Phoenix-shipped widget.
3. **Contrast-lie** — rendering a number with implied precision the computation does not support. Mitigation: 3-decimal precision is the bootstrap floor; no tighter formatting.
4. **Polish substitution** — replacing a real-but-ugly LB (e.g. 0.041) with a nicer literal (0.087). Mitigation: §8.1 rules 1, 2, 4.
5. **Static-badge PROMOTED** — keying the affirmation on a CLI flag or single boolean. Mitigation: §8.1 rule 3.

---

## 9. Module structure

```python
from pathlib import Path
from typing import Literal
import numpy as np

REQUIRED_DIAG_KEYS: tuple[str, ...] = (
    "regression_ci_lb", "epsilon_fold5",
    "fold5_candidate_mean", "fold5_production_mean",
    "fold5_non_regression_ok", "regression_gate_ok",
)
REQUIRED_ARRAY_KEYS: tuple[str, ...] = ("regression_deltas", "fold5_deltas")

def load_diag(path: Path) -> dict: ...
    # json.loads + key validation; raises KeyError / ValueError per §4.

def derive_mode(diag: dict) -> Literal["promoted", "blocked"]: ...
    # Reads regression_gate_ok + fold5_non_regression_ok; both 1.0 -> "promoted".

def render_promotion_gate_figure(
    diag: dict,
    regression_deltas: np.ndarray,
    fold5_deltas: np.ndarray,
    out_path: Path,
    *,
    output_mode: Literal["png", "mp4"] = "png",
    variant: Literal["promoted", "blocked"] | None = None,  # derived if None
    seed: int = 42,
    dpi: int = 144,
) -> Path: ...
    # matplotlib.use("Agg") at module top.
    # Seeds np + matplotlib RNGs.
    # Re-imports reflector.paired_bootstrap_ci_lb / epsilon_fold5 / should_promote.
    # Recomputes diag on arrays; raises on drift > 1e-9 (§4 internal-consistency).
    # Delegates panel composition to private _draw_panel_a / _draw_panel_b / _draw_pill / _draw_footer helpers.

def _mock_diag(variant: Literal["promoted", "blocked"]) -> tuple[dict, np.ndarray, np.ndarray]: ...

def main(argv: list[str] | None = None) -> int: ...
```

---

## 10. Test plan (`ma_gatekeeper/tests/test_render_climax_plots.py`)

Pattern: pure-Python; mock matplotlib's `savefig`; recorder-style assertions on figure structure, matching [test_calibration_invariants.py](../tests/test_calibration_invariants.py) `_AxRecorder` idiom.

1. **`test_render_promoted_mock_does_not_crash`** — `render_promotion_gate_figure(*_mock_diag("promoted"), tmp_path/"x.png")` returns without exception.
2. **`test_output_file_exists_and_nonempty`** — output PNG written, `stat().st_size > 10_000`.
3. **`test_label_text_correctness`** — recorder captures `ax.text` / `ax.set_title` calls; assert `"LB ="`, `"ε ="`, exact 3-decimal LB/ε strings match input.
4. **`test_color_uses_tokens_only`** — parse every hex string passed to matplotlib (`color=`, `facecolor=`, `edgecolor=` recorder kwargs) against the palette exported by [design/tokens.ts](../../design/tokens.ts); assert subset relation.
5. **`test_fail_gate_renders_blocked_variant`** — feed `_MOCK_BLOCKED`; assert `derive_mode` returns `"blocked"` AND the recorder captures `"PROMOTION BLOCKED"` text AND NOT `"PROMOTED"` (substring + boundary check, not lax `in`).
6. **`test_byte_identical_on_rerun`** — render twice to two temp paths with identical inputs; `Path(a).read_bytes() == Path(b).read_bytes()`. Pins determinism (no Creation Time, no Software metadata, seeded RNGs).
7. **`test_raises_on_missing_required_key`** — JSON fixture missing `regression_ci_lb` → `KeyError`.
8. **`test_raises_on_empty_delta_array`** — `regression_deltas=[]` → `ValueError`.
9. **`test_diag_internal_consistency`** — JSON where `regression_ci_lb` disagrees with `paired_bootstrap_ci_lb(regression_deltas)` by >1e-9 → `ValueError` (catches stale-diag bug from §4).
10. **`test_mp4_mode_raises_not_implemented`** — pins the deferred contract.
11. **`test_cited_line_numbers_resolve_to_named_functions`** — `inspect.getsourcelines(reflector.paired_bootstrap_ci_lb)[1]` equals the line cited in the footer template (461); same for `epsilon_fold5` (503) and `should_promote` (508). Surfaces silent reflector.py refactors that would otherwise leave fabricated line citations on screen.
12. **`test_footer_overflow_aborts`** — supply a `source` field long enough to overflow the 75ch budget; assert `RuntimeError` with "footer overflow" in message.

---

## 11. Risks + mitigations

- **(a) Fraunces font missing on rendering host.** Bundle `Fraunces-VariableFont.ttf` under `ma_gatekeeper/scripts/fonts/` and register via `matplotlib.font_manager.fontManager.addfont(...)` at module import. If the font file is absent, fall back to matplotlib's `DejaVu Serif` (deterministic across hosts) with `_LOG.warning`. Test by deleting the font file in CI fixtures and asserting the warning fires. **License**: Fraunces is SIL OFL — compatible with project Apache 2.0.
- **(b) ffmpeg missing for MP4.** Out of scope today; `--mode mp4` raises `NotImplementedError` with a remediation message naming the follow-up issue.
- **(c) matplotlib version drift.** `requirements.txt` pins `matplotlib>=3.8.0`. Byte-identity test #6 catches encoder change across minor versions in CI; remediation = add `==3.8.x` pin and surface in PROJECT_LOG.
- **(d) numpy RNG seed determinism across versions.** `np.random.default_rng(seed)` uses PCG64 (stable BitGenerator algorithm), but per [numpy's compatibility policy](https://numpy.org/doc/stable/reference/random/compatibility.html) the default `BitGenerator` and `Generator.normal` algorithm are explicitly allowed to change across major releases. **Stream stability is guaranteed for same-build only**, not cross-version. Test #6 (byte-identity) verifies same-process / same-build determinism — that's what it tests, and that's all it claims. If a numpy upgrade ships a stream change, test #6 fires loudly in CI; remediation = pin numpy to the previously-verified range and surface the drift in [PROJECT_LOG.md](../../PROJECT_LOG.md). Recommended pin (post-Round 1 WebFetch verification): `numpy>=1.25.0,<3.0` — the project should evaluate moving from the current `numpy>=1.25.0` to this narrower range as a separate cross-cutting decision (out of scope for this script's build loop).
- **(e) matplotlib letter-spacing for PROMOTED pill (`+0.08em` tracking).** matplotlib's text engine has no per-string tracking. Mitigation: render PROMOTED via per-character `ax.text` calls with manual kerning offset. Surface to design-team if visual-fidelity drift on the smaller boolean-flag caption is unacceptable; current spec accepts the drift on the smaller caption (rendered as a single string).

---

## 12. Open Conflicts (token-level escalations to [design-team](../../.claude/skills/design-team/SKILL.md), filed separately from Q8 governance)

These do not block build-loop dispatch but should be resolved before the design system reaches v1.0:

- **`[escalation]` JetBrains Mono `+0.08em` tracking in matplotlib.** Per-character rendering ships for the PROMOTED word; boolean-flag caption accepts the drift. Flag whether a bundled SVG composite for the pill is preferred long-term.
- **`[escalation]` Fraunces system-installation fallback.** Spec ships bundled font + addfont() registration; if bundling is rejected on binary-size grounds, fall back to Inter for panel titles (still token-legal — `fontFamily.body` is not display-locked).
- **`[escalation]` No matplotlib-native token for thin gridlines.** Grid OFF per spec, but if Builder discovers Panel B histogram needs y-gridlines for scrub-speed readability, no `<4.5:1 chrome contrast for 1px gridlines on neutral-900` token exists. Candidate: `neutral-500-decorative` `#4A5F55` at alpha 0.30. Escalate for a `chart-grid` token, or confirm gridlines remain OFF.
- **`[escalation]` No `chart-error-state` color token.** Fallback "PROMOTION BLOCKED" pill reuses `accent-clay` — same hue as Block-lane verdict badge. Risk: Phoenix freeze-framer conflates "promotion blocked" with "Block lane finding." Surface whether a `gate-not-cleared` semantic alias should ship or whether contextual subtitle + PROMOTED-absent state already disambiguates.

---

## 13. Build-loop dispatch hint

Recommended [feature-build-loop](../../.claude/skills/feature-build-loop/SKILL.md) configuration:

- **Builder cohort**: 2 builders, matplotlib + numpy expertise. Each receives this spec as the canonical brief.
- **Reviewer cohort** (required, parallel):
  - **Goal-alignment** — does the PNG visually deliver the climax wow-effect specified in §2 / §6?
  - **Code-quality** — module structure (§9), type hints, sibling-script idiom match against [calibrate.py](../scripts/calibrate.py) / [eval_maud_mcq.py](../scripts/eval_maud_mcq.py).
  - **Bug-hunter** — focuses on edge cases: empty arrays, NaN inputs, malformed JSON, stale-diag, footer overflow, font-fallback path.
- **Reviewer cohort** (recommended, parallel):
  - **WebFetch reviewer** — verify matplotlib `font_manager.addfont`, `savefig(metadata={...})`, `FancyBboxPatch` API against current docs (matplotlib ≥3.8.0). Catches silently-deprecated kwargs.
  - **Procedural-Honesty reviewer** — scans diff against §8 rules: no hardcoded numbers, recomputation is wired, footer template is data-driven, blocked variant cannot be mistaken for PROMOTED, line citations match `inspect.getsourcelines`.
- **NOT required**: design-team Art Director sign-off. Per Q8, this is a product-track artifact; the Visual section (§6) is canonical and traces to [tokens.ts](../../design/tokens.ts). Token-level open conflicts in §12 are filed as parallel design-system issues, not build blockers.

**Exit criteria for build-loop convergence**: all 12 tests pass; all required reviewers return GO; the `_MOCK_PROMOTED` and `_MOCK_BLOCKED` outputs are saved under `ma_gatekeeper/scripts/_mock_climax/` and visually inspected by Hugo before merge.
