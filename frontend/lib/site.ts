/** Site-wide constants — one place to update when the repo goes public. */

import schemes from "@/lib/data/schemes.json";

export const SITE_NAME = "Adhikaar";

export const SITE_TAGLINE =
  "Find out exactly what government support you're entitled to";

/** TODO(publish): update once the repository is pushed to GitHub. */
export const GITHUB_URL = "https://github.com/Ansh-Goyal01/adhikaar";

export const MYSCHEME_URL = "https://www.myscheme.gov.in";

/** Derived from the generated catalog so copy can never drift from the data.
 * SCHEME_COUNT counts schemes the eligibility check actually decides (live,
 * human-reviewed rules); CATALOG_COUNT counts everything browsable; the rest
 * split into rules-pending-review (PENDING_COUNT) and out-of-scope
 * (OUT_OF_SCOPE_COUNT, e.g. institution-only schemes). Never claim the bigger
 * number for the check. */
export const SCHEME_COUNT = schemes.filter(
  (scheme) => scheme.rules.length > 0 && !scheme.out_of_scope,
).length;

export const CATALOG_COUNT = schemes.length;

export const OUT_OF_SCOPE_COUNT = schemes.filter(
  (scheme) => scheme.out_of_scope,
).length;

export const PENDING_COUNT =
  CATALOG_COUNT - SCHEME_COUNT - OUT_OF_SCOPE_COUNT;

export const RULE_COUNT = schemes.reduce(
  (total, scheme) => total + scheme.rules.length,
  0,
);

export const DISCLAIMER =
  "Adhikaar explains eligibility using official scheme documents. It is informational only — not legal advice — and final decisions rest with the implementing authorities. Always confirm on the official portal before acting.";
