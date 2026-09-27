"use client";

import * as React from "react";
import { Square, Volume2 } from "lucide-react";

import { useLanguage, useT } from "@/lib/i18n";

/** Per-section read-aloud for low-literacy users, via the browser's built-in
 * speech synthesis (free, offline, no API key). The button renders ONLY when
 * a voice for the active language actually exists — reading Hindi text with
 * an English voice would be worse than silence (graceful fallback: no audio,
 * never a blocked UI). Server-side TTS (e.g. Bhashini) can replace this by
 * swapping the speak() internals; the component contract stays the same. */
export function ReadAloud({ text, className }: { text: string; className?: string }) {
  const { ttsLang } = useLanguage();
  const t = useT();
  const [speaking, setSpeaking] = React.useState(false);
  const [voice, setVoice] = React.useState<SpeechSynthesisVoice | null>(null);

  React.useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    const pick = () => {
      const primary = ttsLang.split("-")[0];
      const voices = window.speechSynthesis.getVoices();
      const match =
        voices.find((v) => v.lang === ttsLang) ??
        voices.find((v) => v.lang.startsWith(`${primary}-`) || v.lang === primary) ??
        null;
      setVoice(match);
    };
    pick();
    window.speechSynthesis.addEventListener("voiceschanged", pick);
    return () => window.speechSynthesis.removeEventListener("voiceschanged", pick);
  }, [ttsLang]);

  // Stop speech when the section unmounts or language changes.
  React.useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, [ttsLang]);

  if (!voice) return null;

  const toggle = () => {
    const synth = window.speechSynthesis;
    if (speaking) {
      synth.cancel();
      setSpeaking(false);
      return;
    }
    synth.cancel(); // one section at a time
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = voice;
    utterance.lang = voice.lang;
    utterance.rate = 0.95;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    synth.speak(utterance);
    setSpeaking(true);
  };

  const label = speaking ? t("readAloud.stop") : t("readAloud.listen");
  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={speaking}
      aria-label={label}
      title={label}
      className={`print-hidden inline-flex size-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${className ?? ""}`}
    >
      {speaking ? (
        <Square className="size-4" aria-hidden="true" />
      ) : (
        <Volume2 className="size-4" aria-hidden="true" />
      )}
    </button>
  );
}
