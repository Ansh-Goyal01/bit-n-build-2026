"use client";

import { ClipboardCheck, ExternalLink, FileWarning, Printer } from "lucide-react";
import ReactMarkdown from "react-markdown";

import { Button } from "@/components/ui/button";
import { WhatsAppIcon } from "@/components/ui/whatsapp-icon";
import { useT } from "@/lib/i18n";
import {
  type DocumentsHave,
  type WorksheetRow,
  buildWorksheet,
  documentKey,
  documentTracker,
  packetShareText,
} from "@/lib/packet";
import type { ApplicationMode, SchemeResult, UserProfile } from "@/lib/types";

type T = ReturnType<typeof useT>;

/** Inline markdown only — packet lines are single lines of official text. */
function Inline({ text }: { text: string }) {
  return (
    <ReactMarkdown
      components={{
        p: ({ children }) => <>{children}</>,
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent underline underline-offset-2"
          >
            {children}
          </a>
        ),
      }}
    >
      {text}
    </ReactMarkdown>
  );
}

function worksheetValue(t: T, row: WorksheetRow): string {
  const { field, value } = row;
  if (value === null) return "";
  if (typeof value === "boolean") return value ? t("packet.yes") : t("packet.no");
  if (field === "annual_family_income_inr") return `₹${Number(value).toLocaleString("en-IN")}`;
  if (field === "gender" || field === "area") {
    const group = field === "gender" ? "gender" : "area";
    const key = `chips.${group}.${value}`;
    const out = t(key);
    return out === key ? String(value) : out;
  }
  if (field === "social_category") {
    const text = String(value);
    return text.length <= 3 ? text.toUpperCase() : text.replace(/_/g, " ");
  }
  return String(value);
}

