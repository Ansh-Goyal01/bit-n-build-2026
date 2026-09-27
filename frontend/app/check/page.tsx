"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Bookmark, FileText, Pencil, Sparkles } from "lucide-react";

import { Container } from "@/components/site/container";
import { CaseImportButton } from "@/components/assess/case-file";
import { Button, ButtonLink } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { RadioGroup } from "@/components/ui/radio-group";
import { Select } from "@/components/ui/select";
import { ReadAloud } from "@/components/ui/read-aloud";
import { Stepper } from "@/components/ui/stepper";
import { useToast } from "@/components/ui/toast";
import { DEMO_PROFILES } from "@/lib/demo-profiles";
import {
  clearFamilyMembers,
  encodeFamily,
  householdAnswers,
  loadFamilyMembers,
  saveFamilyMembers,
} from "@/lib/family";
import { localizeStep, useT, useWizardOverlay } from "@/lib/i18n";
import { lifeEventByKey } from "@/lib/life-events";
import { useIsClient } from "@/lib/use-is-client";
import {
  type Answers,
  type FieldDef,
  type StepDef,
  STORAGE_KEY,
  decodeAnswers,
  encodeAnswers,
  visibleFields,
  visibleSteps,
} from "@/lib/wizard";

function WhyWeAsk({ children }: { children: React.ReactNode }) {
  const t = useT();
  return (
    <details className="group mt-1">
      <summary className="w-fit cursor-pointer list-none text-sm font-medium text-accent underline-offset-2 hover:underline">
        {t("wizardChrome.whyWeAsk")}
      </summary>
      <p className="mt-1.5 rounded-lg bg-accent-soft p-3 text-sm leading-relaxed text-accent-soft-foreground">
        {children}
      </p>
    </details>
  );
}

function WizardField({
  field,
  value,
  error,
  onChange,
}: {
  field: FieldDef;
  value: Answers[string];
  error?: string;
  onChange: (value: Answers[string]) => void;
}) {
  const t = useT();
  const chooseLabel = t("common.choose");
  if (field.type === "radio" || field.type === "yesno") {
    return (
      <div>
        <RadioGroup
          legend={field.label}
          name={field.key}
          options={field.options ?? []}
          value={typeof value === "string" ? value : null}
          onChange={onChange}
          help={field.help}
          error={error}
          columns={field.type === "yesno"}
        />
        {field.whyWeAsk && <WhyWeAsk>{field.whyWeAsk}</WhyWeAsk>}
      </div>
    );
  }

  if (field.type === "select") {
    return (
      <div>
        <Field
          id={field.key}
          label={field.label}
          help={field.help}
          error={error}
          optional={field.optional}
        >
          <Select
            value={typeof value === "string" ? value : ""}
            onChange={(e) => onChange(e.target.value || null)}
          >
            <option value="">{field.placeholder ?? chooseLabel}</option>
            {(field.options ?? []).map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </Field>
        {field.whyWeAsk && <WhyWeAsk>{field.whyWeAsk}</WhyWeAsk>}
      </div>
    );
  }

  return (
    <div>
      <Field
        id={field.key}
        label={field.label}
        help={field.help}
        error={error}
        optional={field.optional}
      >
        <Input
          type="number"
          inputMode="numeric"
          placeholder={field.placeholder}
          min={field.min}
          max={field.max}
          value={typeof value === "number" ? value : ""}
          onChange={(e) => {
            const raw = e.target.value;
            onChange(raw === "" ? null : Number(raw));
          }}
          className="max-w-52"
        />
      </Field>
      {field.whyWeAsk && <WhyWeAsk>{field.whyWeAsk}</WhyWeAsk>}
    </div>
  );
}

function validateStep(
  step: StepDef,
  answers: Answers,
  t: (key: string, params?: Record<string, string | number>) => string,
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const field of visibleFields(step, answers)) {
    const value = answers[field.key];
    if (field.type === "number") {
      if (typeof value === "number") {
        if (
          (field.min !== undefined && value < field.min) ||
          (field.max !== undefined && value > field.max)
        ) {
          errors[field.key] = t("wizardChrome.numberRange", {
            min: field.min ?? 0,
            max: field.max ?? 0,
          });
        }
      } else if (!field.optional) {
        errors[field.key] = field.errorText ?? t("wizardChrome.fillRequired");
      }
    } else if (!field.optional && (value === null || value === undefined || value === "")) {
      errors[field.key] = field.errorText ?? t("wizardChrome.chooseAnswer");
    }
  }
  return errors;
}

