/** Wizard step definitions + profile encoding for save/resume and share links.
 *
 * Answers are a flat record keyed by UserProfile field name. Three-valued
 * booleans ("yes" | "no" | "unsure") mirror the rules engine's met/failed/
 * unknown logic — "not sure" is always an honest, allowed answer.
 */

import type { UserProfile } from "./types";

export type AnswerValue = string | number | null;
export type Answers = Record<string, AnswerValue>;

export const STORAGE_KEY = "adhikaar-wizard-v1";

export const INDIAN_STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
  "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
  "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
  "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
  "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
  "Andaman and Nicobar Islands", "Chandigarh",
  "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir",
  "Ladakh", "Lakshadweep", "Puducherry",
] as const;

export interface FieldDef {
  key: string;
  type: "number" | "select" | "radio" | "yesno";
  label: string;
  help?: string;
  whyWeAsk?: string;
  optional?: boolean;
  options?: { value: string; label: string; description?: string }[];
  placeholder?: string;
  min?: number;
  max?: number;
  /** Kind message when a required field is empty or a number is out of range. */
  errorText?: string;
  /** Show this field only when the predicate holds. */
  condition?: (answers: Answers) => boolean;
}

export interface StepDef {
  id: string;
  title: string;
  lead?: string;
  fields: FieldDef[];
  condition?: (answers: Answers) => boolean;
}

const YES_NO_UNSURE = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
  { value: "unsure", label: "Not sure" },
];

const isFarmer = (a: Answers) => a.occupation === "farmer";
const isVendor = (a: Answers) => a.occupation === "street_vendor";
const isArtisan = (a: Answers) => a.occupation === "artisan";
const isStudent = (a: Answers) => a.occupation === "student";
const livesInUP = (a: Answers) => a.state === "Uttar Pradesh";

