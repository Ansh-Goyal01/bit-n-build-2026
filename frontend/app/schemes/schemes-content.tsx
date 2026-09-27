"use client";

import { SchemeCatalog } from "@/components/schemes/catalog";
import { Container } from "@/components/site/container";
import { CHANGED_COUNT, FRESHNESS, LAST_CHECKED } from "@/lib/freshness";
import { useT } from "@/lib/i18n";
import { SCHEME_COUNT } from "@/lib/site";

export function SchemesContent() {
  const t = useT();

  return (
    <Container className="flex flex-col gap-8 py-10 sm:py-14">
      <div className="flex max-w-2xl flex-col gap-3">
        <h1 className="font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
          {t("catalog.title")}
        </h1>
        <p className="leading-relaxed text-muted-foreground">
          {t("catalog.lead", { schemeCount: SCHEME_COUNT })}
        </p>
        {FRESHNESS && LAST_CHECKED && (
          <p className="text-sm leading-relaxed text-muted-foreground">
            {CHANGED_COUNT === 0
              ? t("catalog.freshnessUnchanged", {
                  checked: FRESHNESS.schemes_checked,
                  date: LAST_CHECKED,
                })
              : t("catalog.freshnessChanged", {
                  checked: FRESHNESS.schemes_checked,
                  date: LAST_CHECKED,
                  changed: CHANGED_COUNT,
                })}
          </p>
        )}
      </div>
      <SchemeCatalog />
    </Container>
  );
}