function ReviewStep({
  steps,
  answers,
  onEdit,
}: {
  steps: StepDef[];
  answers: Answers;
  onEdit: (index: number) => void;
}) {
  const t = useT();
  const ANSWER_LABEL: Record<string, string> = {
    yes: t("wizardChrome.yes"),
    no: t("wizardChrome.no"),
    unsure: t("wizardChrome.notSure"),
  };
  return (
    <div className="flex flex-col gap-4">
      {steps.map((step, index) => {
        const fields = visibleFields(step, answers).filter(
          (f) => answers[f.key] !== null && answers[f.key] !== undefined && answers[f.key] !== "",
        );
        if (fields.length === 0) return null;
        return (
          <section
            key={step.id}
            aria-label={step.title}
            className="rounded-xl border border-border bg-card p-5 shadow-card"
          >
            <div className="mb-3 flex items-center justify-between gap-4">
              <h3 className="font-semibold">{step.title}</h3>
              <Button variant="ghost" size="sm" onClick={() => onEdit(index)}>
                <Pencil className="size-3.5" aria-hidden="true" />
                {t("common.edit")}
              </Button>
            </div>
            <dl className="grid gap-x-8 gap-y-2 sm:grid-cols-2">
              {fields.map((field) => {
                const raw = answers[field.key];
                const display =
                  typeof raw === "number"
                    ? field.key === "annual_family_income_inr"
                      ? `₹${raw.toLocaleString("en-IN")}`
                      : String(raw)
                    : (field.options?.find((o) => o.value === raw)?.label ??
                      ANSWER_LABEL[String(raw)] ??
                      String(raw));
                return (
                  <div key={field.key} className="flex flex-col">
                    <dt className="text-xs text-muted-foreground">{field.label}</dt>
                    <dd className="text-sm font-medium">{display}</dd>
                  </div>
                );
              })}
            </dl>
          </section>
        );
      })}
    </div>
  );
}

