"""Application-packet parsing — the official text, split into lines, never rewritten.

The corpus stores each scheme's application process as markdown blocks headed
`### Application mode: <mode>` and its documents as a (mostly) numbered list.
Both are parsed here, deterministically and on the English text BEFORE edge
translation (a translated heading could not be parsed reliably).

Invariant: every emitted text is a substring of one source line. Markers
(list bullets, "Step N:" prefixes, heading hashes, quote marks) are stripped;
words are never added, reordered, or paraphrased. That makes "each step maps to
source text" a property that holds by construction and is checked in tests.
"""

import re

from app.agent.state import (
    ApplicationMode,
    ApplicationModeKind,
    ApplicationStep,
    DocumentItem,
)
from app.rules.doc_guides import first_guide_key

_MODE_HEADING = re.compile(r"^###\s*Application mode:\s*(.+?)\s*$", re.MULTILINE)
_LIST_MARKER = re.compile(r"^(?:[-*+]|\d+[.)])\s+")
# "**Step 1:**", "**Step 1**-", "Step 1:" — the UI numbers steps itself.
_STEP_PREFIX = re.compile(r"^(?:\*\*)?\s*Step\s*\d+\s*(?:\*\*)?\s*[:.\-–]?\s*(?:\*\*)?\s*", re.I)
_HEADING = re.compile(r"^#{1,6}\s*")
_QUOTE = re.compile(r"^>\s*")
_MD_LINK = re.compile(r"\[[^\]]*\]\((https?://[^)\s]+)\s*\)")
_BARE_URL = re.compile(r"(?<![(\[])\bhttps?://[^\s)\]]+")
_BOLD_ONLY = re.compile(r"^\*\*([^*]+)\*\*\s*(:?)\s*$")
_LABEL_MAX_CHARS = 80


def _is_label(text: str) -> bool:
    """A short line that introduces what follows ("For 1st Loan:", "**Note:**")."""
    bold = _BOLD_ONLY.match(text)
    inner = (bold.group(1) + bold.group(2)).strip() if bold else text
    if len(inner) > _LABEL_MAX_CHARS:
        return False
    return inner.endswith(":") or (bold is not None and not inner.endswith("."))


def _mode_kind(label: str) -> ApplicationModeKind:
    lowered = label.lower()
    if "csc" in lowered:
        return "csc"
    if "offline" in lowered:
        return "offline"
    if "online" in lowered:
        return "online"
    return "other"


def _links(block: str) -> list[str]:
    found = [*_MD_LINK.findall(block), *_BARE_URL.findall(block)]
    seen: dict[str, None] = {}
    for url in found:
        seen.setdefault(url.rstrip(".,;"), None)
    return list(seen)


def _step(line: str) -> ApplicationStep | None:
    text = line.strip()
    if not text:
        return None
    if _HEADING.match(text):
        heading = _HEADING.sub("", text).strip()
        return ApplicationStep(kind="heading", text=heading) if heading else None
    if _QUOTE.match(text):
        note = _QUOTE.sub("", text).strip()
        return ApplicationStep(kind="note", text=note) if note else None
    text = _LIST_MARKER.sub("", text)
    text = _STEP_PREFIX.sub("", text).strip()
    if not text:
        return None
    if _BOLD_ONLY.match(text) and _is_label(text):
        return ApplicationStep(kind="heading", text=text)
    return ApplicationStep(kind="step", text=text)


def parse_application_modes(markdown: str) -> list[ApplicationMode]:
    """Split the application section into modes and one-line steps.

    Text before the first mode heading (rare) becomes an "other" mode, so no
    official line is ever dropped."""
    if not markdown.strip():
        return []
    headings = list(_MODE_HEADING.finditer(markdown))
    blocks: list[tuple[str, str]] = []
    preamble = markdown[: headings[0].start()] if headings else markdown
    if preamble.strip():
        blocks.append(("", preamble))
    for i, heading in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(markdown)
        blocks.append((heading.group(1), markdown[heading.end() : end]))

    modes = []
    for label, body in blocks:
        steps = [step for line in body.splitlines() if (step := _step(line))]
        if steps:
            modes.append(
                ApplicationMode(mode=_mode_kind(label), steps=steps, links=_links(body))
            )
    return modes


def _document_line(line: str) -> DocumentItem | None:
    text = line.strip()
    if not text:
        return None
    if _LIST_MARKER.match(text):
        item = _LIST_MARKER.sub("", text).strip()
        if not item:
            return None
        return DocumentItem(kind="item", text=item, guide_key=first_guide_key(item))
    if _HEADING.match(text):
        label = _HEADING.sub("", text).strip()
        return DocumentItem(kind="group", text=label) if label else None
    quoted = _QUOTE.sub("", text).strip()
    if not quoted:
        return None
    if _is_label(quoted):
        return DocumentItem(kind="group", text=quoted)
    return DocumentItem(kind="note", text=quoted)


def parse_document_items(markdown: str) -> list[DocumentItem]:
    """Documents list → tickable items, group labels, and prose notes."""
    return [item for line in markdown.splitlines() if (item := _document_line(line))]
