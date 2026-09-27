"use client";

import {
  ArrowRight,
  BadgeCheck,
  BookOpenCheck,
  FileSearch,
  MessageCircleQuestion,
  Scale,
  ShieldCheck,
} from "lucide-react";

import { Container } from "@/components/site/container";
import { ButtonLink } from "@/components/ui/button";
import { useT } from "@/lib/i18n";
import { OUT_OF_SCOPE_COUNT, PENDING_COUNT, RULE_COUNT, SCHEME_COUNT } from "@/lib/site";

export function HowItWorksContent() {
  const t = useT();

  const pipeline = [
    { icon: MessageCircleQuestion, title: t("marketing.howItWorks.pipe1Title"), body: t("marketing.howItWorks.pipe1Body") },
    {
      icon: FileSearch,
      title: t("marketing.howItWorks.pipe2Title"),
      body: t("marketing.howItWorks.pipe2Body", { schemeCount: SCHEME_COUNT, ruleCount: RULE_COUNT }),
    },
    { icon: Scale, title: t("marketing.howItWorks.pipe3Title"), body: t("marketing.howItWorks.pipe3Body") },
    { icon: ShieldCheck, title: t("marketing.howItWorks.pipe4Title"), body: t("marketing.howItWorks.pipe4Body") },
    { icon: BadgeCheck, title: t("marketing.howItWorks.pipe5Title"), body: t("marketing.howItWorks.pipe5Body") },
  ];

  const principles = [
    { title: t("marketing.howItWorks.prin1Title"), body: t("marketing.howItWorks.prin1Body") },
    { title: t("marketing.howItWorks.prin2Title"), body: t("marketing.howItWorks.prin2Body") },
    { title: t("marketing.howItWorks.prin3Title"), body: t("marketing.howItWorks.prin3Body") },
    { title: t("marketing.howItWorks.prin4Title"), body: t("marketing.howItWorks.prin4Body") },
    { title: t("marketing.howItWorks.prin5Title"), body: t("marketing.howItWorks.prin5Body") },
    { title: t("marketing.howItWorks.prin6Title"), body: t("marketing.howItWorks.prin6Body") },
  ];

  const coverage = t("marketing.howItWorks.limitCoverage", {
    schemeCount: SCHEME_COUNT,
    pendingCount: PENDING_COUNT,
  });
  const limitations = [
    OUT_OF_SCOPE_COUNT === 1
      ? `${coverage} ${t("marketing.howItWorks.limitOutOfScope")}`
      : coverage,
    t("marketing.howItWorks.limitStates"),
    t("marketing.howItWorks.limitSelfReported"),
    t("marketing.howItWorks.limitSimplified"),
    t("marketing.howItWorks.limitLanguages"),
  ];

  const stats = [
    { value: "0", accent: true, caption: t("marketing.howItWorks.statFpCaption") },
    { value: "91%", accent: false, caption: t("marketing.howItWorks.statAccCaption") },
    { value: "2.7×", accent: false, caption: t("marketing.howItWorks.statFaithCaption") },
  ];

  return (
    <Container className="flex max-w-3xl flex-col gap-14 py-10 sm:py-14">
      {/* Intro */}
      <div className="flex flex-col gap-4">
        <h1 className="font-serif text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
          {t("marketing.howItWorks.title")}
        </h1>
        <p className="leading-relaxed text-muted-foreground">{t("marketing.howItWorks.intro")}</p>
      </div>

      {/* Pipeline */}
      <section aria-labelledby="pipeline-heading" className="flex flex-col gap-6">
        <h2 id="pipeline-heading" className="font-serif text-2xl font-semibold tracking-tight">
          {t("marketing.howItWorks.pipelineTitle")}
        </h2>
        <ol className="flex flex-col">
          {pipeline.map(({ icon: Icon, title, body }, index) => (
            <li key={title} className="relative flex gap-4 pb-8 last:pb-0">
              {index < pipeline.length - 1 && (
                <span
                  aria-hidden="true"
                  className="absolute top-11 left-5 h-[calc(100%-2.75rem)] w-px bg-border"
                />
              )}
              <span className="z-10 flex size-10 shrink-0 items-center justify-center rounded-lg border border-border bg-card text-accent shadow-card">
                <Icon className="size-5" aria-hidden="true" />
              </span>
              <div className="flex flex-col gap-1 pt-1">
                <h3 className="font-semibold">{title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* Measured, honestly */}
      <section
        aria-labelledby="measured-heading"
        className="flex flex-col gap-4 rounded-xl border border-border bg-card p-6 shadow-card"
      >
        <h2 id="measured-heading" className="font-serif text-2xl font-semibold tracking-tight">
          {t("marketing.howItWorks.measuredTitle")}
        </h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {t("marketing.howItWorks.measuredLead")}
        </p>
        <div className="grid gap-4 sm:grid-cols-3">
          {stats.map(({ value, accent, caption }) => (
            <div key={caption} className="flex flex-col gap-1 rounded-lg bg-background p-4">
              <span
                className={
                  accent
                    ? "font-serif text-3xl font-semibold text-verdict-yes"
                    : "font-serif text-3xl font-semibold text-foreground"
                }
              >
                {value}
              </span>
              <span className="text-sm leading-snug text-muted-foreground">{caption}</span>
            </div>
          ))}
        </div>
        <p className="text-xs leading-relaxed text-muted-foreground">
          {t("marketing.howItWorks.measuredNote")}
        </p>
      </section>

      {/* Principles */}
      <section aria-labelledby="principles-heading" className="flex flex-col gap-6">
        <h2 id="principles-heading" className="font-serif text-2xl font-semibold tracking-tight">
          {t("marketing.howItWorks.principlesTitle")}
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {principles.map(({ title, body }) => (
            <div
              key={title}
              className="flex flex-col gap-2 rounded-xl border border-border bg-card p-5 shadow-card"
            >
              <h3 className="flex items-start gap-2 font-semibold">
                <BookOpenCheck className="mt-0.5 size-4.5 shrink-0 text-accent" aria-hidden="true" />
                {title}
              </h3>
              <p className="text-sm leading-relaxed text-muted-foreground">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Limitations */}
      <section aria-labelledby="limits-heading" className="flex flex-col gap-4">
        <h2 id="limits-heading" className="font-serif text-2xl font-semibold tracking-tight">
          {t("marketing.howItWorks.limitsTitle")}
        </h2>
        <ul className="flex flex-col gap-2.5">
          {limitations.map((item) => (
            <li key={item} className="flex gap-2.5 text-sm leading-relaxed text-muted-foreground">
              <span aria-hidden="true" className="mt-2 size-1.5 shrink-0 rounded-full bg-border" />
              {item}
            </li>
          ))}
        </ul>
      </section>

      {/* CTA */}
      <div className="flex flex-col items-center gap-4 rounded-xl border border-border bg-card p-8 text-center shadow-card">
        <p className="max-w-md font-serif text-xl font-semibold tracking-tight text-balance">
          {t("marketing.howItWorks.closing")}
        </p>
        <ButtonLink href="/check">
          {t("marketing.home.ctaCheck")}
          <ArrowRight className="size-4" aria-hidden="true" />
        </ButtonLink>
      </div>
    </Container>
  );
}
