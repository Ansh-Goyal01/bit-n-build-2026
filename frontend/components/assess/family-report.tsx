"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Link2, Printer, RefreshCw, UserPlus } from "lucide-react";

import { DocGuides } from "@/components/assess/doc-guides";
import { DocumentChecklist } from "@/components/assess/document-checklist";
import { PrintSchemeList } from "@/components/assess/print-scheme-list";
import { ProfileChips } from "@/components/assess/profile-chips";
import { ResultCard } from "@/components/assess/result-card";
import { ResultsSkeleton } from "@/components/assess/skeletons";
import { ValueHeadline } from "@/components/assess/value-headline";
import { Button, ButtonLink } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { WhatsAppIcon } from "@/components/ui/whatsapp-icon";
import { ApiError, assess } from "@/lib/api";
import { encodeFamily, saveFamilyMembers } from "@/lib/family";
import { useLanguage, useT } from "@/lib/i18n";
import type { SchemeResult, UserProfile } from "@/lib/types";
import { type Answers, answersToProfile } from "@/lib/wizard";

/** R2 — the combined household report. Every member is assessed separately
 * against the same rules engine (verdicts stay per-person and cited); this
 * view only groups the outcomes. Household facts were shared at answer time
 * (lib/family.ts), so "one wizard run per member" costs only the personal
 * questions. */

type MemberReport =
  | { kind: "ok"; profile: UserProfile; results: SchemeResult[] }
  | { kind: "need-info"; profile: UserProfile; question: string }
  | { kind: "error"; message: string };

async function assessMember(
  answers: Answers,
  lang: string,
  fallbacks: { needInfo: string; error: string },
): Promise<MemberReport> {
  try {
    const response = await assess("", answersToProfile(answers), lang);
    if (response.status === "need_info") {
      return {
        kind: "need-info",
        profile: response.profile,
        question: response.question ?? fallbacks.needInfo,
      };
    }
    return { kind: "ok", profile: response.profile, results: response.results };
  } catch (error) {
    return {
      kind: "error",
      message: error instanceof ApiError ? error.message : fallbacks.error,
    };
  }
}

const isEntitled = (r: SchemeResult) =>
  r.verdict === "eligible" || r.verdict === "likely_eligible";

function MemberSection({ index, report }: { index: number; report: MemberReport }) {
  const t = useT();
  const heading = t("family.memberLabel", { n: index + 1 });

  return (
    <section aria-label={heading} className="flex flex-col gap-4 border-t border-border pt-8">
      <h2 className="font-serif text-2xl font-semibold tracking-tight">{heading}</h2>

      {report.kind === "error" && (
        <p className="leading-relaxed text-muted-foreground">{report.message}</p>
      )}

      {report.kind === "need-info" && (
        <>
          <ProfileChips profile={report.profile} />
          <p className="leading-relaxed text-muted-foreground">
            {t("family.needInfo")} {report.question}
          </p>
        </>
      )}

      {report.kind === "ok" && (
        <MemberVerdicts profile={report.profile} results={report.results} />
      )}
    </section>
  );
}

function MemberVerdicts({
  profile,
  results,
}: {
  profile: UserProfile;
  results: SchemeResult[];
}) {
  const t = useT();
  const entitled = [
    ...results.filter((r) => r.verdict === "eligible"),
    ...results.filter((r) => r.verdict === "likely_eligible"),
  ];
  const moreInfo = results.filter((r) => r.verdict === "need_more_info");
  const notMatched = results.length - entitled.length - moreInfo.length;

  return (
    <div className="flex flex-col gap-4">
      <ProfileChips profile={profile} />
      {entitled.length === 0 && moreInfo.length === 0 && (
        <p className="leading-relaxed text-muted-foreground">{t("family.noneForMember")}</p>
      )}
      <PrintSchemeList results={entitled} />
      <div className="print-hidden flex flex-col gap-4">
        {entitled.map((result) => (
          <ResultCard key={result.scheme_id} result={result} />
        ))}
      </div>
      {entitled.length > 0 && <ValueHeadline results={entitled} />}
      {moreInfo.length > 0 && (
        <>
          <h3 className="font-semibold">{t("results.moreInfoSection")}</h3>
          <PrintSchemeList results={moreInfo} />
          <div className="print-hidden flex flex-col gap-4">
            {moreInfo.map((result) => (
              <ResultCard key={result.scheme_id} result={result} />
            ))}
          </div>
        </>
      )}
      {notMatched > 0 && (
        <p className="text-sm leading-relaxed text-muted-foreground">
          {t("family.notMatchedCount", { count: notMatched })}
        </p>
      )}
    </div>
  );
}

