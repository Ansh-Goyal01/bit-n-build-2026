"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowRight,
  CheckCircle2,
  HelpCircle,
  Link2,
  MinusCircle,
  Printer,
  RefreshCw,
  UserCheck,
  UserPlus,
} from "lucide-react";

import { ApplicationPacket } from "@/components/assess/application-packet";
import {
  OperatorBadge,
  OperatorChecks,
  OperatorHandoff,
} from "@/components/assess/assisted-mode";
import {
  CasePanel,
  WhatChanged,
  clearPendingImport,
  downloadCase,
  readPendingImport,
} from "@/components/assess/case-file";
import { DocumentPriority } from "@/components/assess/document-priority";
import { PacketSheet } from "@/components/assess/packet-sheet";
import { ResultsSkeleton } from "@/components/assess/skeletons";
import { DocGuides } from "@/components/assess/doc-guides";
import { PrintSchemeList } from "@/components/assess/print-scheme-list";
import { DocumentChecklist } from "@/components/assess/document-checklist";
import { FamilyReport } from "@/components/assess/family-report";
import { ValueHeadline } from "@/components/assess/value-headline";
import { FeedbackForm } from "@/components/assess/feedback-form";
import { ProfileChips } from "@/components/assess/profile-chips";
import { ResultCard } from "@/components/assess/result-card";
import { WhatIf } from "@/components/assess/what-if";
import { Container } from "@/components/site/container";
import { Button, ButtonLink } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { ReadAloud } from "@/components/ui/read-aloud";
import { VoiceInput } from "@/components/ui/voice-input";
import { WhatsAppIcon } from "@/components/ui/whatsapp-icon";
import { type Annotations, type OperatorAnnotation, withAnnotation } from "@/lib/assisted";
import {
  type CaseFile,
  buildCase,
  clearSavedCase,
  loadSavedCase,
  saveCase,
  snapshotOf,
} from "@/lib/case";
import { decodeFamily, saveFamilyMembers } from "@/lib/family";
import { ApiError, assess } from "@/lib/api";
import { useLanguage, useT } from "@/lib/i18n";
import { SCHEME_COUNT } from "@/lib/site";
import type { AssessResponse, SchemeResult, UserProfile } from "@/lib/types";
import type { DocumentsHave } from "@/lib/packet";
import { useIsClient } from "@/lib/use-is-client";
import { type VerdictLike, diffSinceLastCheck } from "@/lib/verdict-diff";
import {
  ANSWER_KEYS,
  type Answers,
  STORAGE_KEY,
  answersToProfile,
  decodeAnswers,
  encodeAnswers,
} from "@/lib/wizard";

type Phase =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "need-info"; question: string; profile: UserProfile }
  | { kind: "ok"; response: AssessResponse };

async function computeAssessment(
  message: string,
  profile: UserProfile,
  lang: string,
  fallbacks: { needInfo: string; error: string },
): Promise<Phase> {
  try {
    const response = await assess(message, profile, lang);
    if (response.status === "need_info") {
      return {
        kind: "need-info",
        question: response.question ?? fallbacks.needInfo,
        profile: response.profile,
      };
    }
    return { kind: "ok", response };
  } catch (error) {
    return {
      kind: "error",
      message: error instanceof ApiError ? error.message : fallbacks.error,
    };
  }
}

/** Answers from the share link, falling back to this browser's saved wizard. */
function loadAnswers(code: string | null): Answers | null {
  let answers = code ? decodeAnswers(code) : null;
  if (!answers) {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) answers = decodeAnswers(saved);
    } catch {
      // storage unavailable — fall through to the empty state
    }
  }
  return answers && Object.keys(answers).length > 0 ? answers : null;
}

function groupResults(results: SchemeResult[]) {
  const entitled = results.filter(
    (r) => r.verdict === "eligible" || r.verdict === "likely_eligible",
  );
  return {
    entitled: [
      ...entitled.filter((r) => r.verdict === "eligible"),
      ...entitled.filter((r) => r.verdict === "likely_eligible"),
    ],
    moreInfo: results.filter((r) => r.verdict === "need_more_info"),
    notEligible: results.filter((r) => r.verdict === "not_eligible"),
  };
}

