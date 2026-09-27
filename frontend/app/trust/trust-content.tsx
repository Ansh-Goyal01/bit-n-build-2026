"use client";

import { AlertTriangle, ArrowRight, CircleCheck, ExternalLink, MinusCircle, ShieldCheck } from "lucide-react";

import { Container } from "@/components/site/container";
import { ButtonLink } from "@/components/ui/button";
import { useT } from "@/lib/i18n";
import { CHANGED_COUNT, getDrift, LAST_CHECKED, wasChecked } from "@/lib/freshness";
import { CATEGORY_LABELS, SCHEMES, type SchemeData } from "@/lib/schemes";
import { RULE_COUNT, SCHEME_COUNT } from "@/lib/site";

type SourceStatus = "verified" | "drift" | "uncovered";

/** Freshness status for one scheme: drifted text wins, then monitor coverage. */
function statusOf(scheme: SchemeData): SourceStatus {
  if (getDrift(scheme.scheme_id)) return "drift";
  return wasChecked(scheme) ? "verified" : "uncovered";
}

const STATUS_STYLE: Record<SourceStatus, string> = {
  verified: "border-emerald-600/20 bg-emerald-600/10 text-emerald-700 dark:text-emerald-400",
  drift: "border-amber-600/20 bg-amber-600/10 text-amber-700 dark:text-amber-400",
  uncovered: "border-border bg-muted text-muted-foreground",
};

const STATUS_ICON: Record<SourceStatus, typeof CircleCheck> = {
  verified: CircleCheck,
  drift: AlertTriangle,
  uncovered: MinusCircle,
};

export function TrustContent() {
  const t = useT();

  // The eligibility check only decides on live, in-scope schemes — the same set
  // SCHEME_COUNT reports — so the provenance table mirrors exactly what ships.
  const liveSchemes = SCHEMES.filter(
    (scheme) => scheme.rules.length > 0 && !scheme.out_of_scope,
  ).sort((a, b) => a.short_name.localeCompare(b.short_name));

  const stats = [
    { value: SCHEME_COUNT, label: t("marketing.trust.statSchemes"), note: t("marketing.trust.statSchemesNote") },
    { value: RULE_COUNT, label: t("marketing.trust.statRules"), note: t("marketing.trust.statRulesNote") },
    { value: CHANGED_COUNT, label: t("marketing.trust.statDrift"), note: t("marketing.trust.statDriftNote") },
  ];

  return (
    <Container className="flex max-w-5xl flex-col gap-12 py-10 sm:py-14">
      {/* Hero */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-2 text-accent">
          <ShieldCheck className="size-5" aria-hidden="true" />
          <span className="text-sm font-medium tracking-wide uppercase">{t("nav.trust")}</span>
        </div>
        <h1 className="font-serif text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
          {t("marketing.trust.title")}
        </h1>
        <p className="max-w-3xl leading-relaxed text-muted-foreground">{t("marketing.trust.intro")}</p>
        <p className="text-sm text-muted-foreground">
          {t("marketing.trust.lastCheckedLabel")}:{" "}
          <span className="font-medium text-foreground">
            {LAST_CHECKED ?? t("marketing.trust.neverChecked")}
          </span>
        </p>
      </div>

      {/* Stats */}
      <section aria-label="Provenance at a glance" className="grid gap-4 sm:grid-cols-3">
        {stats.map((stat) => (
          <div key={stat.label} className="flex flex-col gap-1 rounded-xl border border-border bg-card p-5 shadow-card">
            <span className="font-serif text-3xl font-semibold tracking-tight">{stat.value}</span>
            <span className="text-sm font-medium text-foreground">{stat.label}</span>
            <span className="text-xs leading-relaxed text-muted-foreground">{stat.note}</span>
          </div>
        ))}
      </section>

      {/* How freshness works */}
      <section aria-labelledby="how-heading" className="flex flex-col gap-3">
        <h2 id="how-heading" className="font-serif text-2xl font-semibold tracking-tight">
          {t("marketing.trust.howTitle")}
        </h2>
        <p className="leading-relaxed text-muted-foreground">{t("marketing.trust.howBody")}</p>
      </section>

      {/* Provenance table */}
      <section aria-labelledby="table-heading" className="flex flex-col gap-3">
        <h2 id="table-heading" className="font-serif text-2xl font-semibold tracking-tight">
          {t("marketing.trust.tableTitle")}
        </h2>
        <p className="text-sm text-muted-foreground">{t("marketing.trust.tableCaption")}</p>

        <div className="overflow-x-auto rounded-xl border border-border shadow-card">
          <table className="w-full min-w-[40rem] border-collapse text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/50 text-left">
                <th scope="col" className="px-4 py-3 font-medium">{t("marketing.trust.colScheme")}</th>
                <th scope="col" className="px-4 py-3 text-center font-medium">{t("marketing.trust.colRules")}</th>
                <th scope="col" className="px-4 py-3 font-medium">{t("marketing.trust.colStatus")}</th>
                <th scope="col" className="px-4 py-3 font-medium">{t("marketing.trust.colSource")}</th>
              </tr>
            </thead>
            <tbody>
              {liveSchemes.map((scheme) => {
                const status = statusOf(scheme);
                const StatusIcon = STATUS_ICON[status];
                const statusLabel =
                  status === "verified"
                    ? t("marketing.trust.statusVerified", { date: LAST_CHECKED ?? "" })
                    : status === "drift"
                      ? t("marketing.trust.statusDrift")
                      : t("marketing.trust.statusUncovered");
                return (
                  <tr key={scheme.scheme_id} className="border-b border-border last:border-0 hover:bg-muted/30">
                    <td className="px-4 py-3">
                      <a
                        href={`/schemes/${scheme.scheme_id}`}
                        className="font-medium text-foreground underline-offset-2 hover:text-accent hover:underline"
                      >
                        {scheme.short_name}
                      </a>
                      <span className="block text-xs text-muted-foreground">
                        {CATEGORY_LABELS[scheme.category] ?? scheme.category}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center tabular-nums text-muted-foreground">
                      {scheme.rules.length}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${STATUS_STYLE[status]}`}
                      >
                        <StatusIcon className="size-3.5" aria-hidden="true" />
                        {statusLabel}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <a
                        href={scheme.page_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-accent underline-offset-2 hover:underline"
                      >
                        {t("marketing.trust.openSource")}
                        <ExternalLink className="size-3.5" aria-hidden="true" />
                      </a>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <p className="rounded-xl border border-border bg-card p-5 text-sm leading-relaxed text-muted-foreground shadow-card">
          {t("marketing.trust.disclaimer")}
        </p>
      </section>

      {/* CTA */}
      <div className="flex flex-col items-center gap-4 rounded-xl border border-border bg-card p-8 text-center shadow-card">
        <p className="max-w-md font-serif text-xl font-semibold tracking-tight text-balance">
          {t("marketing.trust.ctaTitle")}
        </p>
        <ButtonLink href="/schemes">
          {t("marketing.trust.ctaLink")}
          <ArrowRight className="size-4" aria-hidden="true" />
        </ButtonLink>
      </div>
    </Container>
  );
}
