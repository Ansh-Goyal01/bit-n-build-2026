# Datasheet — Adhikaar Eligibility Dataset v1

Following the *Datasheets for Datasets* framework (Gebru et al., 2021). This
dataset packages the rule encodings and labeled evaluation personas behind
[Adhikaar](../../README.md), an auditable eligibility checker for Indian welfare
schemes.

**License:** CC BY 4.0 (see [`LICENSE`](LICENSE)). **Version:** v1.
**Machine-readable manifest with counts + content hashes:** [`manifest.json`](manifest.json).

---

## Motivation

**Why was this dataset created?** Public benefit portals answer *"which schemes am
I eligible for?"* with either static lists or, increasingly, LLMs that hallucinate
entitlements. We built the eligibility logic as **data, not code or prompts** — each
scheme rule is one clause of official government text made executable, with the
verbatim clause and its source URL attached. This dataset publishes that rule base
plus a hand-labeled persona set so the accuracy and determinism claims are
independently checkable rather than asserted.

**Who created it?** The Adhikaar contributors, as a student project.

---

## Composition

Three files (plus `schema.json` documenting every field, `eval_report.json`, and a
hash-pinned `manifest.json`):

| File | Rows | What each row is |
|------|------|------------------|
| `rules.jsonl` | see manifest | One eligibility rule: a `require`/`exclude` condition tree over typed household facts, with the **verbatim official `clause`** it encodes and the exact `source_url`. |
| `schemes.jsonl` | see manifest | One scheme: id, names, version, rule counts, and **`simplifications`** — honestly declared criteria in the official text not yet encoded. |
| `personas.jsonl` | 56 | One hand-written household description with **gold** verdicts (`eligible` / `not_eligible` / `need_info`) per scheme. |

**Instances.** Rules are executable encodings of scheme text. Personas are
free-text household descriptions phrased as a user would, each with expert labels.

**Labels.** Persona `gold` was assigned by reading each scheme's official
eligibility and exclusion text against the household facts. `need_info` marks
personas where the description genuinely under-determines a verdict — abstention is
a *correct* label, not a failure.

**Splits.** `personas.jsonl` carries a `split` field: `train` (41) and `heldout`
(15). The held-out set was written once and **withheld during rule development** to
guard against overfitting the rules to known cases.

**Is anything missing?** Yes, and it is recorded, not hidden. Each scheme's
`simplifications` list names criteria present in the official text that the rules do
not yet model (e.g. institutional-landholder exclusions, edge boundary conditions).
This is deliberate: the dataset optimizes for **never overclaiming**, so unencoded
criteria surface as abstentions rather than false grants.

**Sensitive data.** None. Personas are synthetic, authored to span realistic
household situations (widowhood, BPL status, occupation, landholding, disability).
No real individuals are described and no personally identifying information is
present.

---

## Collection & Preprocessing

**Rule source.** Scheme eligibility text was read from official Government of India
sources — primarily `myscheme.gov.in` and the circulars it links. Each rule stores
the exact `source_url`. A separate freshness monitor re-fetches those sources and
diffs them against the committed corpus, so drift in the official text is detectable.

**Encoding process.** Each clause was translated by hand into a typed condition over
a fixed household-fact schema, then unit-tested. Rules carry a `review_status`:
`encoded` (machine-encoded + unit-tested) or `verified` (a human read the rule beside
its source clause and certified it).

**Build.** This bundle is a deterministic projection produced by
[`scripts/build_dataset.py`](../../scripts/build_dataset.py) from the repository's
rule files and eval sets — it invents nothing. `manifest.json` records the source
git commit and a SHA-256 of every file.

---

## Evaluation & Recommended Uses

`eval_report.json` carries the headline numbers. On the labeled pairs:

| | Deterministic rules engine | LLM baseline |
|---|---|---|
| Accuracy | **91.3%** | 54.35% |
| **False positives (overclaimed entitlements)** | **0** | 14 |
| False negatives | 0 | 14 |
| Determinism | same input → same output | none |

**The claim this dataset supports** is not "100% accurate" — it is **zero false
positives with full determinism, every verdict backed by verbatim official clause
text.** Remaining gaps show up as *abstentions* (`need_info`), never as invented
eligibility. The `rules`-phase eligibility numbers are **reproducible offline** (no
LLM in the verdict path); faithfulness and the LLM baseline require an LLM judge and
are reported as measured. See `eval_report.json` for the reproduction command.

**Intended uses.** Benchmarking eligibility/verdict systems; training or evaluating
rule-extraction and clause-grounding models; research on abstention and
anti-hallucination in high-stakes advisory settings; a reusable corpus of
clause-cited welfare rules.

**Out-of-scope / cautions.** This is **not** a substitute for official
determination. Rules are simplified (see each scheme's `simplifications`) and the
underlying government text can change — always verify against the cited
`source_url`. Do not use `likely_eligible`/`eligible` outputs to deny or grant real
benefits.

---

## Distribution & Maintenance

**Distribution.** Published in-repo under CC BY 4.0. Redistribution must preserve
attribution and the provenance note in `LICENSE`.

**Maintenance.** The dataset is regenerated from the live rule repository by the
build script; `manifest.json` (git commit + file hashes) pins each release.
Corrections flow by fixing the underlying rule file and rebuilding. Scheme text
drift is surfaced by the repository's freshness monitor.

**Citation.**
> Adhikaar Eligibility Dataset v1 (CC BY 4.0), Adhikaar contributors, 2026.
