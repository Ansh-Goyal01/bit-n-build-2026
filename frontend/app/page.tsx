"use client";

import {
  ArrowRight,
  BadgeCheck,
  BookOpenCheck,
  CodeXml,
  FileText,
  ListChecks,
  MessageCircleQuestion,
  ScrollText,
  Scale,
} from "lucide-react";

import { Container } from "@/components/site/container";
import { ButtonLink } from "@/components/ui/button";
import { useT } from "@/lib/i18n";
import { SCHEME_COUNT } from "@/lib/site";

export default function LandingPage() {
  const t = useT();

  const trustItems = [
    { icon: BookOpenCheck, label: t("marketing.home.trustGrounded") },
    { icon: BadgeCheck, label: t("marketing.home.trustCited") },
    { icon: ListChecks, label: t("marketing.home.trustCovered", { schemeCount: SCHEME_COUNT }) },
    { icon: CodeXml, label: t("marketing.home.trustOpenSource") },
  ];

  const steps = [
    {
      icon: MessageCircleQuestion,
      title: t("marketing.home.step1Title"),
      body: t("marketing.home.step1Body"),
    },
    {
      icon: Scale,
      title: t("marketing.home.step2Title"),
      body: t("marketing.home.step2Body"),
    },
    {
      icon: FileText,
      title: t("marketing.home.step3Title"),
      body: t("marketing.home.step3Body"),
    },
  ];

  const flow = [
    { label: t("marketing.home.flowSituation"), tone: "plain" },
    { label: t("marketing.home.flowRetrieved"), tone: "plain" },
    { label: t("marketing.home.flowDecides"), tone: "accent" },
    { label: t("marketing.home.flowVerifier"), tone: "plain" },
    { label: t("marketing.home.flowCited"), tone: "plain" },
  ];

  return (
    <>
      {/* Hero */}
      <section className="border-b border-border">
        <Container className="flex flex-col items-center py-20 text-center sm:py-24">
          <h1 className="max-w-3xl font-serif text-4xl leading-tight font-semibold tracking-tight text-balance sm:text-5xl md:text-6xl">
            {t("marketing.home.heroTitle")}
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground text-balance">
            {t("marketing.home.heroLead", { schemeCount: SCHEME_COUNT })}
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
            <ButtonLink href="/check" size="lg">
              {t("marketing.home.ctaCheck")}
              <ArrowRight className="size-4.5" aria-hidden="true" />
            </ButtonLink>
            <ButtonLink href="/how-it-works" size="lg" variant="secondary">
              {t("marketing.home.ctaHow")}
            </ButtonLink>
          </div>
          <p className="mt-5 text-sm text-muted-foreground">{t("marketing.home.heroNote")}</p>
        </Container>
      </section>

      {/* Trust strip */}
      <section aria-label={t("marketing.home.trustGrounded")} className="border-b border-border bg-card">
        <Container>
          <ul className="grid grid-cols-2 gap-x-6 gap-y-4 py-6 md:grid-cols-4">
            {trustItems.map(({ icon: Icon, label }) => (
              <li key={label} className="flex items-center justify-center gap-2.5 text-center">
                <Icon className="size-4.5 shrink-0 text-accent" aria-hidden="true" />
                <span className="text-sm font-medium text-foreground">{label}</span>
              </li>
            ))}
          </ul>
        </Container>
      </section>

      {/* How it works */}
      <section aria-labelledby="how-heading">
        <Container className="flex flex-col gap-12 py-20 sm:py-24">
          <div className="flex flex-col items-center gap-3 text-center">
            <h2
              id="how-heading"
              className="font-serif text-3xl font-semibold tracking-tight sm:text-4xl"
            >
              {t("marketing.home.howTitle")}
            </h2>
            <p className="max-w-xl text-muted-foreground">{t("marketing.home.howLead")}</p>
          </div>
          <ol className="grid gap-6 md:grid-cols-3">
            {steps.map(({ icon: Icon, title, body }, index) => (
              <li
                key={title}
                className="flex flex-col gap-4 rounded-xl border border-border bg-card p-6 shadow-card"
              >
                <div className="flex items-center gap-3">
                  <span className="flex size-10 items-center justify-center rounded-lg bg-accent-soft text-accent-soft-foreground">
                    <Icon className="size-5" aria-hidden="true" />
                  </span>
                  <span className="text-sm font-medium text-muted-foreground tabular-nums">
                    {t("marketing.home.stepLabel", { number: index + 1 })}
                  </span>
                </div>
                <h3 className="text-lg leading-snug font-semibold">{title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{body}</p>
              </li>
            ))}
          </ol>
        </Container>
      </section>

      {/* Why this is different */}
      <section aria-labelledby="different-heading" className="border-y border-border bg-card">
        <Container className="grid items-center gap-12 py-20 sm:py-24 lg:grid-cols-2">
          <div className="flex flex-col gap-5">
            <h2
              id="different-heading"
              className="font-serif text-3xl font-semibold tracking-tight text-balance sm:text-4xl"
            >
              {t("marketing.home.differentTitle")}
            </h2>
            <p className="leading-relaxed text-muted-foreground">
              {t("marketing.home.differentBody1")}
            </p>
            <p className="leading-relaxed text-muted-foreground">
              {t("marketing.home.differentBody2")}{" "}
              <strong className="font-semibold text-foreground">
                {t("marketing.home.differentBody2Strong")}
              </strong>{" "}
              {t("marketing.home.differentBody2End")}
            </p>
            <ButtonLink href="/how-it-works" variant="secondary" className="w-fit">
              {t("marketing.home.readFull")}
            </ButtonLink>
          </div>

          <div className="flex flex-col gap-3" aria-hidden="true">
            {flow.map(({ label, tone }, index, list) => (
              <div key={label} className="flex flex-col items-center gap-3">
                <div
                  className={
                    tone === "accent"
                      ? "w-full rounded-lg border border-primary bg-accent-soft px-5 py-3.5 text-center text-sm font-semibold text-accent-soft-foreground"
                      : "w-full rounded-lg border border-border bg-background px-5 py-3.5 text-center text-sm font-medium text-foreground"
                  }
                >
                  {label}
                </div>
                {index < list.length - 1 && <span className="h-4 w-px bg-border" />}
              </div>
            ))}
          </div>
        </Container>
      </section>

      {/* Closing CTA */}
      <section aria-labelledby="cta-heading">
        <Container className="flex flex-col items-center gap-6 py-20 text-center sm:py-24">
          <span className="flex size-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <ScrollText className="size-6" aria-hidden="true" />
          </span>
          <h2
            id="cta-heading"
            className="max-w-2xl font-serif text-3xl font-semibold tracking-tight text-balance sm:text-4xl"
          >
            {t("marketing.home.closingTitle")}
          </h2>
          <ButtonLink href="/check" size="lg">
            {t("marketing.home.ctaCheck")}
            <ArrowRight className="size-4.5" aria-hidden="true" />
          </ButtonLink>
        </Container>
      </section>
    </>
  );
}
