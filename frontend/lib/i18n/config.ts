/** Language registry — adding a language is ONE entry here plus ONE locale
 * dictionary in ./locales (see hi.ts for the shape). No code changes.
 *
 * `enabled: false` keeps a language behind a flag until its dictionary passes
 * the coverage check (scripts in P2 report untranslated keys).
 */

export interface LanguageDef {
  /** BCP-47 primary subtag; sent to the API as `lang`. */
  code: string;
  /** Endonym shown in the switcher. */
  label: string;
  /** BCP-47 tag for speech synthesis voice matching. */
  ttsLang: string;
  enabled: boolean;
}

export const LANGUAGES: LanguageDef[] = [
  { code: "en", label: "English", ttsLang: "en-IN", enabled: true },
  { code: "hi", label: "हिन्दी", ttsLang: "hi-IN", enabled: true },
  // Machine-translated locales (scripts/generate_locales.py), pending
  // native-speaker review — see each dictionary's header.
  { code: "bn", label: "বাংলা", ttsLang: "bn-IN", enabled: true },
  { code: "mr", label: "मराठी", ttsLang: "mr-IN", enabled: true },
  { code: "te", label: "తెలుగు", ttsLang: "te-IN", enabled: true },
  { code: "ta", label: "தமிழ்", ttsLang: "ta-IN", enabled: true },
  { code: "gu", label: "ગુજરાતી", ttsLang: "gu-IN", enabled: true },
  { code: "kn", label: "ಕನ್ನಡ", ttsLang: "kn-IN", enabled: true },
  { code: "ml", label: "മലയാളം", ttsLang: "ml-IN", enabled: true },
  { code: "pa", label: "ਪੰਜਾਬੀ", ttsLang: "pa-IN", enabled: true },
  { code: "or", label: "ଓଡ଼ିଆ", ttsLang: "or-IN", enabled: true },
];

export const DEFAULT_LANG = "en";
export const LANG_STORAGE_KEY = "adhikaar-lang";

export const enabledLanguages = () => LANGUAGES.filter((l) => l.enabled);
