"use client";

import * as React from "react";
import { ChevronDown, Flag, RefreshCw, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { type FeedbackReport, ApiError, sendFeedback } from "@/lib/api";
import { useT } from "@/lib/i18n";
import type { SchemeResult } from "@/lib/types";
import { cn } from "@/lib/utils";

const CATEGORIES: FeedbackReport["category"][] = [
  "wrong_verdict",
  "missing_scheme",
  "translation",
  "documents",
  "other",
];

type SendState =
  | { kind: "idle" }
  | { kind: "busy" }
  | { kind: "sent" }
  | { kind: "error"; message: string };

/** Report-an-issue form, collapsed by default under the report. Sends only
 * category + optional scheme + free text; the profile never leaves the
 * assessment flow, and the endpoint stores no contact details by design. */
export function FeedbackForm({ results, lang }: { results: SchemeResult[]; lang: string }) {
  const t = useT();
  const [open, setOpen] = React.useState(false);
  const [category, setCategory] = React.useState<FeedbackReport["category"]>("wrong_verdict");
  const [schemeId, setSchemeId] = React.useState("");
  const [message, setMessage] = React.useState("");
  const [state, setState] = React.useState<SendState>({ kind: "idle" });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim().length < 3 || state.kind === "busy") return;
    setState({ kind: "busy" });
    try {
      await sendFeedback({
        category,
        scheme_id: schemeId || null,
        message: message.trim(),
        lang,
      });
      setState({ kind: "sent" });
      setMessage("");
    } catch (error) {
      setState({
        kind: "error",
        message: error instanceof ApiError ? error.message : t("feedback.error"),
      });
    }
  };

  return (
    <section aria-label={t("feedback.title")} className="print-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex items-center gap-2 text-sm font-medium text-muted-foreground transition-colors hover:text-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        <Flag className="size-4" aria-hidden="true" />
        {t("feedback.title")}
        <ChevronDown
          className={cn("size-4 transition-transform", open && "rotate-180")}
          aria-hidden="true"
        />
      </button>

      {open && (
        <form
          onSubmit={(e) => void submit(e)}
          className="mt-4 flex flex-col gap-4 rounded-xl border border-border bg-card p-5"
        >
          <p className="text-sm leading-relaxed text-muted-foreground">{t("feedback.lead")}</p>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field id="feedback-category" label={t("feedback.category")}>
              <Select
                value={category}
                onChange={(e) => setCategory(e.target.value as FeedbackReport["category"])}
              >
                {CATEGORIES.map((value) => (
                  <option key={value} value={value}>
                    {t(`feedback.categories.${value}`)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field id="feedback-scheme" label={t("feedback.scheme")} optional>
              <Select value={schemeId} onChange={(e) => setSchemeId(e.target.value)}>
                <option value="">{t("feedback.schemeNone")}</option>
                {results.map((result) => (
                  <option key={result.scheme_id} value={result.scheme_id}>
                    {result.short_name}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <Field id="feedback-message" label={t("feedback.message")} help={t("feedback.noPii")}>
            <textarea
              rows={4}
              maxLength={2000}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className="w-full rounded-lg border border-input bg-card px-3.5 py-2.5 text-base leading-relaxed text-foreground placeholder:text-muted-foreground transition-colors duration-150 aria-invalid:border-destructive"
            />
          </Field>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="submit"
              variant="secondary"
              className="w-fit"
              disabled={message.trim().length < 3 || state.kind === "busy"}
            >
              {state.kind === "busy" ? (
                <RefreshCw className="size-4 animate-spin" aria-hidden="true" />
              ) : (
                <Send className="size-4" aria-hidden="true" />
              )}
              {state.kind === "busy" ? t("feedback.sending") : t("feedback.submit")}
            </Button>
            <span aria-live="polite" className="text-sm leading-relaxed">
              {state.kind === "sent" && (
                <span className="text-verdict-yes">{t("feedback.sent")}</span>
              )}
              {state.kind === "error" && (
                <span role="alert" className="text-destructive">
                  {state.message}
                </span>
              )}
            </span>
          </div>
        </form>
      )}
    </section>
  );
}
