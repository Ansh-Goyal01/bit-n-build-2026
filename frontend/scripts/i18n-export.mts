/** Export the canonical English i18n strings as JSON for the locale generator.
 *
 * Emits lib/i18n/locales/source-strings.json with two trees:
 *   ui     â€” the full English UiDict (locales/en.ts)
 *   wizard â€” an overlay-shaped skeleton of every wizard string (lib/wizard.ts)
 *
 * Run (Node â‰¥ 23 strips types natively):
 *   node frontend/scripts/i18n-export.mts
 * Then generate locale files:
 *   backend/.venv/Scripts/python.exe -X utf8 scripts/generate_locales.py
 */

import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { en } from "../lib/i18n/locales/en.ts";
import { STEPS } from "../lib/wizard.ts";

interface OptionStrings {
  label: string;
  description?: string;
}
interface FieldStrings {
  label: string;
  help?: string;
  whyWeAsk?: string;
  errorText?: string;
  placeholder?: string;
  options?: Record<string, OptionStrings>;
}

const steps: Record<string, { title: string; lead?: string }> = {};
const fields: Record<string, FieldStrings> = {};

for (const step of STEPS) {
  steps[step.id] = { title: step.title, ...(step.lead ? { lead: step.lead } : {}) };
  for (const field of step.fields) {
    const entry: FieldStrings = { label: field.label };
    if (field.help) entry.help = field.help;
    if (field.whyWeAsk) entry.whyWeAsk = field.whyWeAsk;
    if (field.errorText) entry.errorText = field.errorText;
    if (field.placeholder) entry.placeholder = field.placeholder;
    // State names are proper nouns â€” canonical English in v1 (per hi.ts note),
    // so the state select's options are deliberately not exported.
    if (field.options && field.key !== "state") {
      entry.options = {};
      for (const opt of field.options) {
        entry.options[opt.value] = {
          label: opt.label,
          ...(opt.description ? { description: opt.description } : {}),
        };
      }
    }
    fields[field.key] = entry;
  }
}

const here = dirname(fileURLToPath(import.meta.url));
const dest = join(here, "..", "lib", "i18n", "locales", "source-strings.json");
writeFileSync(dest, `${JSON.stringify({ ui: en, wizard: { steps, fields } }, null, 2)}\n`, "utf8");
console.log(`wrote ${dest}`);