export const STEPS: StepDef[] = [
  {
    id: "about",
    title: "About you",
    lead: "Most schemes depend on age and life situation — this is the foundation of your report.",
    fields: [
      {
        key: "age",
        type: "number",
        label: "Your age",
        help: "In years. Most schemes have an age window, so this matters a lot.",
        min: 1,
        max: 120,
        errorText: "Please enter your age — most schemes depend on it.",
        placeholder: "e.g. 45",
      },
      {
        key: "gender",
        type: "radio",
        label: "Gender",
        options: [
          { value: "female", label: "Female" },
          { value: "male", label: "Male" },
          { value: "other", label: "Another gender" },
          { value: "unsure", label: "Prefer not to say" },
        ],
        whyWeAsk:
          "Some schemes are only for women — like the widow pension and the daughters' savings scheme. We never store this.",
      },
      {
        key: "marital_status",
        type: "radio",
        label: "Marital status",
        options: [
          { value: "single", label: "Single" },
          { value: "married", label: "Married" },
          { value: "widowed", label: "Widowed" },
          { value: "divorced_separated", label: "Divorced or separated" },
          { value: "unsure", label: "Prefer not to say" },
        ],
        whyWeAsk:
          "The Indira Gandhi Widow Pension depends on marital status. We only use this to check that one rule.",
      },
    ],
  },
  {
    id: "place",
    title: "Where you live",
    lead: "A few schemes work differently in villages and cities.",
    fields: [
      {
        key: "state",
        type: "select",
        label: "State or union territory",
        help: "Central schemes apply across India. If you live in Uttar Pradesh, we also check its state schemes.",
        optional: true,
        options: INDIAN_STATES.map((s) => ({ value: s, label: s })),
        placeholder: "Choose your state",
      },
      {
        key: "area",
        type: "radio",
        label: "Do you live in a village or a city?",
        options: [
          { value: "rural", label: "Village (rural)" },
          { value: "urban", label: "City or town (urban)" },
        ],
        help: "Housing support, for example, is currently for rural areas.",
      },
    ],
  },
  {
    id: "work",
    title: "Your work and income",
    lead: "This helps us check farmer, vendor, artisan, and income-linked schemes.",
    fields: [
      {
        key: "occupation",
        type: "select",
        label: "What best describes your main work?",
        placeholder: "Choose one",
        options: [
          { value: "farmer", label: "Farmer" },
          { value: "street_vendor", label: "Street vendor or hawker" },
          { value: "artisan", label: "Traditional artisan or craftsperson" },
          { value: "daily_wage", label: "Daily-wage or manual labourer" },
          { value: "salaried", label: "Salaried job (private)" },
          { value: "govt_service", label: "Government service" },
          { value: "self_employed", label: "Self-employed or small business" },
          { value: "homemaker", label: "Homemaker" },
          { value: "student", label: "Student" },
          { value: "retired", label: "Retired" },
          { value: "unemployed", label: "Not working at the moment" },
          { value: "other", label: "Something else" },
        ],
      },
      {
        key: "annual_family_income_inr",
        type: "number",
        label: "Your family's yearly income (₹)",
        help: "Everyone in the household together, before tax. A rough estimate is fine.",
        whyWeAsk:
          "Several schemes have an income ceiling — for example ₹2.5 lakh a year for the SC scholarship. Your answer is only compared against those limits and never stored.",
        optional: true,
        min: 0,
        max: 100000000,
        placeholder: "e.g. 120000",
      },
      {
        key: "pays_income_tax",
        type: "yesno",
        label: "Did anyone in your family pay income tax last year?",
        options: YES_NO_UNSURE,
        help: "Some schemes exclude income-tax payers. “Not sure” is a fine answer.",
      },
    ],
  },
  {
    id: "work-details",
    title: "A little more about your work",
    condition: (a) => isFarmer(a) || isVendor(a) || isArtisan(a) || isStudent(a),
    fields: [
      {
        key: "is_farmer_with_land",
        type: "yesno",
        label: "Does your family own cultivable land in its own name?",
        options: YES_NO_UNSURE,
        condition: isFarmer,
        help: "PM-KISAN support goes to landholding farmer families.",
      },
      {
        key: "cultivates_crops",
        type: "yesno",
        label: "Do you grow crops on that land?",
        options: YES_NO_UNSURE,
        condition: isFarmer,
        help: "Crop insurance applies to farmers actually growing notified crops.",
      },
      {
        key: "has_land_ownership_or_tenure_docs",
        type: "yesno",
        label: "Do you have land papers — ownership or tenancy documents?",
        options: YES_NO_UNSURE,
        condition: isFarmer,
      },
      {
        key: "holds_constitutional_or_political_post",
        type: "yesno",
        label:
          "Has anyone in your family held a constitutional post or elected office — minister, MP, MLA, mayor, or district panchayat chairperson?",
        options: YES_NO_UNSURE,
        condition: isFarmer,
        help: "PM-KISAN excludes families of such office-holders.",
      },
      {
        key: "is_practicing_registered_professional",
        type: "yesno",
        label:
          "Is anyone in your family a practicing registered professional — doctor, engineer, lawyer, chartered accountant, or architect?",
        options: YES_NO_UNSURE,
        condition: isFarmer,
        help: "PM-KISAN excludes families of practicing registered professionals.",
      },
      {
        key: "has_vending_certificate_or_lor",
        type: "yesno",
        label: "Do you have a vending certificate or a letter of recommendation from your town body?",
        options: YES_NO_UNSURE,
        condition: isVendor,
        help: "PM SVANidhi loans ask for one of these. If not, your town's vending committee can issue it.",
      },
      {
        key: "is_vishwakarma_trade_artisan",
        type: "yesno",
        label: "Is your craft one of the 18 traditional trades — like carpenter, blacksmith, tailor, potter, cobbler, or goldsmith?",
        options: YES_NO_UNSURE,
        condition: isArtisan,
        help: "PM Vishwakarma supports these listed family trades.",
      },
      {
        key: "is_post_matric_student",
        type: "yesno",
        label: "Are you studying after Class 10 (post-matric)?",
        options: YES_NO_UNSURE,
        condition: isStudent,
        help: "The SC scholarship covers courses after Class 10.",
      },
    ],
  },
  {
    id: "household",
    title: "Your household",
    lead: "These answers decide the housing, health, and cooking-gas schemes.",
    fields: [
      {
        key: "social_category",
        type: "radio",
        label: "Social category",
        options: [
          { value: "general", label: "General" },
          { value: "obc", label: "OBC" },
          { value: "sc", label: "SC" },
          { value: "st", label: "ST" },
          { value: "ews", label: "EWS (Economically Weaker Section)" },
          { value: "dnt", label: "DNT (Denotified or Nomadic Tribe)" },
          {
            value: "safai_mitra",
            label: "Safai Mitra (sanitation worker or waste picker)",
          },
          {
            value: "minority",
            label: "Minority (Muslim, Christian, Sikh, Buddhist, Jain, Parsi)",
          },
          { value: "unsure", label: "Prefer not to say" },
        ],
        whyWeAsk:
          "The Post-Matric Scholarship is specifically for SC students, so we can only check it with this answer. It is never stored or shared.",
      },
      {
        key: "has_bpl_card",
        type: "yesno",
        label: "Is your family on the BPL list, or do you hold a BPL / priority ration card?",
        options: YES_NO_UNSURE,
        whyWeAsk:
          "Pension and cooking-gas schemes use the BPL list. Since we can't check the list itself, a “yes” makes those verdicts “likely eligible”, to be confirmed at the office.",
      },
      {
        key: "house_type",
        type: "radio",
        label: "What kind of house do you live in?",
        options: [
          { value: "kutcha", label: "Kutcha", description: "Mud, thatch, or other temporary materials" },
          { value: "pucca", label: "Pucca", description: "Brick, cement, or concrete" },
          { value: "unsure", label: "Not sure" },
        ],
        help: "Rural housing support goes to families in kutcha houses.",
      },
      {
        key: "has_lpg_connection",
        type: "yesno",
        label: "Does your household already have an LPG gas connection?",
        options: YES_NO_UNSURE,
      },
      {
        key: "owns_motorized_vehicle",
        type: "yesno",
        label: "Does anyone in the family own a motorised vehicle — a car, tractor, or two-wheeler?",
        options: YES_NO_UNSURE,
        help: "A few schemes use this to identify better-off households.",
      },
    ],
  },
  {
    id: "family",
    title: "You and your family",
    lead: "Last set — pensions, insurance, savings, and health cover.",
    fields: [
      {
        key: "has_bank_account",
        type: "yesno",
        label: "Do you have a bank account?",
        options: YES_NO_UNSURE,
        help: "Insurance and pension schemes pay through a bank account.",
      },
      {
        key: "family_member_in_govt_service",
        type: "yesno",
        label: "Is anyone in your family a serving or retired government employee?",
        options: YES_NO_UNSURE,
        help: "Some schemes exclude government-employee families.",
      },
      {
        key: "receives_govt_pension_over_10k",
        type: "yesno",
        label: "Does anyone in the family receive a government pension of ₹10,000 or more a month?",
        options: YES_NO_UNSURE,
      },
      {
        key: "receives_other_govt_pension",
        type: "yesno",
        label: "Do you already receive a pension under another state or central government scheme — old-age, widow, disability or similar?",
        options: YES_NO_UNSURE,
        condition: livesInUP,
        help: "Uttar Pradesh's widow and divyang pensions are not paid alongside another government pension.",
      },
      {
        key: "daughter_age",
        type: "number",
        label: "If you have a daughter under 10, how old is she?",
        help: "The Sukanya Samriddhi savings account can be opened until she turns 10. Skip this if it doesn't apply.",
        optional: true,
        min: 0,
        max: 25,
        placeholder: "Age in years",
      },
      {
        key: "number_of_children",
        type: "number",
        label: "How many children are in your family?",
        condition: livesInUP,
        optional: true,
        min: 0,
        max: 20,
        placeholder: "e.g. 2",
        help: "Uttar Pradesh's Kanya Sumangala Yojana is for families with at most two children. Skip this if it doesn't apply.",
      },
      {
        key: "is_pregnant",
        type: "yesno",
        label: "Are you currently pregnant?",
        options: YES_NO_UNSURE,
        condition: (a) => a.gender === "female",
        help: "Maternity benefit schemes need this to check eligibility.",
      },
      {
        key: "single_girl_child",
        type: "yesno",
        label: "Are you the only girl child in your family (no brother)?",
        options: YES_NO_UNSURE,
        condition: (a) => a.gender === "female",
        whyWeAsk:
          "A few scholarships are reserved for a family's single girl child. We only use this to check those, and nothing is stored.",
      },
      {
        key: "disability_percent",
        type: "number",
        label: "If you live with a disability, what percentage is on your certificate?",
        whyWeAsk:
          "The Indira Gandhi Disability Pension needs 80% or more. We ask for the number only to check that rule, and it is never stored.",
        optional: true,
        min: 0,
        max: 100,
        placeholder: "e.g. 80",
      },
      {
        key: "disability_type",
        type: "select",
        label: "Which category is on the disability certificate?",
        condition: (a) => Number(a.disability_percent) > 0,
        optional: true,
        whyWeAsk:
          "Some disability schemes apply only to specific categories named in the National Trust Act. Leave this blank if you're not sure.",
        options: [
          { value: "", label: "Prefer not to say / not sure" },
          { value: "autism", label: "Autism" },
          { value: "cerebral_palsy", label: "Cerebral palsy" },
          { value: "intellectual_disability", label: "Intellectual disability" },
          { value: "multiple_disabilities", label: "Multiple disabilities" },
          { value: "other", label: "Another disability" },
        ],
      },
      {
        key: "bereavement_event",
        type: "yesno",
        label: "Has the main earner of your family passed away?",
        options: YES_NO_UNSURE,
        whyWeAsk:
          "The National Family Benefit Scheme gives a one-time payment to a poor family whose primary breadwinner has died. We ask only to check that scheme.",
      },
      {
        key: "is_pmjay_priority_category",
        type: "yesno",
        label: "Is your family in a deprived or priority group — for example landless labourers, or listed in the SECC survey?",
        options: YES_NO_UNSURE,
        help: "Ayushman Bharat health cover uses these categories. “Not sure” is fine — many families are listed without knowing.",
      },
    ],
  },
];

