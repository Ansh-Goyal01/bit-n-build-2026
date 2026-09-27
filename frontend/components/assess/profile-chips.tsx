"use client";

import { useT } from "@/lib/i18n";
import type { UserProfile } from "@/lib/types";

type T = ReturnType<typeof useT>;

/** Translate an enumerated profile value; unknown values fall back to the
 * canonical English value (t() returns the key path when a key is missing). */
function val(t: T, group: string, value: string): string {
  const key = `chips.${group}.${value}`;
  const out = t(key);
  return out === key ? value : out;
}

function describe(t: T, profile: UserProfile): string[] {
  const chips: string[] = [];
  if (profile.age != null) chips.push(t("chips.yearsOld", { age: profile.age }));
  if (profile.gender) chips.push(val(t, "gender", profile.gender));
  if (profile.marital_status) chips.push(val(t, "marital", profile.marital_status));
  if (profile.occupation) chips.push(val(t, "occupation", profile.occupation));
  if (profile.state) chips.push(profile.state);
  if (profile.area) chips.push(val(t, "area", profile.area));
  if (profile.annual_family_income_inr != null)
    chips.push(
      t("chips.income", { amount: profile.annual_family_income_inr.toLocaleString("en-IN") }),
    );
  if (profile.social_category && profile.social_category !== "general")
    chips.push(
      // Short codes (sc, st, obc, ews, dnt) read as acronyms; longer values
      // (minority, safai_mitra) read as words.
      profile.social_category.length <= 3
        ? profile.social_category.toUpperCase()
        : profile.social_category
            .split("_")
            .map((word) => word[0].toUpperCase() + word.slice(1))
            .join(" "),
    );
  if (profile.has_bpl_card) chips.push(t("chips.bplCard"));
  if (profile.is_farmer_with_land) chips.push(t("chips.ownsFarmland"));
  if (profile.cultivates_crops) chips.push(t("chips.cultivatesCrops"));
  if (profile.disability_percent != null)
    chips.push(t("chips.disability", { percent: profile.disability_percent }));
  if (profile.has_bank_account) chips.push(t("chips.hasBankAccount"));
  if (profile.pays_income_tax === false) chips.push(t("chips.noIncomeTax"));
  if (profile.pays_income_tax) chips.push(t("chips.paysIncomeTax"));
  if (profile.family_member_in_govt_service) chips.push(t("chips.govtJobInFamily"));
  if (profile.house_type) chips.push(val(t, "house", profile.house_type));
  if (profile.owns_motorized_vehicle) chips.push(t("chips.ownsVehicle"));
  if (profile.has_lpg_connection === false) chips.push(t("chips.noLpg"));
  if (profile.is_street_vendor) chips.push(t("chips.streetVendor"));
  if (profile.has_vending_certificate_or_lor) chips.push(t("chips.vendingCertificate"));
  if (profile.is_vishwakarma_trade_artisan) chips.push(t("chips.artisan"));
  if (profile.is_post_matric_student) chips.push(t("chips.postMatricStudent"));
  if (profile.is_student) chips.push(t("chips.student"));
  if (profile.daughter_age != null)
    chips.push(t("chips.daughter", { age: profile.daughter_age }));
  if (profile.number_of_children != null)
    chips.push(t("chips.children", { count: profile.number_of_children }));
  if (profile.receives_other_govt_pension) chips.push(t("chips.otherGovtPension"));
  // Distinct facts can collapse to one phrase (occupation "street vendor" +
  // is_street_vendor) — dedupe after translation so keys stay unique too.
  return [...new Set(chips)];
}

/** The structured facts this report is based on. */
export function ProfileChips({ profile }: { profile: UserProfile }) {
  const t = useT();
  const chips = describe(t, profile);
  if (chips.length === 0) return null;
  return (
    <div aria-label={t("chips.ariaLabel")}>
      <span className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        {t("chips.heading")}
      </span>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {chips.map((chip) => (
          <span
            key={chip}
            className="rounded-full border border-border bg-card px-2.5 py-0.5 text-xs text-foreground"
          >
            {chip}
          </span>
        ))}
      </div>
    </div>
  );
}
