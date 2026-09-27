"""Canonical state / union-territory names — the exact strings state-scheme
rules compare against (e.g. `state eq "Uttar Pradesh"`).

Mirrors INDIAN_STATES in frontend/lib/wizard.ts (a parity test keeps the two
lists identical), so a wizard submission already arrives canonical. Free-text
extraction may say "UP" or "uttar pradesh"; `canonical_state` maps those to
the canonical name, and anything unrecognised to None ("not stated") — a
state rule must never compare against an unnormalised string.
"""

INDIAN_STATES: tuple[str, ...] = (
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir",
    "Ladakh", "Lakshadweep", "Puducherry",
)  # fmt: skip

# Common abbreviations and older spellings → canonical name. Keys are
# normalised (lowercase, punctuation stripped, single spaces).
_ALIASES: dict[str, str] = {
    "up": "Uttar Pradesh",
    "u p": "Uttar Pradesh",
    "mp": "Madhya Pradesh",
    "ap": "Andhra Pradesh",
    "hp": "Himachal Pradesh",
    "jk": "Jammu and Kashmir",
    "j and k": "Jammu and Kashmir",
    "wb": "West Bengal",
    "tn": "Tamil Nadu",
    "orissa": "Odisha",
    "uttaranchal": "Uttarakhand",
    "pondicherry": "Puducherry",
    "new delhi": "Delhi",
    "nct of delhi": "Delhi",
}


def _key(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else " " for ch in value.lower().replace("&", " and "))
    return " ".join(cleaned.split())


_BY_KEY: dict[str, str] = {_key(name): name for name in INDIAN_STATES} | _ALIASES


def canonical_state(value: str) -> str | None:
    """Canonical state name for `value`, or None when it isn't a known state."""
    return _BY_KEY.get(_key(value))
