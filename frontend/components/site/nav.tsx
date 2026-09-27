"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, ScrollText, X } from "lucide-react";

import { Container } from "@/components/site/container";
import { LanguageSwitcher } from "@/components/site/language-switcher";
import { ButtonLink } from "@/components/ui/button";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/how-it-works", key: "nav.howItWorks" },
  { href: "/schemes", key: "nav.exploreSchemes" },
  { href: "/trust", key: "nav.trust" },
  { href: "/about", key: "nav.about" },
];

export function SiteNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const t = useT();

  return (
    <header className="print-hidden sticky top-0 z-40 border-b border-border bg-background">
      <Container className="flex h-16 items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <ScrollText className="size-4.5" aria-hidden="true" />
          </span>
          <span className="font-serif text-lg font-semibold tracking-tight">
            Adhikaar
          </span>
        </Link>

        <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
          {LINKS.map(({ href, key }) => (
            <Link
              key={href}
              href={href}
              aria-current={pathname === href ? "page" : undefined}
              className={cn(
                "rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors duration-150 hover:bg-muted hover:text-foreground",
                pathname === href && "text-foreground",
              )}
            >
              {t(key)}
            </Link>
          ))}
          <LanguageSwitcher className="ml-1" />
          <ButtonLink href="/check" className="ml-2">
            {t("nav.checkEligibility")}
          </ButtonLink>
        </nav>

        <div className="flex min-w-0 items-center gap-2 md:hidden">
          <LanguageSwitcher />
          {/* Long CTA translations (ta, ml, te…) can't fit a 390px row —
              below sm the CTA lives in the menu panel instead. */}
          <ButtonLink href="/check" size="sm" className="max-sm:hidden">
            {t("nav.checkEligibility")}
          </ButtonLink>
          <button
            type="button"
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? t("nav.closeMenu") : t("nav.openMenu")}
            onClick={() => setOpen((v) => !v)}
            className="flex size-10 items-center justify-center rounded-lg text-foreground transition-colors duration-150 hover:bg-muted"
          >
            {open ? (
              <X className="size-5" aria-hidden="true" />
            ) : (
              <Menu className="size-5" aria-hidden="true" />
            )}
          </button>
        </div>
      </Container>

      {open && (
        <nav
          id="mobile-menu"
          aria-label="Main"
          className="border-t border-border bg-background md:hidden"
        >
          <Container className="flex flex-col gap-1 py-3">
            {LINKS.map(({ href, key }) => (
              <Link
                key={href}
                href={href}
                aria-current={pathname === href ? "page" : undefined}
                onClick={() => setOpen(false)}
                className="rounded-md px-3 py-2.5 text-base text-foreground transition-colors duration-150 hover:bg-muted"
              >
                {t(key)}
              </Link>
            ))}
            <ButtonLink
              href="/check"
              size="sm"
              className="mt-1 w-fit sm:hidden"
              onClick={() => setOpen(false)}
            >
              {t("nav.checkEligibility")}
            </ButtonLink>
          </Container>
        </nav>
      )}
    </header>
  );
}
