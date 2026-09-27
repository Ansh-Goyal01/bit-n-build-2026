/** Wizard string overlays: wizard.ts stays the canonical (English) source of
 * questions and logic; a locale overlays only STRINGS on top of it, keyed by
 * step id / field key / option value. Missing keys fall back to English —
 * the coverage script reports them, they never break the UI. */

import type { FieldDef, StepDef } from "@/lib/wizard";

export interface FieldOverlay {
  label?: string;
  help?: string;
  whyWeAsk?: string;
  errorText?: string;
  placeholder?: string;
  options?: Record<string, { label?: string; description?: string }>;
}

export interface WizardOverlay {
  steps?: Record<string, { title?: string; lead?: string }>;
  fields?: Record<string, FieldOverlay>;
}

export function localizeField(field: FieldDef, overlay: WizardOverlay | null): FieldDef {
  const o = overlay?.fields?.[field.key];
  if (!o) return field;
  return {
    ...field,
    label: o.label ?? field.label,
    help: o.help ?? field.help,
    whyWeAsk: o.whyWeAsk ?? field.whyWeAsk,
    errorText: o.errorText ?? field.errorText,
    placeholder: o.placeholder ?? field.placeholder,
    options: field.options?.map((opt) => ({
      ...opt,
      label: o.options?.[opt.value]?.label ?? opt.label,
      description: o.options?.[opt.value]?.description ?? opt.description,
    })),
  };
}

export function localizeStep(step: StepDef, overlay: WizardOverlay | null): StepDef {
  const o = overlay?.steps?.[step.id];
  return {
    ...step,
    title: o?.title ?? step.title,
    lead: o?.lead ?? step.lead,
    fields: step.fields.map((f) => localizeField(f, overlay)),
  };
}