function SectionHeading({
  icon: Icon,
  tone,
  title,
  lead,
  count,
}: {
  icon: typeof CheckCircle2;
  tone: "yes" | "info" | "no";
  title: string;
  lead: string;
  count: number;
}) {
  const toneClass = {
    yes: "bg-verdict-yes-soft text-verdict-yes",
    info: "bg-verdict-info-soft text-verdict-info",
    no: "bg-verdict-no-soft text-verdict-no",
  }[tone];
  return (
    <div className="flex items-start gap-3">
      <span className={`mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg ${toneClass}`}>
        <Icon className="size-4.5" aria-hidden="true" />
      </span>
      <div>
        <h2 className="font-serif text-xl font-semibold tracking-tight sm:text-2xl">
          {title} <span className="text-muted-foreground">({count})</span>
        </h2>
        {/* Guidance prose earns its place on screen; on paper only facts do. */}
        <p className="print-hidden mt-0.5 text-sm leading-relaxed text-muted-foreground">{lead}</p>
      </div>
    </div>
  );
}

function ResultsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  const isClient = useIsClient();
  const t = useT();
  const { lang } = useLanguage();
  const [phase, setPhase] = React.useState<Phase>({ kind: "loading" });
  const [followUp, setFollowUp] = React.useState("");
  const [followUpBusy, setFollowUpBusy] = React.useState(false);
  // Case file: a case imported on /check (handed over via sessionStorage) or
  // the opt-in saved case restores ticks and annotations, and its last
  // verdicts become the baseline for "what changed since last time". Read
  // once, client-side; nothing renders from it before the report loads.
  const [initialCase] = React.useState<CaseFile | null>(() => {
    if (typeof window === "undefined") return null;
    return readPendingImport() ?? loadSavedCase(window.localStorage, ANSWER_KEYS);
  });
  const [savedOnDevice, setSavedOnDevice] = React.useState(
    () => typeof window !== "undefined" && loadSavedCase(window.localStorage, ANSWER_KEYS) !== null,
  );
  const [baseline, setBaseline] = React.useState<{ snapshot: VerdictLike[]; since: string } | null>(
    initialCase ? { snapshot: initialCase.snapshot, since: initialCase.updated_at } : null,
  );
  const createdRef = React.useRef<CaseFile | null>(initialCase);
  React.useEffect(() => clearPendingImport(), []);
  // Application-packet document ticks: one shared state for the tracker,
  // the priority list, and every packet (known document types are shared).
  const [have, setHave] = React.useState<DocumentsHave>(initialCase?.documents_have ?? {});
  const toggleHave = React.useCallback(
    (key: string) => setHave((prev) => ({ ...prev, [key]: !prev[key] })),
    [],
  );
  // Assisted mode: operator "document seen" annotations. They sit beside the
  // verdicts and never feed back into the engine.
  const [assisted, setAssisted] = React.useState(initialCase?.assisted ?? false);
  const [annotations, setAnnotations] = React.useState<Annotations>(
    initialCase?.annotations ?? {},
  );
  const annotate = React.useCallback(
    (key: string, change: Partial<OperatorAnnotation>) =>
      setAnnotations((prev) => withAnnotation(prev, key, change)),
    [],
  );
  // "Print packet": <html data-print="packet"> swaps the printed page from the
  // whole report to one scheme's packet sheet, then resets after printing.
  const [printTarget, setPrintTarget] = React.useState<string | null>(null);
  React.useEffect(() => {
    if (!printTarget) return;
    const root = document.documentElement;
    root.dataset.print = "packet";
    const reset = () => {
      delete root.dataset.print;
      setPrintTarget(null);
    };
    window.addEventListener("afterprint", reset, { once: true });
    const frame = window.requestAnimationFrame(() => window.print());
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("afterprint", reset);
      delete root.dataset.print;
    };
  }, [printTarget]);

  const code = searchParams.get("p");
  const answers = React.useMemo(
    () => (isClient ? loadAnswers(code) : undefined),
    [code, isClient],
  );

  // R2 — a ?f= link is a whole-household report and takes over the page.
  const familyCode = searchParams.get("f");
  const familyMembers = React.useMemo(
    () => (familyCode ? decodeFamily(familyCode) : null),
    [familyCode],
  );

  const fallbacks = React.useMemo(
    () => ({ needInfo: t("results.needInfoFallback"), error: t("results.errorFallback") }),
    [t],
  );

  // Event-handler re-runs (retry, follow-up answers) may show the loader eagerly.
  const runAssessment = async (message: string, profile: UserProfile) => {
    setPhase({ kind: "loading" });
    setPhase(await computeAssessment(message, profile, lang, fallbacks));
  };

  // Re-runs when the language changes too: same verdicts (language-invariant
  // by construction), freshly translated prose.
  React.useEffect(() => {
    if (familyMembers || !answers) return;
    let cancelled = false;
    void computeAssessment("", answersToProfile(answers), lang, fallbacks).then((next) => {
      if (!cancelled) setPhase(next);
    });
    return () => {
      cancelled = true;
    };
  }, [answers, lang, fallbacks, familyMembers]);

  // Derive the code from loaded answers when the URL doesn't carry one, so
  // a shared link always reproduces this report for its recipient.
  const shareUrl = () => {
    const shareCode = code ?? (answers ? encodeAnswers(answers) : null);
    return shareCode ? `${window.location.origin}/results?p=${shareCode}` : null;
  };

  // Opt-in autosave on this device — never in assisted mode, where the
  // computer is shared and the case leaves by export instead.
  const reportResults = phase.kind === "ok" ? phase.response.results : null;
  React.useEffect(() => {
    if (!savedOnDevice || assisted || !reportResults || !answers) return;
    const value = buildCase(
      createdRef.current,
      {
        lang,
        answers,
        snapshot: snapshotOf(reportResults),
        documents_have: have,
        annotations,
        assisted,
      },
      new Date(),
    );
    createdRef.current = value;
    saveCase(window.localStorage, value);
  }, [savedOnDevice, assisted, reportResults, answers, lang, have, annotations]);

  const handleSaveChange = (save: boolean) => {
    setSavedOnDevice(save);
    if (!save) clearSavedCase(window.localStorage);
    toast(t(save ? "caseFile.savedToast" : "caseFile.unsavedToast"));
  };

  const handleExport = () => {
    if (!reportResults || !answers) return;
    downloadCase(
      buildCase(
        createdRef.current,
        {
          lang,
          answers,
          snapshot: snapshotOf(reportResults),
          documents_have: have,
          annotations,
          assisted,
        },
        new Date(),
      ),
    );
  };

  const handleClear = () => {
    clearSavedCase(window.localStorage);
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Storage unavailable — nothing stored to clear.
    }
    setSavedOnDevice(false);
    setHave({});
    setAnnotations({});
    setBaseline(null);
    createdRef.current = null;
    toast(t("caseFile.clearedToast"));
  };

  const handleImported = (value: CaseFile) => {
    createdRef.current = value;
    setHave(value.documents_have);
    setAnnotations(value.annotations);
    setAssisted(value.assisted);
    setBaseline({ snapshot: value.snapshot, since: value.updated_at });
    router.push(`/results?p=${encodeAnswers(value.answers)}`);
  };

  const handleCopyLink = async () => {
    const url = shareUrl();
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      toast(t("results.linkCopied"));
    } catch {
      toast(t("results.linkCopyFailed"));
    }
  };

  const handleWhatsAppShare = () => {
    const url = shareUrl();
    if (!url) return;
    // wa.me works logged-out and app-less (falls back to WhatsApp Web),
    // and carries the report as a link — the report itself stays unstored.
    const text = `${t("results.whatsappMessage")}\n${url}`;
    window.open(
      `https://wa.me/?text=${encodeURIComponent(text)}`,
      "_blank",
      "noopener,noreferrer",
    );
  };

  if (isClient && familyMembers) {
    return <FamilyReport members={familyMembers} />;
  }

  if (isClient && answers === null) {
    return (
      <EmptyState
        title={t("results.emptyTitle")}
        body={t("results.emptyBody")}
        action={
          <ButtonLink href="/check">
            {t("results.emptyAction")}
            <ArrowRight className="size-4" aria-hidden="true" />
          </ButtonLink>
        }
      />
    );
  }

  if (phase.kind === "loading") {
    return (
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <h1 className="font-serif text-2xl font-semibold tracking-tight sm:text-3xl">
            {t("results.preparing")}
          </h1>
          <p className="leading-relaxed text-muted-foreground" role="status">
            {t("results.preparingBody", { count: SCHEME_COUNT })}
          </p>
        </div>
        <ResultsSkeleton />
      </div>
    );
  }

  if (phase.kind === "error") {
    return (
      <ErrorState
        title={t("results.errorTitle")}
        body={phase.message}
        action={
          <div className="flex flex-wrap justify-center gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                if (answers) void runAssessment("", answersToProfile(answers));
              }}
            >
              <RefreshCw className="size-4" aria-hidden="true" />
              {t("common.tryAgain")}
            </Button>
            <ButtonLink variant="ghost" href="/check">
              {t("results.useGuidedQuestions")}
              <ArrowRight className="size-4" aria-hidden="true" />
            </ButtonLink>
          </div>
        }
      />
    );
  }

  if (phase.kind === "need-info") {
    return (
      <div className="mx-auto flex max-w-xl flex-col gap-6">
        <div className="flex flex-col gap-2">
          <h1 className="font-serif text-2xl font-semibold tracking-tight sm:text-3xl">
            {t("results.needInfoTitle")}
          </h1>
          <p className="leading-relaxed text-muted-foreground">{phase.question}</p>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!followUp.trim() || followUpBusy) return;
            setFollowUpBusy(true);
            void runAssessment(followUp.trim(), phase.profile).finally(() =>
              setFollowUpBusy(false),
            );
          }}
          className="flex flex-col gap-4"
        >
          <Field
            id="follow-up"
            label={t("results.yourAnswer")}
            help={t("results.plainWords")}
          >
            <div className="flex items-center gap-2">
              <Input
                value={followUp}
                onChange={(e) => setFollowUp(e.target.value)}
                placeholder={t("results.typeAnswer")}
              />
              <VoiceInput
                onResult={(transcript) =>
                  setFollowUp((prev) => (prev.trim() ? `${prev.trim()} ${transcript}` : transcript))
                }
              />
            </div>
          </Field>
          <Button type="submit" disabled={!followUp.trim() || followUpBusy} className="w-fit">
            {t("results.continueToReport")}
            <ArrowRight className="size-4" aria-hidden="true" />
          </Button>
        </form>
      </div>
    );
  }

  const { response } = phase;
  const groups = groupResults(response.results);
  // Presentation-only date formatting; the date itself is canonical.
  const reportDate = new Date().toLocaleDateString(lang === "en" ? "en-IN" : `${lang}-IN`, {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const headline =
    groups.entitled.length > 0
      ? groups.entitled.length === 1
        ? t("results.entitledTitleOne")
        : t("results.entitledTitleMany", { count: groups.entitled.length })
      : t("results.noEntitlementTitle");
  const headlineLead =
    groups.entitled.length > 0
      ? t("results.entitledLead")
      : groups.moreInfo.length > 0
        ? t("results.moreInfoLead")
        : t("results.noneLead", { count: SCHEME_COUNT });

  return (
    <>
      <div className="report-root flex flex-col gap-10 print:gap-4">
        {/* Report header */}
        <header className="flex flex-col gap-4 print:gap-2">
          <p className="text-sm font-medium tracking-wide text-muted-foreground uppercase">
            {t("results.reportLabel")} · {reportDate}
          </p>
          <div className="flex items-start justify-between gap-2">
            <h1 className="font-serif text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
              {headline}
            </h1>
            <ReadAloud text={`${headline}. ${headlineLead}`} />
          </div>
          <p className="max-w-2xl leading-relaxed text-muted-foreground">{headlineLead}</p>

          <ProfileChips profile={response.profile} />

          <div className="print-hidden flex flex-wrap gap-2 pt-1">
            <Button variant="secondary" onClick={() => window.print()}>
              <Printer className="size-4" aria-hidden="true" />
              {t("results.print")}
            </Button>
            <Button variant="secondary" onClick={handleCopyLink}>
              <Link2 className="size-4" aria-hidden="true" />
              {t("results.copyLink")}
            </Button>
            <Button variant="secondary" onClick={handleWhatsAppShare}>
              <WhatsAppIcon className="size-4" />
              {t("results.shareWhatsApp")}
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                // R2 — this report's answers become household member 1; the
                // wizard reopens with only the shared household facts kept.
                if (!answers) return;
                saveFamilyMembers([answers]);
                router.push("/check?member=new");
              }}
            >
              <UserPlus className="size-4" aria-hidden="true" />
              {t("family.addMember")}
            </Button>
            <Button
              variant={assisted ? "default" : "secondary"}
              aria-pressed={assisted}
              onClick={() => setAssisted((on) => !on)}
            >
              <UserCheck className="size-4" aria-hidden="true" />
              {t(assisted ? "assisted.on" : "assisted.toggle")}
            </Button>
            <ButtonLink variant="ghost" href="/check">
              <RefreshCw className="size-4" aria-hidden="true" />
              {t("results.changeAnswers")}
            </ButtonLink>
          </div>
          <p className="print-hidden text-sm leading-relaxed text-muted-foreground">
            {t("family.addMemberHelp")}
          </p>
          {assisted && (
            <p className="print-hidden rounded-lg bg-accent-soft p-3 text-sm leading-relaxed text-accent-soft-foreground">
              {t("assisted.lead")}
            </p>
          )}
        </header>

        {response.explanations_simplified && (
          <p
            role="status"
            className="print-hidden rounded-lg bg-verdict-info-soft p-3 text-sm leading-relaxed text-verdict-info"
          >
            {t("results.explanationsSimplified")}
          </p>
        )}

        {baseline && (
          <WhatChanged
            diff={diffSinceLastCheck(baseline.snapshot, response.results)}
            since={new Date(baseline.since).toLocaleDateString(
              lang === "en" ? "en-IN" : `${lang}-IN`,
              { day: "numeric", month: "long", year: "numeric" },
            )}
          />
        )}

        {groups.entitled.length > 0 && (
          <section aria-label={t("results.entitledSection")} className="flex flex-col gap-5">
            <SectionHeading
              icon={CheckCircle2}
              tone="yes"
              title={t("results.entitledSection")}
              lead={t("results.entitledSectionLead")}
              count={groups.entitled.length}
            />
            <PrintSchemeList results={groups.entitled} />
            <div className="print-hidden flex flex-col gap-4">
              {groups.entitled.map((result) => (
                <ResultCard
                  key={result.scheme_id}
                  result={result}
                  badges={<OperatorBadge result={result} annotations={annotations} />}
                  packet={
                    <ApplicationPacket
                      result={result}
                      profile={response.profile}
                      have={have}
                      onToggle={toggleHave}
                      onPrint={() => setPrintTarget(result.scheme_id)}
                      extra={
                        assisted && (
                          <OperatorChecks
                            result={result}
                            annotations={annotations}
                            onAnnotate={annotate}
                          />
                        )
                      }
                    />
                  }
                />
              ))}
            </div>
          </section>
        )}

        {groups.entitled.length > 0 && <ValueHeadline results={groups.entitled} />}

        {groups.entitled.length > 0 && (
          <DocumentPriority results={groups.entitled} have={have} onToggle={toggleHave} />
        )}

        {groups.entitled.length > 0 && (
          <DocumentChecklist results={groups.entitled} have={have} onToggle={toggleHave} />
        )}

        {groups.entitled.length > 0 && <DocGuides results={groups.entitled} />}

        {groups.moreInfo.length > 0 && (
          <section aria-label={t("results.moreInfoSection")} className="flex flex-col gap-5">
            <SectionHeading
              icon={HelpCircle}
              tone="info"
              title={t("results.moreInfoSection")}
              lead={t("results.moreInfoSectionLead")}
              count={groups.moreInfo.length}
            />
            <PrintSchemeList results={groups.moreInfo} />
            <div className="print-hidden flex flex-col gap-4">
              {groups.moreInfo.map((result) => (
                <ResultCard key={result.scheme_id} result={result} />
              ))}
            </div>
          </section>
        )}

        {groups.notEligible.length > 0 && (
          <section aria-label={t("results.notEligibleSection")} className="flex flex-col gap-5">
            <SectionHeading
              icon={MinusCircle}
              tone="no"
              title={t("results.notEligibleSection")}
              lead={t("results.notEligibleSectionLead")}
              count={groups.notEligible.length}
            />
            {/* On paper a name list carries everything these cards say — the
                full cards would multiply the printed report several times over. */}
            <p className="hidden print-block text-sm leading-relaxed text-muted-foreground">
              {groups.notEligible.map((r) => r.short_name).join(" · ")}
            </p>
            <div className="print-hidden flex flex-col gap-4">
              {groups.notEligible.map((result) => (
                <ResultCard key={result.scheme_id} result={result} />
              ))}
            </div>
          </section>
        )}

        <CasePanel
          saved={savedOnDevice}
          assisted={assisted}
          onSaveChange={handleSaveChange}
          onExport={handleExport}
          onClear={handleClear}
          onImported={handleImported}
        />

        <WhatIf profile={response.profile} baseline={response.results} lang={lang} />

        <FeedbackForm results={response.results} lang={lang} />

        <footer className="rounded-xl border border-border bg-card p-5 text-sm leading-relaxed text-muted-foreground">
          {t("footer.disclaimer")}
        </footer>
      </div>
      {groups.entitled.map((result) => (
        <PacketSheet
          key={result.scheme_id}
          result={result}
          profile={response.profile}
          have={have}
          active={printTarget === result.scheme_id}
          handoff={
            assisted && <OperatorHandoff result={result} annotations={annotations} have={have} />
          }
        />
      ))}
    </>
  );
}

export default function ResultsPage() {
  return (
    <Container className="max-w-3xl py-10 sm:py-14">
      <React.Suspense
        fallback={
          <div className="flex flex-col gap-6">
            <ResultsSkeleton />
          </div>
        }
      >
        <ResultsContent />
      </React.Suspense>
    </Container>
  );
}
