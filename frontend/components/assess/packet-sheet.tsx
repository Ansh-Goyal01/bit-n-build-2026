"use client";

import { useT } from "@/lib/i18n";
import { type DocumentsHave, documentTracker, stripMarkdown } from "@/lib/packet";
import type { SchemeResult, UserProfile } from "@/lib/types";
import { ApplicationSteps, Worksheet } from "./application-packet";

/** Print-only application packet for one scheme. Hidden on screen; when the
 * person taps "Print packet", <html data-print="packet"> hides the report and
 * shows only the sheet marked active (see globals.css). Ticked documents
 * print checked; the rest print as empty boxes to carry to the office. */
export function PacketSheet({
  result,
  profile,
  have,
  active,
  handoff,
}: {
  result: SchemeResult;
  profile: UserProfile;
  have: DocumentsHave;
  active: boolean;
  /** Assisted-mode operator hand-off block, when one exists. */
  handoff?: React.ReactNode;
}) {
  const t = useT();
  const { lines } = documentTracker(result, have);
  const confirmations = result.confirmations ?? [];

  return (
    <article className="packet-sheet" data-active={active ? "true" : "false"} aria-hidden={!active}>
      <p className="text-xs tracking-wide text-muted-foreground uppercase">
        {t("packet.title")} · {new Date().toLocaleDateString("en-IN")}
      </p>
      <h1 className="mt-1 font-serif text-2xl font-semibold">{result.scheme_name}</h1>
      <p className="text-sm">
        {result.short_name} · {t(`verdicts.${result.verdict}`)}
      </p>

      <div className="mt-4">
        <Worksheet profile={profile} />
      </div>

      <h2 className="mt-4 text-sm font-semibold">{t("packet.documentsTitle")}</h2>
      {lines.length === 0 ? (
        <p className="text-sm">{t("packet.noDocumentsListed")}</p>
      ) : (
        <ul className="mt-1 text-sm leading-snug">
          {lines.map((line) => (
            <li key={line.key}>
              {have[line.key] ? "☑" : "☐"} {stripMarkdown(line.item.text)}
            </li>
          ))}
        </ul>
      )}

      <h2 className="mt-4 mb-1 text-sm font-semibold">{t("packet.stepsTitle")}</h2>
      <ApplicationSteps modes={result.application_modes ?? []} pageUrl={result.page_url} />

      {confirmations.length > 0 && (
        <>
          <h2 className="mt-4 text-sm font-semibold">{t("packet.beforeYouGo")}</h2>
          <ul className="list-disc pl-5 text-sm leading-snug">
            {confirmations.map((step) => (
              <li key={step.rule_id}>{step.text}</li>
            ))}
          </ul>
        </>
      )}

      {handoff}

      <p className="mt-4 text-xs text-muted-foreground">
        {result.page_url} · {t("footer.disclaimer")}
      </p>
    </article>
  );
}
