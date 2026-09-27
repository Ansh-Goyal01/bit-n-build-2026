"use client";

// Assisted mode (CSC / Jan Seva Kendra operator). Everything here annotates
// the engine's result; nothing changes a verdict.
import { ShieldCheck, UserCheck } from "lucide-react";

import { Chip } from "@/components/ui/chip";
import { Input } from "@/components/ui/input";
import {
  type Annotations,
  NOTE_MAX_LENGTH,
  type OperatorAnnotation,
  annotate,
  annotationKey,
  handoffSummary,
} from "@/lib/assisted";
import { useT } from "@/lib/i18n";
import { type DocumentsHave, documentTracker, stripMarkdown } from "@/lib/packet";
import type { SchemeResult } from "@/lib/types";

type OnAnnotate = (key: string, change: Partial<OperatorAnnotation>) => void;

/** "Document seen" checks for each self-declared fact behind a conditional
 * verdict — rendered inside the application packet. */
export function OperatorChecks({
  result,
  annotations,
  onAnnotate,
}: {
  result: SchemeResult;
  annotations: Annotations;
  onAnnotate: OnAnnotate;
}) {
  const t = useT();
  const confirmations = result.confirmations ?? [];
  if (confirmations.length === 0) return null;
  return (
    <fieldset className="rounded-lg border border-border bg-card p-3">
      <legend className="flex items-center gap-1.5 px-1 text-sm font-semibold">
        <UserCheck className="size-4 text-accent" aria-hidden="true" />
        {t("assisted.checksTitle")}
      </legend>
      <p className="mb-2 text-xs leading-relaxed text-muted-foreground">
        {t("assisted.checksLead")}
      </p>
      <ul className="flex flex-col gap-3">
        {confirmations.map((step) => {
          const key = annotationKey(result.scheme_id, step.rule_id);
          const annotation = annotations[key];
          const id = `op-${key}`;
          return (
            <li key={key} className="flex flex-col gap-1.5 text-sm">
              <label htmlFor={id} className="flex cursor-pointer items-start gap-2">
                <input
                  id={id}
                  type="checkbox"
                  className="mt-0.5 size-4 shrink-0 accent-accent"
                  checked={annotation?.seen ?? false}
                  onChange={(e) => onAnnotate(key, { seen: e.target.checked })}
                />
                <span>
                  <span className="font-medium">{t("assisted.documentSeen")}</span>{" "}
                  <span className="text-muted-foreground">{step.text}</span>
                </span>
              </label>
              {annotation?.seen && (
                <Input
                  aria-label={t("assisted.noteLabel")}
                  placeholder={t("assisted.notePlaceholder")}
                  maxLength={NOTE_MAX_LENGTH}
                  value={annotation.note}
                  onChange={(e) => onAnnotate(key, { note: e.target.value })}
                  className="ml-6 h-9 w-auto text-sm"
                />
              )}
            </li>
          );
        })}
      </ul>
    </fieldset>
  );
}

/** Separate from the verdict badge on purpose: "Verified by operator: 1 of 2". */
export function OperatorBadge({
  result,
  annotations,
}: {
  result: SchemeResult;
  annotations: Annotations;
}) {
  const t = useT();
  const { verified, pending } = annotate(result, annotations);
  if (verified.length === 0) return null;
  return (
    <Chip tone="yes">
      <ShieldCheck aria-hidden="true" />
      {t("assisted.badge", { seen: verified.length, total: verified.length + pending.length })}
    </Chip>
  );
}

/** Operator hand-off block for the printed packet. */
export function OperatorHandoff({
  result,
  annotations,
  have,
}: {
  result: SchemeResult;
  annotations: Annotations;
  have: DocumentsHave;
}) {
  const t = useT();
  const missing = documentTracker(result, have).missing.map((line) =>
    stripMarkdown(line.item.text),
  );
  const handoff = handoffSummary(result, annotations, missing);
  return (
    <section className="mt-4 rounded border border-border p-3">
      <h2 className="text-sm font-semibold">{t("assisted.handoffTitle")}</h2>

      <h3 className="mt-2 text-xs font-semibold uppercase">{t("assisted.handoffConfirmed")}</h3>
      {handoff.verified.length === 0 ? (
        <p className="text-sm">{t("assisted.handoffNoneConfirmed")}</p>
      ) : (
        <ul className="list-disc pl-5 text-sm leading-snug">
          {handoff.verified.map((fact) => (
            <li key={fact.ruleId}>
              {t("assisted.verifiedBy")} {fact.text}
              {fact.note && ` — ${fact.note}`}
            </li>
          ))}
        </ul>
      )}
      {handoff.pending.length > 0 && (
        <>
          <h3 className="mt-2 text-xs font-semibold uppercase">{t("assisted.handoffPending")}</h3>
          <ul className="list-disc pl-5 text-sm leading-snug">
            {handoff.pending.map((fact) => (
              <li key={fact.ruleId}>{fact.text}</li>
            ))}
          </ul>
        </>
      )}

      <h3 className="mt-2 text-xs font-semibold uppercase">{t("assisted.handoffMissing")}</h3>
      {handoff.missingDocuments.length === 0 ? (
        <p className="text-sm">{t("assisted.handoffNoneMissing")}</p>
      ) : (
        <ul className="list-disc pl-5 text-sm leading-snug">
          {handoff.missingDocuments.map((doc, i) => (
            <li key={i}>{doc}</li>
          ))}
        </ul>
      )}

      <h3 className="mt-2 text-xs font-semibold uppercase">{t("assisted.handoffNext")}</h3>
      {handoff.nextSteps.length > 0 ? (
        <ol className="list-decimal pl-5 text-sm leading-snug">
          {handoff.nextSteps.map((step, i) => (
            <li key={i}>{stripMarkdown(step.text)}</li>
          ))}
        </ol>
      ) : (
        <p className="text-sm">{t("assisted.handoffNoOffline")}</p>
      )}
      <p className="mt-1 text-sm">{handoff.officialUrl}</p>
    </section>
  );
}