export function FamilyReport({ members }: { members: Answers[] }) {
  const router = useRouter();
  const toast = useToast();
  const t = useT();
  const { lang } = useLanguage();
  const [reports, setReports] = React.useState<MemberReport[] | null>(null);

  const fallbacks = React.useMemo(
    () => ({ needInfo: t("results.needInfoFallback"), error: t("results.errorFallback") }),
    [t],
  );

  // Language changes re-run for freshly translated prose; verdicts are
  // language-invariant by construction.
  React.useEffect(() => {
    let cancelled = false;
    void Promise.all(members.map((m) => assessMember(m, lang, fallbacks))).then((next) => {
      if (!cancelled) setReports(next);
    });
    return () => {
      cancelled = true;
    };
  }, [members, lang, fallbacks]);

  if (reports === null) {
    return (
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <h1 className="font-serif text-2xl font-semibold tracking-tight sm:text-3xl">
            {t("results.preparing")}
          </h1>
        </div>
        <ResultsSkeleton />
      </div>
    );
  }

  const entitledTotal = reports.reduce(
    (sum, r) => (r.kind === "ok" ? sum + r.results.filter(isEntitled).length : sum),
    0,
  );
  // Combined checklist/guides across the household, one scheme once.
  const allEntitled = [
    ...new Map(
      reports
        .flatMap((r) => (r.kind === "ok" ? r.results.filter(isEntitled) : []))
        .map((r) => [r.scheme_id, r] as const),
    ).values(),
  ];

  const shareUrl = `${window.location.origin}/results?f=${encodeFamily(members)}`;

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      toast(t("results.linkCopied"));
    } catch {
      toast(t("results.linkCopyFailed"));
    }
  };

  const handleWhatsAppShare = () => {
    const text = `${t("results.whatsappMessage")}\n${shareUrl}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank", "noopener,noreferrer");
  };

  const handleAddMember = () => {
    saveFamilyMembers(members);
    router.push("/check?member=new");
  };

  const reportDate = new Date().toLocaleDateString(lang === "en" ? "en-IN" : `${lang}-IN`, {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-4">
        <p className="text-sm font-medium tracking-wide text-muted-foreground uppercase">
          {t("family.reportLabel")} · {reportDate}
        </p>
        <h1 className="font-serif text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
          {entitledTotal > 0
            ? t("family.entitledTitle", { count: entitledTotal })
            : t("family.noEntitlementTitle")}
        </h1>
        <p className="max-w-2xl leading-relaxed text-muted-foreground">{t("family.lead")}</p>

        <div className="print-hidden flex flex-wrap gap-2 pt-1">
          <Button variant="secondary" onClick={handleAddMember}>
            <UserPlus className="size-4" aria-hidden="true" />
            {t("family.addMember")}
          </Button>
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
          <ButtonLink variant="ghost" href="/check">
            <RefreshCw className="size-4" aria-hidden="true" />
            {t("results.changeAnswers")}
          </ButtonLink>
        </div>
      </header>

      {reports.map((report, index) => (
        <MemberSection key={index} index={index} report={report} />
      ))}

      {allEntitled.length > 0 && <DocumentChecklist results={allEntitled} />}
      {allEntitled.length > 0 && <DocGuides results={allEntitled} />}

      <footer className="rounded-xl border border-border bg-card p-5 text-sm leading-relaxed text-muted-foreground">
        {t("footer.disclaimer")}
      </footer>
    </div>
  );
}
