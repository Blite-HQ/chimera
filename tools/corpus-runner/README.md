# chimera-eval — the corpus runner (third plane)

Offline, aggregate evaluation. **Not** verification, **not** a guardrail — see
[`docs/tres-planos.md`](../../docs/tres-planos.md).

Shape borrowed from [Inspect](https://inspect.aisi.org.uk/) (UK AISI, MIT):
`Dataset → Task → Solver → Scorer`, plus its `C/I/P/N` scoring vocabulary. The
form is ported, the dependency is not — the reasoning is in
`knowledge/trust/17-evaluacion-inspect-tres-planos.md` §1.2.

Two things this adds on top of that shape:

- a **`config_digest`**, so two runs of the same evaluation are provably the
  same evaluation (Inspect captures `revision` and `packages`, but no digest);
- **no clock in the log**, so two identical runs produce byte-identical output
  and an ablation is a `diff`, not a reading exercise.

And one rule that is this codebase's own: a **process failure is not a verdict**.
If a solver or scorer raises, the sample is reported as an error and left out of
the rates — counting it as `I` would invent a mistake, and counting it as `N`
would invent an abstention.

## Run it

```bash
uv run python scripts/run_eval_corpus.py
```

Writes an `EvalLog` under `results/eval/` and prints the KPIs:

| KPI                   | reads as                                                  |
| --------------------- | --------------------------------------------------------- |
| `accuracy`            | mean score — **cannot** tell a mistake from an abstention |
| `over_refusal_rate`   | `count(N)/scored` — the system abstained: costs utility   |
| `decisive_error_rate` | `count(I)/scored` — the system committed and was wrong    |
| `process_errors`      | samples that could not be measured at all                 |

## Layout

- `chimera_eval.dataset` · `Sample`/`Dataset` with **structured** targets (a
  graph partition is not a string).
- `chimera_eval.score` · `C/I/P/N` and the rates.
- `chimera_eval.task` · what to evaluate; `solver`/`scorer` are injected.
- `chimera_eval.runner` · execution + `EvalLog`.
- `chimera_eval.tasks.*` · the only place that imports the verification plane.

The core imports neither `blite` nor `chimera_api`; an import-linter contract
(`O8: evaluation is downstream`) keeps the arrow pointing one way.
