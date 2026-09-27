# Adhikaar Eligibility Dataset — v1

An **auditable, clause-cited dataset of Indian welfare-scheme eligibility rules**,
plus a hand-labeled persona set for evaluating eligibility systems. Every rule
carries the verbatim official text it encodes and a link to its government source.

**License:** [CC BY 4.0](LICENSE) · **Datasheet:** [DATASHEET.md](DATASHEET.md) ·
**Integrity:** [manifest.json](manifest.json) (counts + SHA-256 per file)

## What's inside

| File | Description |
|------|-------------|
| `rules.jsonl` | One row per eligibility rule: condition tree + **verbatim `clause`** + `source_url`. |
| `schemes.jsonl` | One row per scheme: names, version, rule counts, declared `simplifications`. |
| `personas.jsonl` | 56 labeled household personas (`train`/`heldout`) with gold verdicts. |
| `schema.json` | Field-by-field documentation for the three data files. |
| `eval_report.json` | Reproducible headline metrics: deterministic rules engine vs LLM baseline. |
| `manifest.json` | Version, source commit, per-file hashes and counts. |

## Quickstart

```python
import json

rules   = [json.loads(l) for l in open("rules.jsonl",    encoding="utf-8")]
schemes = [json.loads(l) for l in open("schemes.jsonl",  encoding="utf-8")]
people  = [json.loads(l) for l in open("personas.jsonl", encoding="utf-8")]

# Every rule is grounded in official text you can verify:
r = rules[0]
print(r["clause"], "->", r["source_url"])

# Personas carry expert gold labels; 'need_info' means "correctly abstain":
p = people[0]
print(p["message"], p["gold"])
```

## The headline

On 92 labeled (persona, scheme) pairs, the deterministic rules engine scores
**91.3% accuracy with 0 false positives**, versus **54.35% with 14 false positives**
for an LLM baseline. It never invents an entitlement — gaps surface as abstentions.
Full numbers and the reproduction command are in [`eval_report.json`](eval_report.json);
the methodology is in [`DATASHEET.md`](DATASHEET.md).

## Rebuild / verify

```bash
python scripts/build_dataset.py          # regenerate this bundle from the repo
```

`manifest.json` records a SHA-256 for every file, so a rebuild that changes any
content is immediately visible in the diff.

## Citation

> Adhikaar Eligibility Dataset v1 (CC BY 4.0), Adhikaar contributors, 2026.

⚠️ Not a substitute for official determination. Rules are simplified (see each
scheme's `simplifications`) and government text can change — always verify against
the cited `source_url`.
