/** R5 — life-event entry points: landing pages that pre-fill the wizard.
 *
 * A preset only sets answers the event genuinely implies (a widowed visitor
 * has marital_status "widowed"); everything else stays for the wizard to ask.
 * `schemeIds` power the "covers, among others" chips from the static catalog —
 * scheme short names are proper nouns and render language-invariant.
 */

import type { Answers } from "@/lib/wizard";

export interface LifeEvent {
  /** URL segment and i18n key fragment (marketing.lifeEvents.<key>Title). */
  key: string;
  /** English metadata title (server-rendered <title>; page body is localized). */
  metaTitle: string;
  answers: Answers;
  schemeIds: string[];
}

export const LIFE_EVENTS: LifeEvent[] = [
  {
    key: "widowed",
    metaTitle: "Support after losing your spouse",
    answers: { marital_status: "widowed" },
    schemeIds: ["ignwps", "pmjjby"],
  },
  {
    key: "pregnant",
    metaTitle: "Support during pregnancy",
    answers: { gender: "female", is_pregnant: "yes" },
    schemeIds: ["pmjay"],
  },
  {
    key: "farmer",
    metaTitle: "Schemes for farming families",
    answers: { occupation: "farmer" },
    schemeIds: ["pm-kisan", "pmfby"],
  },
  {
    key: "student",
    metaTitle: "Scholarships and education support",
    answers: { occupation: "student" },
    schemeIds: ["nsp-post-matric-sc"],
  },
  {
    key: "senior",
    metaTitle: "Pensions after 60",
    answers: {},
    schemeIds: ["ignoaps", "apy"],
  },
  {
    key: "disability",
    metaTitle: "Disability entitlements",
    answers: {},
    schemeIds: ["igndps"],
  },
];

export function lifeEventByKey(key: string): LifeEvent | undefined {
  return LIFE_EVENTS.find((event) => event.key === key);
}
