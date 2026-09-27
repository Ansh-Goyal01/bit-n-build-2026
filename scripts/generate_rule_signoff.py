"""Generate the per-rule human sign-off checklist in the Obsidian vault.

The vault page is a generated VIEW — the source of truth for verification state
is the `review_status` field on each rule in backend/app/rules/schemes/*.yaml
(encoded = machine-encoded + unit-tested; verified = human-certified against the
source clause). Re-run after any rule change:

    python -X utf8 scripts/generate_rule_signoff.py
"""

import json
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = ROOT / "backend" / "app" / "rules" / "schemes"
PROPOSED_DIR = ROOT / "backend" / "app" / "rules" / "proposed"
CORPUS_DIR = ROOT / "data" / "corpus"
AUDIT_RESULTS_DIR = ROOT / "backend" / "evals" / "results"
OUT = ROOT / "obsidian-vault" / "03-Rules-as-code" / "Rule-Sign-off-Checklist.md"
QUEUE_OUT = ROOT / "obsidian-vault" / "03-Rules-as-code" / "Review-Queue.md"

STATUS_LABEL = {"encoded": "☐ encoded — awaiting sign-off", "verified": "✅ verified"}


def latest_semantic_audit() -> dict:
    """Per-rule findings from the newest semantic-audit artifact, or {} if none.

    Keyed (scheme_id, rule_id). The audit is a generated suspicion layer — the
    checklist renders it beside each encoded condition so the signer reviews
    the condition's LOGIC, not just the clause text (the PMEGP lesson)."""
    artifacts = sorted(AUDIT_RESULTS_DIR.glob("semantic-audit-*.json"))
    if not artifacts:
        return {}
    artifact = json.loads(artifacts[-1].read_text(encoding="utf-8"))
    return {
        (scheme_id, finding["rule_id"]): finding
        for scheme_id, findings in artifact["schemes"].items()
        for finding in findings
    }


def semantic_cell(finding: dict | None) -> str:
    if finding is None:
        return "—"
    if finding["verdict"] == "faithful":
        return "✓ faithful"
    marker = "🚨" if finding["failure_direction"] == "false_entitlement" else "🚩"
    reason = " ".join(finding["reason"].split()).replace("|", "\\|")
    return f"{marker} {finding['mismatch_type']} — {reason}"


def condition_text(when: dict) -> str:
    if "any" in when and when["any"] is not None:
        return " OR ".join(condition_text(c) for c in when["any"])
    if "all" in when and when["all"] is not None:
        return " AND ".join(condition_text(c) for c in when["all"])
    op = {"eq": "=", "ne": "≠", "gt": ">", "gte": "≥", "lt": "<", "lte": "≤"}[when["op"]]
    return f"`{when['field']} {op} {when['value']}`"


def scheme_name(scheme_id: str) -> str:
    doc = json.loads((CORPUS_DIR / f"{scheme_id}.json").read_text(encoding="utf-8"))
    return doc.get("short_name") or doc.get("name") or scheme_id


def main() -> None:
    schemes = []
    for path in sorted(RULES_DIR.glob("*.yaml")):
        schemes.append(yaml.safe_load(path.read_text(encoding="utf-8")))

    total = sum(len(s["rules"]) for s in schemes)
    verified = sum(
        1 for s in schemes for r in s["rules"] if r.get("review_status") == "verified"
    )
    lines = [
        "---",
        "title: Rule-Sign-off-Checklist",
        "tags: [rules-as-code, checklist, generated]",
        f"updated: {date.today().isoformat()}",
        "---",
        "",
        "# Per-rule verification checklist",
        "",
        "> [!important] Generated file — do not edit here.",
        "> Source of truth is `review_status` on each rule in",
        "> `backend/app/rules/schemes/*.yaml`. To certify a rule, read the clause",
        "> beside the linked official source; then flip its `review_status` to",
        "> `verified` manually. Regenerate with",
        "> `python -X utf8 scripts/generate_rule_signoff.py`.",
        "",
        f"**Progress: {verified}/{total} rules verified.** "
        "A rule counts as *shipped-verified* only after human sign-off; until then "
        "the site's limitations page must say rules are machine-encoded and tested "
        "but pending certification.",
        "",
        "How to check one rule (~2 min): open the source URL, find the clause, then",
        "",
        "1. **Clause text** — the quoted clause matches the official text verbatim.",
        "2. **CONDITION LOGIC** — the encoded condition captures the clause's *logic*, "
        "not just its topic: the profile **field means what the clause tests** (not a "
        "look-alike binding — PMEGP once bound *project cost* to *family income*), the "
        "**operator/threshold** are exact and point the right way, an **IF-THEN clause "
        "is not flattened** into a bare requirement, **OR-alternatives are `any_of`** "
        "(not stacked requires), and disqualifiers are `exclude`, not `require`.",
        "3. **Self-declared** — facts the person can't reliably self-report are marked "
        "`self_declared`.",
        "",
        "> [!warning] Clause-verbatim review alone is NOT sufficient. A rule can quote "
        "> the clause perfectly while encoding different logic — that is exactly how "
        "> the PMEGP defect shipped as `verified`. Step 2 is the one that catches it; "
        "> the *semantic check* column ([[Condition-Semantics-Audit]]) is an "
        "> independent-family LLM's opinion on step 2, rendered beside each rule.",
        "",
    ]

    audit = latest_semantic_audit()
    for scheme in schemes:
        sid = scheme["scheme_id"]
        simplifications = scheme.get("simplifications") or []
        lines += [
            f"## {scheme_name(sid)} (`{sid}`, rules v{scheme['version']})",
            "",
            "| # | rule | kind | **ENCODED CONDITION** | semantic check | "
            "official clause (as encoded) | status |",
            "|---|------|------|-----------------------|----------------|"
            "------------------------------|--------|",
        ]
        for i, rule in enumerate(scheme["rules"], 1):
            clause = " ".join(rule["clause"].split())
            flags = " *(self-declared)*" if rule.get("self_declared") else ""
            status = STATUS_LABEL[rule.get("review_status", "encoded")]
            lines.append(
                f"| {i} | `{rule['id']}`{flags} | {rule['kind']} | "
                f"**{condition_text(rule['when'])}** | "
                f"{semantic_cell(audit.get((sid, rule['id'])))} | {clause} "
                f"([source]({rule['source_url']})) | {status} |"
            )
        lines.append("")
        if simplifications:
            lines.append("**Known simplifications (flagged for the signer):**")
            lines += [f"- ⚠️ {' '.join(s.split())}" for s in simplifications]
            lines.append("")

    lines += [
        "---",
        "Related: [[Verification-Sign-off]] (process) · [[Encoding-Notes]] · "
        "[[Scheme-Coverage]]",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} — {total} rules, {verified} verified, "
          f"{sum(len(s.get('simplifications') or []) for s in schemes)} simplifications flagged")
    write_review_queue()


