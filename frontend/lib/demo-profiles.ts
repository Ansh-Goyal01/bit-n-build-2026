/** One-click demo profiles — ordinary wizard answers, sent through the same
 * `/results?p=` share link a real person gets, so a demo exercises exactly
 * the production path. Nothing is stored. Titles live in the i18n
 * dictionary under `demo.<id>`.
 *
 * Kept free of runtime imports (type-only imports are erased) so
 * `node --test` can load it with native type stripping. */

import type { Answers } from "./wizard";

export interface DemoProfile {
  id: "widow" | "student" | "vendor";
  answers: Answers;
}

export const DEMO_PROFILES: DemoProfile[] = [
  {
    // A widow in rural Uttar Pradesh with a BPL card.
    id: "widow",
    answers: {
      age: 62,
      gender: "female",
      marital_status: "widowed",
      state: "Uttar Pradesh",
      area: "rural",
      occupation: "homemaker",
      annual_family_income_inr: 40000,
      pays_income_tax: "no",
      social_category: "obc",
      has_bpl_card: "yes",
      house_type: "kutcha",
      has_lpg_connection: "no",
      owns_motorized_vehicle: "no",
      has_bank_account: "yes",
      family_member_in_govt_service: "no",
      receives_govt_pension_over_10k: "no",
      receives_other_govt_pension: "no",
    },
  },
  {
    // An OBC post-matric student in Lucknow.
    id: "student",
    answers: {
      age: 19,
      gender: "female",
      marital_status: "single",
      state: "Uttar Pradesh",
      area: "urban",
      occupation: "student",
      is_post_matric_student: "yes",
      annual_family_income_inr: 180000,
      pays_income_tax: "no",
      social_category: "obc",
      has_bpl_card: "no",
      has_bank_account: "yes",
      family_member_in_govt_service: "no",
    },
  },
  {
    // A street vendor in Kanpur with a young daughter.
    id: "vendor",
    answers: {
      age: 34,
      gender: "male",
      marital_status: "married",
      state: "Uttar Pradesh",
      area: "urban",
      occupation: "street_vendor",
      has_vending_certificate_or_lor: "yes",
      annual_family_income_inr: 150000,
      pays_income_tax: "no",
      social_category: "general",
      has_bpl_card: "no",
      has_bank_account: "yes",
      family_member_in_govt_service: "no",
      daughter_age: 5,
      number_of_children: 2,
    },
  },
];
