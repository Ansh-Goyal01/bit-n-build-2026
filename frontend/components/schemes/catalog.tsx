"use client";

// Searchable, filterable scheme catalog. All data is static — filtering is
// instant and works even when the backend is asleep.
import * as React from "react";
import Link from "next/link";
import { ArrowRight, Search, SearchX } from "lucide-react";

import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { SchemeLevelBadge } from "@/components/schemes/scheme-level-badge";
import { useT } from "@/lib/i18n";
import { AUDIENCES_ALL, CATEGORIES, SCHEMES, STATES, audiencesOf } from "@/lib/schemes";

export function SchemeCatalog() {
  const t = useT();
  const [query, setQuery] = React.useState("");
  const [category, setCategory] = React.useState("");
  const [audience, setAudience] = React.useState("");
  // "" = all, "central", or a state name (state schemes for that state).
  const [level, setLevel] = React.useState("");

  const filtered = SCHEMES.filter((scheme) => {
    if (category && scheme.category !== category) return false;
    if (audience && !audiencesOf(scheme.scheme_id).includes(audience)) return false;
    if (level === "central" && scheme.level !== "central") return false;
    if (level && level !== "central" && scheme.state !== level) return false;
    if (query) {
      const haystack =
        `${scheme.short_name} ${scheme.name} ${scheme.ministry} ${scheme.benefit_snippet}`.toLowerCase();
      if (!haystack.includes(query.toLowerCase().trim())) return false;
    }
    return true;
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_auto_auto_auto]">
        <div className="relative">
          <Search
            className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            type="search"
            aria-label={t("catalog.searchLabel")}
            placeholder={t("catalog.searchPlaceholder")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select
          aria-label={t("catalog.filterLevelLabel")}
          value={level}
          onChange={(e) => setLevel(e.target.value)}
          className="lg:w-52"
        >
          <option value="">{t("catalog.allLevels")}</option>
          <option value="central">{t("catalog.centralSchemes")}</option>
          {STATES.map((state) => (
            <option key={state} value={state}>
              {t("catalog.stateScheme", { state })}
            </option>
          ))}
        </Select>
        <Select
          aria-label={t("catalog.filterCategoryLabel")}
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="lg:w-44"
        >
          <option value="">{t("catalog.allCategories")}</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {t(`catalog.categories.${c}`)}
            </option>
          ))}
        </Select>
        <Select
          aria-label={t("catalog.filterAudienceLabel")}
          value={audience}
          onChange={(e) => setAudience(e.target.value)}
          className="lg:w-52"
        >
          <option value="">{t("catalog.everyone")}</option>
          {AUDIENCES_ALL.map((value) => (
            <option key={value} value={value}>
              {t(`catalog.audiences.${value}`)}
            </option>
          ))}
        </Select>
      </div>

      <p className="text-sm text-muted-foreground" role="status">
        {t("catalog.showing", { shown: filtered.length, total: SCHEMES.length })}
      </p>

      {filtered.length === 0 ? (
        <EmptyState
          icon={SearchX}
          title={t("catalog.emptyTitle")}
          body={t("catalog.emptyBody")}
          action={
            <Button
              variant="secondary"
              onClick={() => {
                setQuery("");
                setCategory("");
                setAudience("");
                setLevel("");
              }}
            >
              {t("catalog.emptyClear")}
            </Button>
          }
        />
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((scheme) => (
            <li key={scheme.scheme_id}>
              <Link
                href={`/schemes/${scheme.scheme_id}`}
                className="group flex h-full flex-col gap-3 rounded-xl border border-border bg-card p-5 shadow-card transition-all duration-150 ease-soft hover:border-input hover:shadow-raised"
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="font-serif text-lg leading-snug font-semibold">
                    {scheme.short_name}
                  </span>
                  <span className="flex flex-wrap justify-end gap-1.5">
                    {scheme.out_of_scope ? (
                      <Chip tone="neutral">{t("catalog.individualsOnly")}</Chip>
                    ) : (
                      scheme.rules.length === 0 && (
                        <Chip tone="info">{t("catalog.comingSoon")}</Chip>
                      )
                    )}
                    <SchemeLevelBadge schemeId={scheme.scheme_id} />
                    <Chip tone="neutral">{t(`catalog.categories.${scheme.category}`)}</Chip>
                  </span>
                </div>
                <p className="text-sm leading-snug text-muted-foreground">{scheme.name}</p>
                <p className="line-clamp-3 text-sm leading-relaxed text-foreground/80">
                  {scheme.benefit_snippet}
                </p>
                <span className="mt-auto flex items-center gap-1 pt-1 text-sm font-medium text-accent">
                  {t("catalog.viewDetails")}
                  <ArrowRight
                    className="size-3.5 transition-transform duration-150 group-hover:translate-x-0.5"
                    aria-hidden="true"
                  />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
