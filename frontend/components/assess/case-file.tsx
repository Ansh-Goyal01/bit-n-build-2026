"use client";

// Case file UI: opt-in save on this device, JSON export/import between a
// phone and a CSC computer, and "what changed since last time".
import * as React from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Download, FolderOpen, History, Trash2, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { type CaseFile, caseFileName, parseCaseFile } from "@/lib/case";
import { useT } from "@/lib/i18n";
import type { CaseDiff, VerdictChange } from "@/lib/verdict-diff";
import { isEmptyDiff } from "@/lib/verdict-diff";
import { ANSWER_KEYS, encodeAnswers } from "@/lib/wizard";
import { VerdictBadge } from "./verdict-badge";

/** Hand-over key for a case imported on /check: the results page reads it
 * once on load (sessionStorage — this tab only, gone when it closes). */
export const PENDING_IMPORT_KEY = "adhikaar-case-import";

export function readPendingImport(): CaseFile | null {
  try {
    const text = window.sessionStorage.getItem(PENDING_IMPORT_KEY);
    if (!text) return null;
    const parsed = parseCaseFile(text, ANSWER_KEYS);
    return parsed.ok ? parsed.value : null;
  } catch {
    return null;
  }
}

export function clearPendingImport(): void {
  try {
    window.sessionStorage.removeItem(PENDING_IMPORT_KEY);
  } catch {
    // Storage unavailable — nothing was stashed.
  }
}

export function downloadCase(value: CaseFile): void {
  const blob = new Blob([JSON.stringify(value, null, 1)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = caseFileName(new Date());
  link.click();
  URL.revokeObjectURL(url);
}

/** File picker that validates a case file. With `onImported` the caller
 * applies it in place; without, it is handed to /results via sessionStorage. */
export function CaseImportButton({
  onImported,
  variant = "secondary",
}: {
  onImported?: (value: CaseFile) => void;
  variant?: "secondary" | "ghost";
}) {
  const t = useT();
  const toast = useToast();
  const router = useRouter();
  const inputRef = React.useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    const parsed = parseCaseFile(await file.text(), ANSWER_KEYS);
    if (!parsed.ok) {
      toast(t("caseFile.importInvalid"));
      return;
    }
    toast(t("caseFile.imported"));
    if (onImported) {
      onImported(parsed.value);
      return;
    }
    try {
      window.sessionStorage.setItem(PENDING_IMPORT_KEY, JSON.stringify(parsed.value));
    } catch {
      // Without sessionStorage the report still opens from the answers.
    }
    router.push(`/results?p=${encodeAnswers(parsed.value.answers)}`);
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="application/json,.json"
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={(e) => {
          const file = e.target.files?.[0];
          e.target.value = "";
          if (file) void handleFile(file);
        }}
      />
      <Button variant={variant} size="sm" onClick={() => inputRef.current?.click()}>
        <Upload className="size-4" aria-hidden="true" />
        {t("caseFile.import")}
      </Button>
    </>
  );
}

export function CasePanel({
  saved,
  assisted,
  onSaveChange,
  onExport,
  onClear,
  onImported,
}: {
  saved: boolean;
  assisted: boolean;
  onSaveChange: (save: boolean) => void;
  onExport: () => void;
  onClear: () => void;
  onImported: (value: CaseFile) => void;
}) {
  const t = useT();
  return (
    <section
      aria-label={t("caseFile.title")}
      className="print-hidden flex flex-col gap-3 rounded-xl border border-border bg-card p-4"
    >
      <div className="flex items-start gap-2.5">
        <FolderOpen className="mt-0.5 size-5 shrink-0 text-accent" aria-hidden="true" />
        <div>
          <h2 className="font-serif text-lg font-semibold">{t("caseFile.title")}</h2>
          <p className="text-sm leading-relaxed text-muted-foreground">{t("caseFile.lead")}</p>
        </div>
      </div>
      {assisted ? (
        <p className="rounded-lg bg-verdict-info-soft p-3 text-sm leading-relaxed text-verdict-info">
          {t("caseFile.sharedComputer")}
        </p>
      ) : (
        <label className="flex cursor-pointer items-start gap-2.5 text-sm leading-relaxed">
          <input
            type="checkbox"
            checked={saved}
            onChange={(e) => onSaveChange(e.target.checked)}
            className="mt-1 size-4 shrink-0 accent-accent"
          />
          <span>
            <span className="font-medium">{t("caseFile.saveOnDevice")}</span>{" "}
            <span className="text-muted-foreground">{t("caseFile.saveOnDeviceHelp")}</span>
          </span>
        </label>
      )}
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" size="sm" onClick={onExport}>
          <Download className="size-4" aria-hidden="true" />
          {t("caseFile.export")}
        </Button>
        <CaseImportButton onImported={onImported} />
        <Button variant="ghost" size="sm" onClick={onClear}>
          <Trash2 className="size-4" aria-hidden="true" />
          {t("caseFile.clear")}
        </Button>
      </div>
    </section>
  );
}

function ChangeList({ title, changes }: { title: string; changes: VerdictChange[] }) {
  if (changes.length === 0) return null;
  return (
    <div>
      <h3 className="text-sm font-semibold">{title}</h3>
      <ul className="mt-1.5 flex flex-col gap-2">
        {changes.map((change) => (
          <li key={change.scheme_id} className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium">{change.short_name}</span>
            <VerdictBadge verdict={change.before} />
            <ArrowRight className="size-4 text-muted-foreground" aria-hidden="true" />
            <VerdictBadge verdict={change.after} />
          </li>
        ))}
      </ul>
    </div>
  );
}

/** "What changed since 12 Sep": verdict flips and newly unlocked schemes
 * between the saved case's last check and this one. */
export function WhatChanged({ diff, since }: { diff: CaseDiff; since: string }) {
  const t = useT();
  return (
    <section
      aria-label={t("caseFile.changedTitle", { date: since })}
      className="print-hidden flex flex-col gap-3 rounded-xl border border-accent/30 bg-accent/5 p-4"
    >
      <h2 className="flex items-center gap-2 font-serif text-lg font-semibold">
        <History className="size-5 text-accent" aria-hidden="true" />
        {t("caseFile.changedTitle", { date: since })}
      </h2>
      {isEmptyDiff(diff) ? (
        <p className="text-sm text-muted-foreground">{t("caseFile.noChanges")}</p>
      ) : (
        <>
          <ChangeList title={t("caseFile.unlocked")} changes={diff.unlocked} />
          {diff.added.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold">{t("caseFile.added")}</h3>
              <p className="mt-1 text-sm">{diff.added.map((r) => r.short_name).join(" · ")}</p>
            </div>
          )}
          <ChangeList title={t("caseFile.lost")} changes={diff.lost} />
          <ChangeList title={t("caseFile.changed")} changes={diff.changed} />
        </>
      )}
    </section>
  );
}