export default function CheckPage() {
  const router = useRouter();
  const toast = useToast();
  const t = useT();
  const overlay = useWizardOverlay();
  const headingRef = React.useRef<HTMLHeadingElement>(null);

  const isClient = useIsClient();
  // Lazy-initialised from this browser's saved answers; during SSR the
  // initialiser runs without localStorage and yields a fresh start.
  // A ?life= entry point (R5) seeds the answers the event implies on top.
  const [answers, setAnswers] = React.useState<Answers>(() => {
    if (typeof window === "undefined") return {};
    let saved: Answers = {};
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      saved = (stored ? decodeAnswers(stored) : null) ?? {};
    } catch {
      // Private mode or blocked storage — start fresh.
    }
    const params = new URLSearchParams(window.location.search);
    // Family mode (R2): a new member starts from the household's shared
    // answers only — personal questions are asked fresh.
    if (params.get("member") === "new") return householdAnswers(saved);
    const lifeKey = params.get("life");
    const preset = lifeKey ? lifeEventByKey(lifeKey)?.answers : undefined;
    return preset ? { ...saved, ...preset } : saved;
  });
  const [stepIndex, setStepIndex] = React.useState(0);
  const [errors, setErrors] = React.useState<Record<string, string>>({});
  const [resumeOpen, setResumeOpen] = React.useState(false);
  const [resumeCode, setResumeCode] = React.useState("");
  const [resumeError, setResumeError] = React.useState<string | undefined>();

  // Autosave as the person types — losing answers is the one unforgivable bug.
  React.useEffect(() => {
    if (!isClient) return;
    try {
      localStorage.setItem(STORAGE_KEY, encodeAnswers(answers));
    } catch {
      // Storage unavailable; save-and-resume codes still work.
    }
  }, [answers, isClient]);

  // Wizard logic stays canonical (wizard.ts); the active locale only
  // overlays strings, so conditions and answer VALUES are language-invariant.
  const steps = visibleSteps(answers).map((s) => localizeStep(s, overlay));
  const totalSteps = steps.length + 1; // + review
  const isReview = stepIndex >= steps.length;
  const step = isReview ? null : steps[stepIndex];

  const focusHeading = () => {
    // Move focus to the step heading so screen readers announce the change.
    requestAnimationFrame(() => headingRef.current?.focus());
  };

  const goTo = (index: number) => {
    setErrors({});
    setStepIndex(index);
    window.scrollTo({ top: 0 });
    focusHeading();
  };

  const handleContinue = () => {
    if (step) {
      const stepErrors = validateStep(step, answers, t);
      if (Object.keys(stepErrors).length > 0) {
        setErrors(stepErrors);
        return;
      }
    }
    goTo(stepIndex + 1);
  };

  // An organic /check visit (no ?member=new) starts a fresh check — any
  // abandoned family run would otherwise resurface as a surprise family report.
  React.useEffect(() => {
    if (!isClient) return;
    if (new URLSearchParams(window.location.search).get("member") !== "new") {
      clearFamilyMembers();
    }
  }, [isClient]);

  const handleSubmit = () => {
    const members = loadFamilyMembers();
    if (members.length > 0) {
      const all = [...members, answers];
      saveFamilyMembers(all);
      router.push(`/results?f=${encodeFamily(all)}`);
      return;
    }
    router.push(`/results?p=${encodeAnswers(answers)}`);
  };

  const handleSaveCode = async () => {
    const code = encodeAnswers(answers);
    try {
      await navigator.clipboard.writeText(code);
      toast(t("wizardChrome.codeCopied"));
    } catch {
      toast(t("wizardChrome.codeIs", { code }));
    }
  };

  const handleResume = () => {
    const parsed = decodeAnswers(resumeCode.trim());
    if (!parsed) {
      setResumeError(t("wizardChrome.resumeInvalid"));
      return;
    }
    setAnswers(parsed);
    setResumeError(undefined);
    setResumeOpen(false);
    setResumeCode("");
    toast(t("wizardChrome.resumeWelcome"));
  };

  // Until the client takes over, mirror the server-rendered shell exactly —
  // saved answers may differ from the fresh-start HTML.
  if (!isClient) {
    return (
      <Container className="max-w-2xl py-10 sm:py-14">
        <p className="text-muted-foreground" role="status">
          {t("wizardChrome.loading")}
        </p>
      </Container>
    );
  }

  const stepTitle = isReview ? t("wizardChrome.review") : (step?.title ?? "");
  const stepLead = isReview
    ? t("wizardChrome.reviewLead")
    : (step?.lead ?? t("wizardChrome.defaultLead"));
  // Read-aloud covers this step's full question set for low-literacy users.
  const spokenStep = [
    stepTitle,
    stepLead,
    ...(step
      ? visibleFields(step, answers).flatMap((f) => [f.label, f.help ?? ""])
      : []),
  ]
    .filter(Boolean)
    .join(". ");

  return (
    <Container className="max-w-2xl py-10 sm:py-14">
      <div className="flex flex-col gap-8">
        <Stepper
          current={Math.min(stepIndex + 1, totalSteps)}
          total={totalSteps}
          label={stepTitle}
        />

        <div className="flex flex-col gap-2">
          <div className="flex items-start justify-between gap-2">
            <h1
              ref={headingRef}
              tabIndex={-1}
              className="font-serif text-2xl font-semibold tracking-tight outline-none sm:text-3xl"
            >
              {stepTitle}
            </h1>
            <ReadAloud text={spokenStep} />
          </div>
          <p className="leading-relaxed text-muted-foreground">{stepLead}</p>
        </div>

        {isReview ? (
          <ReviewStep steps={steps} answers={answers} onEdit={goTo} />
        ) : (
          <div className="flex flex-col gap-7">
            {step &&
              visibleFields(step, answers).map((field) => (
                <WizardField
                  key={field.key}
                  field={field}
                  value={answers[field.key] ?? null}
                  error={errors[field.key]}
                  onChange={(value) => {
                    setAnswers((prev) => ({ ...prev, [field.key]: value }));
                    setErrors((prev) => {
                      if (!prev[field.key]) return prev;
                      const next = { ...prev };
                      delete next[field.key];
                      return next;
                    });
                  }}
                />
              ))}
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-6">
          <div>
            {stepIndex > 0 && (
              <Button variant="secondary" onClick={() => goTo(stepIndex - 1)}>
                <ArrowLeft className="size-4" aria-hidden="true" />
                {t("common.back")}
              </Button>
            )}
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Button variant="ghost" onClick={handleSaveCode}>
              <Bookmark className="size-4" aria-hidden="true" />
              {t("wizardChrome.saveResume")}
            </Button>
            {isReview ? (
              <Button onClick={handleSubmit}>
                <FileText className="size-4" aria-hidden="true" />
                {t("wizardChrome.getReport")}
              </Button>
            ) : (
              <Button onClick={handleContinue}>
                {t("common.continue")}
                <ArrowRight className="size-4" aria-hidden="true" />
              </Button>
            )}
          </div>
        </div>

        <div className="text-sm text-muted-foreground">
          {resumeOpen ? (
            <div className="flex flex-col gap-2">
              <Field
                id="resume-code"
                label={t("wizardChrome.resumeCode")}
                error={resumeError}
                help={t("wizardChrome.resumeHelp")}
              >
                <Input
                  value={resumeCode}
                  onChange={(e) => setResumeCode(e.target.value)}
                  placeholder={t("wizardChrome.resumePlaceholder")}
                />
              </Field>
              <div className="flex gap-2">
                <Button size="sm" variant="secondary" onClick={handleResume}>
                  {t("wizardChrome.restore")}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setResumeOpen(false)}>
                  {t("wizardChrome.neverMind")}
                </Button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setResumeOpen(true)}
              className="text-accent underline-offset-2 hover:underline"
            >
              {t("wizardChrome.haveCode")}
            </button>
          )}
        </div>

        {stepIndex === 0 && (
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span>{t("caseFile.haveFile")}</span>
            <CaseImportButton variant="ghost" />
          </div>
        )}

        {stepIndex === 0 && (
          <div className="flex flex-col gap-2 rounded-xl border border-dashed border-border p-4">
            <p className="flex items-center gap-1.5 text-sm font-medium">
              <Sparkles className="size-4 text-accent" aria-hidden="true" />
              {t("demo.heading")}
            </p>
            <p className="text-sm text-muted-foreground">{t("demo.lead")}</p>
            <div className="flex flex-wrap gap-2">
              {DEMO_PROFILES.map((demo) => (
                <ButtonLink
                  key={demo.id}
                  size="sm"
                  variant="secondary"
                  href={`/results?p=${encodeAnswers(demo.answers)}`}
                >
                  {t(`demo.${demo.id}`)}
                </ButtonLink>
              ))}
            </div>
          </div>
        )}
      </div>
    </Container>
  );
}
