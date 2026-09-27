"use client";

import * as React from "react";
import { Mic, MicOff } from "lucide-react";

import { useLanguage, useT } from "@/lib/i18n";
import { useIsClient } from "@/lib/use-is-client";

/** Speak-your-answer for low-literacy users, via the browser's built-in
 * speech recognition (free, no API key; Chrome/Edge/Android). Mirrors the
 * ReadAloud contract: the mic renders ONLY where recognition exists —
 * elsewhere the plain text box is the whole experience, never a dead button.
 * Server-side ASR (e.g. Bhashini) can replace this by swapping the
 * recognition internals; the component contract stays the same. */

// The Web Speech recognition API is absent from TS's DOM lib (still
// vendor-prefixed in practice) — type only the surface we touch.
interface RecognitionResultEvent {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
}
interface SpeechRecognitionLike {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: RecognitionResultEvent) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

function recognitionCtor(): (new () => SpeechRecognitionLike) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as Record<string, unknown>;
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null) as
    | (new () => SpeechRecognitionLike)
    | null;
}

export function VoiceInput({
  onResult,
  className,
}: {
  /** Receives the final transcript once the person stops speaking. */
  onResult: (transcript: string) => void;
  className?: string;
}) {
  const { ttsLang } = useLanguage();
  const t = useT();
  const isClient = useIsClient();
  const [listening, setListening] = React.useState(false);
  const recognitionRef = React.useRef<SpeechRecognitionLike | null>(null);

  React.useEffect(() => {
    return () => recognitionRef.current?.abort();
  }, []);

  // First paint matches the server (no mic); support is a pure client read.
  if (!isClient || recognitionCtor() === null) return null;

  const toggle = () => {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const Ctor = recognitionCtor();
    if (!Ctor) return;
    const recognition = new Ctor();
    recognition.lang = ttsLang;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
      const transcript = Array.from({ length: event.results.length }, (_, i) =>
        event.results[i][0].transcript.trim(),
      )
        .filter(Boolean)
        .join(" ");
      if (transcript) onResult(transcript);
    };
    // Covers natural end, stop(), permission denial, and no-speech alike.
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  };

  const label = listening ? t("voice.stop") : t("voice.speak");
  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={listening}
      aria-label={label}
      title={label}
      className={`print-hidden inline-flex size-9 shrink-0 items-center justify-center rounded-lg transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
        listening
          ? "bg-accent-soft text-accent"
          : "text-muted-foreground hover:bg-muted hover:text-foreground"
      } ${className ?? ""}`}
    >
      {listening ? (
        <MicOff className="size-4" aria-hidden="true" />
      ) : (
        <Mic className="size-4" aria-hidden="true" />
      )}
    </button>
  );
}
