"use client";

import { MapPin } from "lucide-react";

import { Chip } from "@/components/ui/chip";
import { useT } from "@/lib/i18n";
import { getScheme } from "@/lib/schemes";

/** "State scheme — Uttar Pradesh" for a state government scheme; nothing for
 * central schemes. The state name is a proper noun and stays untranslated. */
export function SchemeLevelBadge({ schemeId }: { schemeId: string }) {
  const t = useT();
  const scheme = getScheme(schemeId);
  if (scheme?.level !== "state" || !scheme.state) return null;
  return (
    <Chip tone="accent">
      <MapPin aria-hidden="true" />
      {t("catalog.stateScheme", { state: scheme.state })}
    </Chip>
  );
}
