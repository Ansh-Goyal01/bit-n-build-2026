"""Generate machine-translated locale files for every supported language.

Reads the canonical English strings exported by `node frontend/scripts/i18n-export.mts`
(frontend/lib/i18n/locales/source-strings.json) and translates every leaf through the
backend's own translation pipeline (`app.i18n.translate.translate_many`) â€” the
same provider, disk cache, and canonical-value protections the report prose
uses. Each target language becomes frontend/lib/i18n/locales/<code>.ts with the same
shape as the hand-reviewed hi.ts (a UiDict + a WizardOverlay).

Safety rails:
- Interpolation placeholders ({count}, {code}, â€¦) must survive translation
  byte-for-byte; a string that loses one falls back to English and is reported.
- Failed/missing translations fall back to English (the runtime does the same
  for missing keys) â€” a locale can ship partial and never break the UI.
- Output files are marked machine-translated pending native-speaker review.

Run (LLM calls are disk-cached â€” reruns are free and deterministic):

    backend/.venv/Scripts/python.exe -X utf8 -u scripts/generate_locales.py
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import app.i18n.translate as tr  # noqa: E402
from app.i18n.translate import SUPPORTED_LANGUAGES, translate_many  # noqa: E402

# UI strings are long and Indic scripts are verbose â€” 16-string batches
# overran the model's output budget on Tamil (indices 0..5 of 0..15 came
# back). Halving the batch keeps every response comfortably inside it.
tr._BATCH_SIZE = 8

LOCALES_DIR = ROOT / "frontend" / "lib" / "i18n" / "locales"
SOURCE = LOCALES_DIR / "source-strings.json"

# Hand-reviewed locales are never overwritten by the generator.
HAND_REVIEWED = {"en", "hi"}

ENDONYMS = {
    "bn": "à¦¬à¦¾à¦‚à¦²à¦¾",
    "mr": "à¤®à¤°à¤¾à¤ à¥€",
    "te": "à°¤à±†à°²à±à°—à±",
    "ta": "à®¤à®®à®¿à®´à¯",
    "gu": "àª—à«àªœàª°àª¾àª¤à«€",
    "kn": "à²•à²¨à³à²¨à²¡",
    "ml": "à´®à´²à´¯à´¾à´³à´‚",
    "pa": "à¨ªà©°à¨œà¨¾à¨¬à©€",
    "or": "à¬“à¬¡à¬¼à¬¿à¬†",
}

PLACEHOLDER = re.compile(r"\{\w+\}")


def flatten(node: object, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], str]]:
    if isinstance(node, str):
        return [(path, node)]
    if isinstance(node, dict):
        leaves: list[tuple[tuple[str, ...], str]] = []
        for key, value in node.items():
            leaves.extend(flatten(value, (*path, key)))
        return leaves
    raise TypeError(f"unexpected node type {type(node)!r} at {'.'.join(path)}")


def rebuild(skeleton: object, values: dict[tuple[str, ...], str], path: tuple[str, ...] = ()) -> object:
    if isinstance(skeleton, str):
        return values[path]
    assert isinstance(skeleton, dict)
    return {key: rebuild(value, values, (*path, key)) for key, value in skeleton.items()}


def translate_tree(tree: dict, lang: str) -> tuple[dict, list[str]]:
    """Translate every leaf; placeholder-losing strings fall back to English."""
    leaves = flatten(tree)
    texts = [text for _, text in leaves]
    translated = translate_many(texts, lang)

    fallbacks: list[str] = []
    values: dict[tuple[str, ...], str] = {}
    for (path, source), output in zip(leaves, translated, strict=True):
        wanted = set(PLACEHOLDER.findall(source))
        if output == source or not output.strip():
            # Identical output is only a miss for real prose â€” acronym-only
            # labels (OBC, SC) correctly pass through unchanged.
            if re.search(r"[a-z]", source):
                fallbacks.append(".".join(path))
            values[path] = source
        elif wanted - set(PLACEHOLDER.findall(output)):
            fallbacks.append(".".join(path) + " (placeholder lost)")
            values[path] = source
        else:
            values[path] = output
    return rebuild(tree, values), fallbacks  # type: ignore[return-value]


def ts_literal(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def write_locale(code: str, ui: dict, wizard: dict, fallbacks: list[str]) -> None:
    language = SUPPORTED_LANGUAGES[code]
    endonym = ENDONYMS[code]
    review_note = (
        f"{len(fallbacks)} strings fell back to English (see generator output)"
        if fallbacks
        else "all strings translated"
    )
    header = (
        f"/** {language} ({endonym}) â€” MACHINE-TRANSLATED, pending native-speaker review.\n"
        f" *\n"
        f" * Generated {date.today().isoformat()} by scripts/generate_locales.py through the\n"
        f" * backend translation pipeline (disk-cached, canonical values copied through).\n"
        f" * Coverage: {review_note}. Do not hand-edit strings here without also\n"
        f" * recording the review in the vault sign-off notes; regenerate with:\n"
        f" *   node frontend/scripts/i18n-export.mts\n"
        f" *   backend/.venv/Scripts/python.exe -X utf8 -u scripts/generate_locales.py\n"
        f" */\n"
    )
    body = (
        f"{header}\n"
        f'import type {{ UiDict }} from "./en";\n'
        f'import type {{ WizardOverlay }} from "../overlay";\n\n'
        f"export const {code}: UiDict = {ts_literal(ui)};\n\n"
        f"export const {code}Wizard: WizardOverlay = {ts_literal(wizard)};\n"
    )
    (LOCALES_DIR / f"{code}.ts").write_text(body, encoding="utf-8", newline="\n")


def main() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    targets = [c for c in SUPPORTED_LANGUAGES if c not in HAND_REVIEWED]
    for code in targets:
        print(f"--- {code} ({SUPPORTED_LANGUAGES[code]})")
        ui, ui_fallbacks = translate_tree(source["ui"], code)
        wizard, wiz_fallbacks = translate_tree(source["wizard"], code)
        fallbacks = ui_fallbacks + wiz_fallbacks
        write_locale(code, ui, wizard, fallbacks)
        print(f"    wrote {code}.ts â€” {len(fallbacks)} English fallbacks")
        for path in fallbacks:
            print(f"      fallback: {path}")
    print("done")


if __name__ == "__main__":
    main()
