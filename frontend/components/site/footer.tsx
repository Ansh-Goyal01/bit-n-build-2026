"use client";

import Link from "next/link";

import { Container } from "@/components/site/container";
import { useT } from "@/lib/i18n";
import { GITHUB_URL, MYSCHEME_URL } from "@/lib/site";

const LINKS = [
  { href: "/how-it-works", key: "nav.howItWorks" },
  { href: "/schemes", key: "nav.exploreSchemes" },
  { href: "/about", key: "nav.about" },
  { href: "/check", key: "nav.checkEligibility" },
];

export function SiteFooter() {
  const t = useT();
  return (
    <footer className="print-hidden mt-auto border-t border-border bg-card">
      <Container className="grid gap-8 py-12 md:grid-cols-[2fr_1fr_1fr]">
        <div className="flex max-w-md flex-col gap-3">
          <p className="font-serif text-lg font-semibold tracking-tight">Adhikaar</p>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {t("footer.disclaimer")}
          </p>
        </div>

        <nav aria-label="Footer" className="flex flex-col gap-2">
          <p className="text-sm font-semibold">{t("footer.explore")}</p>
          {LINKS.map(({ href, key }) => (
            <Link
              key={href}
              href={href}
              className="w-fit text-sm text-muted-foreground transition-colors duration-150 hover:text-foreground"
            >
              {t(key)}
            </Link>
          ))}
        </nav>

        <div className="flex flex-col gap-2">
          <p className="text-sm font-semibold">{t("footer.sources")}</p>
          <a
            href={MYSCHEME_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="w-fit text-sm text-muted-foreground transition-colors duration-150 hover:text-foreground"
          >
            {t("footer.myscheme")}
          </a>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="w-fit text-sm text-muted-foreground transition-colors duration-150 hover:text-foreground"
          >
            {t("footer.sourceCode")}
          </a>
        </div>
      </Container>
      <div className="border-t border-border">
        <Container className="py-4">
          <p className="text-xs text-muted-foreground">{t("footer.copyrightNote")}</p>
        </Container>
      </div>
    </footer>
  );
}
