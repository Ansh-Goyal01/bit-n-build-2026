/** Locale coverage report â€” the P2 gate behind `enabled` in lib/i18n/config.ts.
 *
 * For every non-English locale, walks the UiDict and wizard overlay and lists
 * leaf strings that are byte-identical to the English canonical (i.e. fell
 * back untranslated). Proper nouns and canonical values that are identical by
 * design are allowlisted below.
 *
 * Run (Node â‰¥ 23 strips types natively):
 *   node frontend/scripts/i18n-coverage.mts
 * Exit code 1 when any locale has non-allowlisted fallbacks.
 */

import { en } from "../lib/i18n/locales/en.ts";
import { bn, bnWizard } from "../lib/i18n/locales/bn.ts";
import { gu, guWizard } from "../lib/i18n/locales/gu.ts";
import { hi, hiWizard } from "../lib/i18n/locales/hi.ts";
import { kn, knWizard } from "../lib/i18n/locales/kn.ts";
import { ml, mlWizard } from "../lib/i18n/locales/ml.ts";
import { mr, mrWizard } from "../lib/i18n/locales/mr.ts";
import { or, orWizard } from "../lib/i18n/locales/or.ts";
import { pa, paWizard } from "../lib/i18n/locales/pa.ts";
import { ta, taWizard } from "../lib/i18n/locales/ta.ts";
import { te, teWizard } from "../lib/i18n/locales/te.ts";

const LOCALES = { bn, gu, hi, kn, ml, mr, or, pa, ta, te } as const;
const OVERLAYS = {
  bn: bnWizard,
  gu: guWizard,
  hi: hiWizard,
  kn: knWizard,
  ml: mlWizard,
  mr: mrWizard,
  or: orWizard,
  pa: paWizard,
  ta: taWizard,
  te: teWizard,
} as const;

/** Values identical to English on purpose (brand names, codes, numerals). */
const ALLOWLIST = [
  /^Adhikaar$/,
  /^GitHub$/,
  /^myScheme/,
  /^PM[- ]/,
  // Category codes kept in Latin script by the human-reviewed Hindi locale;
  // treated as canonical across all Indic locales.
  /^(OBC|SC|ST|EWS|BPL|APL)$/,
  /^\d[\d,.%â€“-]*$/,
];

function walk(
  node: unknown,
  ref: unknown,
  path: string,
  out: string[],
): void {
  if (typeof node === "string") {
    if (typeof ref === "string" && node === ref && !ALLOWLIST.some((re) => re.test(node))) {
      out.push(`${path} = ${JSON.stringify(node)}`);
    }
    return;
  }
  if (typeof node === "object" && node !== null) {
    for (const [key, value] of Object.entries(node)) {
      const refChild =
        typeof ref === "object" && ref !== null
          ? (ref as Record<string, unknown>)[key]
          : undefined;
      walk(value, refChild, path ? `${path}.${key}` : key, out);
    }
  }
}

let failed = false;
for (const [code, dict] of Object.entries(LOCALES)) {
  const fallbacks: string[] = [];
  walk(dict, en, "ui", fallbacks);
  // Wizard overlays share key paths with each other, not with en â€” compare
  // against the English canonical only via identical-string detection between
  // the overlay and itself is meaningless, so check overlay strings that are
  // pure ASCII instead (Indic locales should carry Indic script).
  const overlay = OVERLAYS[code as keyof typeof OVERLAYS];
  const ascii: string[] = [];
  collectAscii(overlay, `wizard`, ascii);
  const report = [...fallbacks, ...ascii];
  if (report.length > 0) {
    failed = true;
    console.log(`\n${code}: ${report.length} untranslated string(s)`);
    for (const line of report) console.log(`  ${line}`);
  } else {
    console.log(`${code}: OK`);
  }
}

function collectAscii(node: unknown, path: string, out: string[]): void {
  if (typeof node === "string") {
    // A translated Indic string must contain at least one non-ASCII char;
    // allowlisted proper nouns pass.
    if (/^[\x00-\x7F]+$/.test(node) && !ALLOWLIST.some((re) => re.test(node))) {
      out.push(`${path} = ${JSON.stringify(node)}`);
    }
    return;
  }
  if (typeof node === "object" && node !== null) {
    for (const [key, value] of Object.entries(node)) {
      collectAscii(value, `${path}.${key}`, out);
    }
  }
}

process.exit(failed ? 1 : 0);