export function Worksheet({ profile }: { profile: UserProfile }) {
  const t = useT();
  const rows = buildWorksheet(profile);
  return (
    <div>
      <h4 className="text-sm font-semibold text-foreground">{t("packet.worksheetTitle")}</h4>
      <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
        {t("packet.worksheetLead")}
      </p>
      <dl className="mt-2 grid gap-x-4 gap-y-1.5 text-sm sm:grid-cols-2">
        {rows.map((row) => (
          <div key={row.field} className="flex items-baseline justify-between gap-3 border-b border-dashed border-border pb-1">
            <dt className="text-muted-foreground">{t(`packet.fields.${row.field}`)}</dt>
            <dd className={row.filled ? "font-medium text-foreground" : "text-xs text-verdict-info"}>
              {row.filled ? worksheetValue(t, row) : t("packet.toFill")}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-1.5 text-xs text-muted-foreground">{t("packet.filledFromCheck")}</p>
    </div>
  );
}

export function ApplicationSteps({ modes, pageUrl }: { modes: ApplicationMode[]; pageUrl: string }) {
  const t = useT();
  if (modes.length === 0) {
    return (
      <p className="text-sm leading-relaxed text-muted-foreground">
        {t("packet.noStepsListed")}{" "}
        {pageUrl && (
          <a href={pageUrl} target="_blank" rel="noopener noreferrer" className="text-accent underline">
            {t("card.officialPage")}
          </a>
        )}
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      {modes.map((mode, i) => {
        let n = 0;
        return (
          <div key={i}>
            <p className="text-xs font-semibold tracking-wide text-accent uppercase">
              {t(`packet.modes.${mode.mode}`)}
            </p>
            <ol className="mt-1.5 flex flex-col gap-1.5 text-sm leading-relaxed">
              {mode.steps.map((step, j) => {
                if (step.kind === "heading") {
                  return (
                    <li key={j} className="list-none pt-1 font-medium text-foreground">
                      <Inline text={step.text} />
                    </li>
                  );
                }
                if (step.kind === "note") {
                  return (
                    <li key={j} className="list-none rounded-md bg-muted px-2.5 py-1.5 text-xs text-muted-foreground">
                      <Inline text={step.text} />
                    </li>
                  );
                }
                n += 1;
                return (
                  <li key={j} className="flex list-none gap-2.5">
                    <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-accent/10 text-xs font-semibold text-accent">
                      {n}
                    </span>
                    <span className="text-foreground">
                      <Inline text={step.text} />
                    </span>
                  </li>
                );
              })}
            </ol>
          </div>
        );
      })}
      <p className="text-xs text-muted-foreground">{t("packet.stepsSource")}</p>
    </div>
  );
}

/** Have/missing tracker for one scheme. Missing known document types show
 * where to get them (localized guides); anything else points to the office.
 * A scheme whose official page lists no documents says exactly that. */
export function DocumentTrackerList({
  result,
  have,
  onToggle,
  showGuides = true,
}: {
  result: SchemeResult;
  have: DocumentsHave;
  onToggle: (key: string) => void;
  showGuides?: boolean;
}) {
  const t = useT();
  const items = result.document_items ?? [];
  if (!items.some((item) => item.kind === "item")) {
    return (
      <div className="flex flex-col gap-1.5">
        {items
          .filter((item) => item.kind === "note")
          .map((item, i) => (
            <p key={i} className="text-sm leading-relaxed text-muted-foreground">
              <Inline text={item.text} />
            </p>
          ))}
        <p className="flex items-start gap-2 rounded-lg bg-verdict-info-soft p-3 text-sm leading-relaxed text-verdict-info">
          <FileWarning className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          {t("packet.noDocumentsListed")}
        </p>
      </div>
    );
  }
  return (
    <ul className="flex flex-col gap-1.5">
      {items.map((item, index) => {
        if (item.kind === "group") {
          return (
            <li key={index} className="pt-1.5 text-xs font-semibold text-muted-foreground">
              <Inline text={item.text.replace(/^\*\*|\*\*$/g, "")} />
            </li>
          );
        }
        if (item.kind === "note") {
          return (
            <li key={index} className="text-xs leading-relaxed text-muted-foreground">
              <Inline text={item.text} />
            </li>
          );
        }
        const key = documentKey(result.scheme_id, index, item);
        const checked = Boolean(have[key]);
        return (
          <li key={index}>
            <label className="flex cursor-pointer items-start gap-2.5 text-sm leading-relaxed text-foreground">
              <input
                type="checkbox"
                checked={checked}
                onChange={() => onToggle(key)}
                className="mt-1 size-4 shrink-0 accent-accent"
              />
              <span className={checked ? "text-muted-foreground line-through" : undefined}>
                <Inline text={item.text} />
              </span>
            </label>
            {!checked && showGuides && (
              <p className="print-hidden mt-0.5 ml-6.5 text-xs leading-relaxed text-muted-foreground">
                {item.guide_key
                  ? `${t(`docGuides.${item.guide_key}.where`)} ${t(`docGuides.${item.guide_key}.time`)}`
                  : t("packet.askAtOffice")}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}

/** The on-screen packet inside an entitled result card. */
export function ApplicationPacket({
  result,
  profile,
  have,
  onToggle,
  onPrint,
  extra,
}: {
  result: SchemeResult;
  profile: UserProfile;
  have: DocumentsHave;
  onToggle: (key: string) => void;
  onPrint: () => void;
  /** Assisted-mode controls, rendered after "Before you go". */
  extra?: React.ReactNode;
}) {
  const t = useT();
  const { lines, haveCount } = documentTracker(result, have);
  const confirmations = result.confirmations ?? [];

  const share = () => {
    const text = `${t("packet.shareHeading")}\n${packetShareText(result, have, t)}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank", "noopener,noreferrer");
  };

  return (
    <section
      aria-label={t("packet.title")}
      className="flex flex-col gap-5 rounded-xl border border-accent/30 bg-accent/5 p-4 sm:p-5"
    >
      <div className="flex items-start gap-2.5">
        <ClipboardCheck className="mt-0.5 size-5 shrink-0 text-accent" aria-hidden="true" />
        <div>
          <h4 className="font-serif text-lg font-semibold">{t("packet.title")}</h4>
          <p className="text-sm leading-relaxed text-muted-foreground">{t("packet.lead")}</p>
        </div>
      </div>

      <Worksheet profile={profile} />

      <div>
        <h4 className="text-sm font-semibold text-foreground">
          {t("packet.documentsTitle")}
          {lines.length > 0 && (
            <span className="ml-2 font-normal text-muted-foreground">
              {t("packet.documentsProgress", { have: haveCount, total: lines.length })}
            </span>
          )}
        </h4>
        <div className="mt-2">
          <DocumentTrackerList result={result} have={have} onToggle={onToggle} />
        </div>
      </div>

      <div>
        <h4 className="mb-2 text-sm font-semibold text-foreground">{t("packet.stepsTitle")}</h4>
        <ApplicationSteps modes={result.application_modes ?? []} pageUrl={result.page_url} />
      </div>

      {confirmations.length > 0 && (
        <div className="rounded-lg bg-verdict-info-soft p-3 text-sm leading-relaxed text-verdict-info">
          <p className="font-medium">{t("packet.beforeYouGo")}</p>
          <ul className="mt-1.5 list-disc space-y-1 pl-5">
            {confirmations.map((step) => (
              <li key={step.rule_id}>{step.text}</li>
            ))}
          </ul>
        </div>
      )}

      {extra}

      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" size="sm" onClick={onPrint}>
          <Printer className="size-4" aria-hidden="true" />
          {t("packet.print")}
        </Button>
        <Button variant="secondary" size="sm" onClick={share}>
          <WhatsAppIcon className="size-4" />
          {t("packet.share")}
        </Button>
        <a
          href={result.page_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex h-9 items-center gap-1 px-2 text-sm font-medium text-accent underline-offset-2 hover:underline"
        >
          {t("card.officialPage")} <ExternalLink className="size-3.5" aria-hidden="true" />
        </a>
      </div>
    </section>
  );
}