/** Every answer key the wizard can produce — the allow-list for imported
 * case files. */
export const ANSWER_KEYS: ReadonlySet<string> = new Set(
  STEPS.flatMap((step) => step.fields.map((field) => field.key)),
);

/** Steps that apply for the current answers (conditions evaluated live). */
export function visibleSteps(answers: Answers): StepDef[] {
  return STEPS.filter((step) => !step.condition || step.condition(answers));
}

export function visibleFields(step: StepDef, answers: Answers): FieldDef[] {
  return step.fields.filter((f) => !f.condition || f.condition(answers));
}

const toBool = (v: AnswerValue): boolean | null =>
  v === "yes" ? true : v === "no" ? false : null;

/** Map wizard answers onto the API's UserProfile shape. */
export function answersToProfile(answers: Answers): UserProfile {
  const num = (key: string): number | null => {
    const v = answers[key];
    return typeof v === "number" && Number.isFinite(v) ? v : null;
  };
  const str = (key: string): string | null => {
    const v = answers[key];
    return typeof v === "string" && v && v !== "unsure" ? v : null;
  };

  const occupation = str("occupation");
  const maritalMap: Record<string, string> = {
    single: "single",
    married: "married",
    widowed: "widowed",
    divorced_separated: "divorced",
  };

  return {
    age: num("age"),
    gender: str("gender"),
    marital_status: answers.marital_status
      ? (maritalMap[String(answers.marital_status)] ?? null)
      : null,
    state: str("state"),
    area: str("area"),
    occupation: occupation ? occupation.replace(/_/g, " ") : null,
    is_farmer_with_land: toBool(answers.is_farmer_with_land),
    annual_family_income_inr: num("annual_family_income_inr"),
    social_category: str("social_category"),
    has_bpl_card: toBool(answers.has_bpl_card),
    disability_percent: num("disability_percent"),
    has_bank_account: toBool(answers.has_bank_account),
    pays_income_tax: toBool(answers.pays_income_tax),
    is_student: occupation === "student" ? true : null,
    daughter_age: num("daughter_age"),
    family_member_in_govt_service: toBool(answers.family_member_in_govt_service),
    receives_govt_pension_over_10k: toBool(answers.receives_govt_pension_over_10k),
    holds_constitutional_or_political_post: toBool(
      answers.holds_constitutional_or_political_post,
    ),
    is_practicing_registered_professional: toBool(
      answers.is_practicing_registered_professional,
    ),
    cultivates_crops: toBool(answers.cultivates_crops),
    has_land_ownership_or_tenure_docs: toBool(answers.has_land_ownership_or_tenure_docs),
    house_type:
      answers.house_type === "kutcha" || answers.house_type === "pucca"
        ? (answers.house_type as "kutcha" | "pucca")
        : null,
    owns_motorized_vehicle: toBool(answers.owns_motorized_vehicle),
    is_pmjay_priority_category: toBool(answers.is_pmjay_priority_category),
    has_lpg_connection: toBool(answers.has_lpg_connection),
    is_street_vendor: occupation === "street_vendor" ? true : null,
    has_vending_certificate_or_lor: toBool(answers.has_vending_certificate_or_lor),
    is_vishwakarma_trade_artisan: toBool(answers.is_vishwakarma_trade_artisan),
    is_post_matric_student: toBool(answers.is_post_matric_student),
    is_pregnant: toBool(answers.is_pregnant),
    single_girl_child: toBool(answers.single_girl_child),
    // Free-form category string; the backend normalizes/validates it, mapping
    // any unrecognized value to null ("not stated").
    disability_type: answers.disability_type
      ? (String(answers.disability_type) as UserProfile["disability_type"])
      : null,
    bereavement_event: toBool(answers.bereavement_event),
    receives_other_govt_pension: toBool(answers.receives_other_govt_pension),
    number_of_children: num("number_of_children"),
  };
}

/** URL-safe answer encoding for save/resume codes and shareable report links. */
export function encodeAnswers(answers: Answers): string {
  const compact = Object.fromEntries(
    Object.entries(answers).filter(([, v]) => v !== null && v !== ""),
  );
  const json = JSON.stringify(compact);
  const bytes = new TextEncoder().encode(json);
  let binary = "";
  bytes.forEach((b) => (binary += String.fromCharCode(b)));
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function decodeAnswers(code: string): Answers | null {
  try {
    const b64 = code.replace(/-/g, "+").replace(/_/g, "/");
    const binary = atob(b64);
    const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
    const parsed: unknown = JSON.parse(new TextDecoder().decode(bytes));
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) return null;
    const entries = Object.entries(parsed as Record<string, unknown>).filter(
      ([, v]) => typeof v === "string" || typeof v === "number",
    );
    return Object.fromEntries(entries) as Answers;
  } catch {
    return null;
  }
}
