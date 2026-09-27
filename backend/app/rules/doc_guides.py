"""R4 — detect common document types in a scheme's documents markdown.

Detection runs on the English corpus text before edge-translation (the
frontend only ever sees translated markdown, so it cannot match reliably).
The emitted keys are language-invariant; the frontend owns the localized
guide content (where to get each document, typical cost, typical time).
"""

import re

# Guide key → keywords that indicate the document type. Declaration order is
# the emission order, so downstream rendering is deterministic. Keywords match
# on word boundaries, case-insensitively.
GUIDE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "aadhaar": ("aadhaar", "aadhar"),
    "bank_account": ("bank account", "bank passbook", "passbook", "ifsc", "bank details"),
    "caste_certificate": (
        "caste certificate",
        "category certificate",
        "community certificate",
    ),
    "income_certificate": ("income certificate", "income proof", "proof of income"),
    "bpl_card": ("bpl",),
    "ration_card": ("ration card",),
    "land_records": (
        "land record",
        "land records",
        "khasra",
        "khatauni",
        "land ownership",
        "landholding",
    ),
    "disability_certificate": ("disability certificate", "udid"),
    "photo": ("photograph", "passport-size", "passport size"),
    "age_proof": ("birth certificate", "age proof", "proof of age", "date of birth"),
    "residence_proof": (
        "domicile",
        "residence proof",
        "address proof",
        "proof of residence",
    ),
    "death_certificate": ("death certificate",),
}

_PATTERNS: dict[str, re.Pattern[str]] = {
    key: re.compile(
        r"\b(?:" + "|".join(re.escape(kw) for kw in keywords) + r")\b",
        re.IGNORECASE,
    )
    for key, keywords in GUIDE_KEYWORDS.items()
}


def first_guide_key(text: str) -> str | None:
    """The first known document type (declaration order) a single line names."""
    return next((key for key, pattern in _PATTERNS.items() if pattern.search(text)), None)


def guide_keys_for(documents_markdown: str) -> list[str]:
    """Guide keys for every known document type the markdown mentions."""
    if not documents_markdown:
        return []
    return [key for key, pattern in _PATTERNS.items() if pattern.search(documents_markdown)]
