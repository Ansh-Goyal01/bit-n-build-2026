"use client";

import { ArrowRight, ExternalLink } from "lucide-react";

import { Container } from "@/components/site/container";
import { ButtonLink } from "@/components/ui/button";
import { useT } from "@/lib/i18n";
import { GITHUB_URL, MYSCHEME_URL, SCHEME_COUNT } from "@/lib/site";

export function AboutContent() {
  const t = useT();

  return (
    <Container className="flex max-w-3xl flex-col gap-12 py-10 sm:py-14">
      <div className="flex flex-col gap-4">
        <h1 className="font-serif text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
          {t("marketing.about.title")}
        </h1>
        <p className="leading-relaxed text-muted-foreground">{t("marketing.about.intro1")}</p>
        <p className="leading-relaxed text-muted-foreground">
          {t("marketing.about.intro2", { schemeCount: SCHEME_COUNT })}
        </p>
      </div>

      <section aria-labelledby="open-heading" className="flex flex-col gap-3">
        <h2 id="open-heading" className="font-serif text-2xl font-semibold tracking-tight">
          {t("marketing.about.openTitle")}
        </h2>
        <p className="leading-relaxed text-muted-foreground">{t("marketing.about.openBody")}</p>
        <div className="flex flex-wrap gap-x-5 gap-y-2 pt-1">
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-sm font-medium text-accent underline-offset-2 hover:underline"
          >
            {t("marketing.about.linkSource")}
            <ExternalLink className="size-3.5" aria-hidden="true" />
          </a>
          <a
            href={MYSCHEME_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-sm font-medium text-accent underline-offset-2 hover:underline"
          >
            {t("marketing.about.linkMyscheme")}
            <ExternalLink className="size-3.5" aria-hidden="true" />
          </a>
        </div>
      </section>

      <section aria-labelledby="privacy-heading" className="flex flex-col gap-3">
        <h2 id="privacy-heading" className="font-serif text-2xl font-semibold tracking-tight">
          {t("marketing.about.privacyTitle")}
        </h2>
        <p className="leading-relaxed text-muted-foreground">{t("marketing.about.privacyBody")}</p>
      </section>

      <section aria-labelledby="disclaimer-heading" className="flex flex-col gap-3">
        <h2 id="disclaimer-heading" className="font-serif text-2xl font-semibold tracking-tight">
          {t("marketing.about.finePrintTitle")}
        </h2>
        <p className="rounded-xl border border-border bg-card p-5 text-sm leading-relaxed text-muted-foreground shadow-card">
          {t("footer.disclaimer")}
        </p>
      </section>

      <section aria-labelledby="contact-heading" className="flex flex-col gap-3">
        <h2 id="contact-heading" className="font-serif text-2xl font-semibold tracking-tight">
          {t("marketing.about.contactTitle")}
        </h2>
        <p className="leading-relaxed text-muted-foreground">
          {t("marketing.about.contactBody")}{" "}
          <a
            href={`${GITHUB_URL}/issues`}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-accent underline-offset-2 hover:underline"
          >
            {t("marketing.about.contactLink")}
          </a>{" "}
          {t("marketing.about.contactEnd")}
        </p>
      </section>

      <div className="flex flex-col items-center gap-4 rounded-xl border border-border bg-card p-8 text-center shadow-card">
        <p className="max-w-md font-serif text-xl font-semibold tracking-tight text-balance">
          {t("marketing.about.closing")}
        </p>
        <ButtonLink href="/check">
          {t("marketing.home.ctaCheck")}
          <ArrowRight className="size-4" aria-hidden="true" />
        </ButtonLink>
      </div>
    </Container>
  );
}
