"use client";

/** Client-side i18n: a context provider + hooks. Language choice lives ONLY
 * in localStorage (no PII, no server state). The first paint is English and
 * the stored language applies on hydration — a deliberate trade against
 * hydration mismatches. The engine never sees the language; it reaches the
 * API only as the `lang` field, translating prose at the edge. */

import * as React from "react";

import { DEFAULT_LANG, LANG_STORAGE_KEY, enabledLanguages, LANGUAGES } from "./config";
import { bn, bnWizard } from "./locales/bn";
import { en, type UiDict } from "./locales/en";
import { gu, guWizard } from "./locales/gu";
import { hi, hiWizard } from "./locales/hi";
import { kn, knWizard } from "./locales/kn";
import { ml, mlWizard } from "./locales/ml";
import { mr, mrWizard } from "./locales/mr";
import { or, orWizard } from "./locales/or";
import { pa, paWizard } from "./locales/pa";
import { ta, taWizard } from "./locales/ta";
import { te, teWizard } from "./locales/te";
import type { WizardOverlay } from "./overlay";

const UI_DICTS: Record<string, UiDict> = { en, hi, bn, mr, te, ta, gu, kn, ml, pa, or };
const WIZARD_OVERLAYS: Record<string, WizardOverlay | null> = {
  en: null,
  hi: hiWizard,
  bn: bnWizard,
  mr: mrWizard,
  te: teWizard,
  ta: taWizard,
  gu: guWizard,
  kn: knWizard,
  ml: mlWizard,
  pa: paWizard,
  or: orWizard,
};

interface LanguageContextValue {
  lang: string;
  setLang: (code: string) => void;
  ttsLang: string;
}

const LanguageContext = React.createContext<LanguageContextValue>({
  lang: DEFAULT_LANG,
  setLang: () => {},
  ttsLang: "en-IN",
});

// localStorage is an external store — useSyncExternalStore gives a
// hydration-safe read (server snapshot: default language) without
// setState-in-effect churn.
const langListeners = new Set<() => void>();

function readStoredLang(): string {
  try {
    const stored = localStorage.getItem(LANG_STORAGE_KEY);
    if (stored && enabledLanguages().some((l) => l.code === stored)) return stored;
  } catch {
    // storage unavailable — stay on the default
  }
  return DEFAULT_LANG;
}

function writeStoredLang(code: string): void {
  try {
    localStorage.setItem(LANG_STORAGE_KEY, code);
  } catch {
    // fine — the choice just won't persist
  }
  langListeners.forEach((notify) => notify());
}

function subscribeLang(notify: () => void): () => void {
  langListeners.add(notify);
  return () => langListeners.delete(notify);
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const lang = React.useSyncExternalStore(subscribeLang, readStoredLang, () => DEFAULT_LANG);

  React.useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = React.useCallback((code: string) => {
    writeStoredLang(code);
  }, []);

  const ttsLang = LANGUAGES.find((l) => l.code === lang)?.ttsLang ?? "en-IN";

  return (
    <LanguageContext.Provider value={{ lang, setLang, ttsLang }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextValue {
  return React.useContext(LanguageContext);
}

type Params = Record<string, string | number>;

function lookup(dict: UiDict, path: string): string | undefined {
  let node: unknown = dict;
  for (const part of path.split(".")) {
    if (typeof node !== "object" || node === null) return undefined;
    node = (node as Record<string, unknown>)[part];
  }
  return typeof node === "string" ? node : undefined;
}

function interpolate(template: string, params?: Params): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (m, key: string) =>
    key in params ? String(params[key]) : m,
  );
}

/** t("results.print") — active locale with English fallback. */
export function useT() {
  const { lang } = useLanguage();
  return React.useCallback(
    (path: string, params?: Params): string => {
      const dict = UI_DICTS[lang] ?? en;
      const value = lookup(dict, path) ?? lookup(en, path) ?? path;
      return interpolate(value, params);
    },
    [lang],
  );
}

/** The active locale's wizard string overlay (null = English canonical). */
export function useWizardOverlay(): WizardOverlay | null {
  const { lang } = useLanguage();
  return WIZARD_OVERLAYS[lang] ?? null;
}

export { localizeField, localizeStep } from "./overlay";
