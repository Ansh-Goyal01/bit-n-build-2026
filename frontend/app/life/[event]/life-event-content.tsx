"use client";

import { ArrowRight, Sparkles } from "lucide-react";

import { Container } from "@/components/site/container";
import { ButtonLink } from "@/components/ui/button";
import { useT } from "@/lib/i18n";
import schemes from "@/lib/data/schemes.json";
import { lifeEventByKey } from "@/lib/life-events";

export function LifeEventContent({ eventKey }: { eventKey: string }) {
  const t = useT();
  const event = lifeEventByKey(eventKey);
  if (!event) return null; // the server component already 404s unknown keys

  const shortNames = schemes
    .filter((scheme) => event.schemeIds.includes(scheme.scheme_id))
    .map((scheme) => scheme.short_name);

  return (
    <Container className="flex max-w-2xl flex-col items-center gap-8 py-16 text-center sm:py-24">
      <p className="flex items-center gap-2 text-sm font-medium text-accent">
        <Sparkles className="size-4" aria-hidden="true" />
        {t("marketing.lifeEvents.eyebrow")}
      </p>
      <h1 className="font-serif text-3xl leading-tight font-semibold tracking-tight text-balance sm:text-5xl">
        {t(`marketing.lifeEvents.${event.key}Title`)}
      </h1>
      <p className="max-w-xl text-lg leading-relaxed text-muted-foreground text-balance">
        {t(`marketing.lifeEvents.${event.key}Lead`)}
      </p>

      {shortNames.length > 0 && (
        <div className="flex flex-col items-center gap-2.5">
          <p className="text-sm font-medium text-muted-foreground">
            {t("marketing.lifeEvents.relevantTitle")}
          </p>
          <ul className="flex flex-wrap items-center justify-center gap-2">
            {shortNames.map((name) => (
              <li
                key={name}
                className="rounded-full border border-border bg-card px-3.5 py-1.5 text-sm font-medium text-foreground shadow-card"
              >
                {name}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex flex-col items-center gap-3">
        <ButtonLink href={`/check?life=${event.key}`} size="lg">
          {t("marketing.lifeEvents.startCheck")}
          <ArrowRight className="size-4.5" aria-hidden="true" />
        </ButtonLink>
        <p className="text-sm text-muted-foreground">{t("marketing.lifeEvents.ctaNote")}</p>
      </div>
    </Container>
  );
}