def write_review_queue() -> None:
    """Render LLM-proposed rules (rules/proposed/*.yaml) awaiting human review."""
    proposals = [
        yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted(PROPOSED_DIR.glob("*.yaml"))
    ] if PROPOSED_DIR.exists() else []

    lines = [
        "---",
        "title: Review-Queue",
        "tags: [rules-as-code, review-queue, generated]",
        f"updated: {date.today().isoformat()}",
        "---",
        "",
        "# Review queue — LLM-proposed rules (NOT live)",
        "",
        "> [!important] Nothing here affects the product. Proposals live in",
        "> `backend/app/rules/proposed/` — a directory the engine never loads.",
        "> To approve a rule: verify its clause against the source URL, then move",
        "> it into `backend/app/rules/schemes/<scheme_id>.yaml` with",
        "> `review_status: encoded` (or `verified`), add unit tests, and delete it",
        "> from the proposal file. Regenerate this page afterwards.",
        "",
    ]
    if not proposals:
        lines.append("*The queue is empty — no proposals awaiting review.*")
    for prop in proposals:
        meta = prop.get("extraction", {})
        lines += [
            f"## {prop['scheme_id']} — extracted {meta.get('extracted_at', '?')} "
            f"({meta.get('status', 'unknown')})",
            "",
            f"Source: {meta.get('source_url', '?')}",
            "",
        ]
        rules = prop.get("rules") or []
        if rules:
            lines += [
                "| # | rule | kind | encoded condition | official clause (verbatim) | decision |",
                "|---|------|------|-------------------|----------------------------|----------|",
            ]
            for i, rule in enumerate(rules, 1):
                clause = " ".join(rule["clause"].split())
                flags = " *(self-declared)*" if rule.get("self_declared") else ""
                lines.append(
                    f"| {i} | `{rule['id']}`{flags} | {rule['kind']} | "
                    f"{condition_text(rule['when'])} | {clause} | ☐ approve / ☐ edit / ☐ reject |"
                )
            lines.append("")
        for title, key, render in (
            ("Blocked — needs a new profile field (human decision)", "blocked_rules",
             lambda b: f"- ⛔ {b['criterion']} → proposed field "
                       f"`{b['proposed_field']['name']}` ({b['proposed_field']['type']}): "
                       f"{b['proposed_field']['meaning']}"),
            ("Rejected drafts (failed schema validation)", "rejected_drafts",
             lambda r: f"- ✖ `{r['draft'].get('id', '?')}` — {r['error'].splitlines()[0]}"),
            ("Proposed simplifications", "simplifications",
             lambda s: f"- ⚠️ {' '.join(s.split())}"),
        ):
            entries = prop.get(key) or []
            if entries:
                lines += [f"**{title}:**", *[render(e) for e in entries], ""]

    QUEUE_OUT.write_text("\n".join(lines), encoding="utf-8")
    n_rules = sum(len(p.get("rules") or []) for p in proposals)
    print(f"wrote {QUEUE_OUT} — {len(proposals)} proposal(s), {n_rules} rules queued")


if __name__ == "__main__":
    main()
