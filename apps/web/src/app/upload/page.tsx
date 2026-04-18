"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  Check,
  CheckCircle2,
  FileSpreadsheet,
  FolderUp,
  Info,
  Loader2,
  X,
} from "lucide-react";
import { useState } from "react";

import { BackOfficeShell } from "@/components/back-office-shell";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { uk } from "@/i18n/uk";
import { formatInt } from "@/i18n/format";
import { runMatcher, uploadDataset } from "@/lib/api/endpoints";
import type { MatcherRunResponse, UploadResponse } from "@/lib/api/types";

type StepState = "active" | "done" | "pending";

interface StepIndicatorProps {
  steps: { label: string; state: StepState }[];
}

function StepIndicator({ steps }: StepIndicatorProps) {
  return (
    <ol className="flex items-center gap-2 text-sm">
      {steps.map((step, i) => {
        const number = i + 1;
        const isLast = i === steps.length - 1;
        return (
          <li key={step.label} className="flex items-center gap-2">
            <span
              className={cn(
                "flex h-7 w-7 items-center justify-center rounded-full border text-xs font-semibold tabular",
                step.state === "done" && "border-forest bg-forest text-surface",
                step.state === "active" &&
                  "border-forest bg-forest/10 text-forest-700",
                step.state === "pending" && "border-ink/15 bg-surface text-ink-muted",
              )}
            >
              {step.state === "done" ? <Check className="h-3.5 w-3.5" /> : number}
            </span>
            <span
              className={cn(
                "font-medium",
                step.state === "active" ? "text-ink" : "text-ink-muted",
              )}
            >
              {step.label}
            </span>
            {!isLast && (
              <span
                aria-hidden
                className={cn(
                  "mx-2 h-px w-8",
                  step.state === "done" ? "bg-forest" : "bg-ink/15",
                )}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}

interface DropzoneProps {
  id: string;
  label: string;
  hint: string;
  file: File | null;
  onChange: (file: File | null) => void;
}

function Dropzone({ id, label, hint, file, onChange }: DropzoneProps) {
  return (
    <label
      htmlFor={id}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors",
        file
          ? "border-forest/50 bg-forest/[0.04]"
          : "border-ink/15 bg-surface-muted/40 hover:border-forest/40 hover:bg-surface-muted",
      )}
    >
      <span
        className={cn(
          "flex h-12 w-12 items-center justify-center rounded-2xl",
          file ? "bg-forest text-surface" : "bg-surface-muted text-ink-muted",
        )}
      >
        {file ? <CheckCircle2 className="h-6 w-6" /> : <FolderUp className="h-6 w-6" />}
      </span>
      <div className="flex flex-col gap-1">
        <span className="text-sm font-semibold text-ink">{label}</span>
        <span className="text-xs text-ink-muted">{hint}</span>
      </div>
      <Input
        id={id}
        type="file"
        accept=".xlsx"
        className="hidden"
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
      />
    </label>
  );
}

interface FileRow {
  role: "zem" | "ner";
  label: string;
  file: File | null;
  onRemove: () => void;
}

function FileList({ rows }: { rows: FileRow[] }) {
  return (
    <div className="flex flex-col gap-2 rounded-2xl border border-ink/[0.06] bg-surface-muted/40 p-3">
      <span className="px-2 pt-1 text-[11px] font-medium uppercase tracking-wider text-ink-muted">
        {uk.upload.selectedTitle}
      </span>
      <ul className="flex flex-col divide-y divide-ink/[0.06]">
        {rows.map((row) => (
          <li
            key={row.role}
            className="flex items-center justify-between gap-3 px-2 py-2.5"
          >
            <div className="flex min-w-0 items-center gap-3">
              <span
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-lg",
                  row.file
                    ? "bg-forest/10 text-forest-700"
                    : "bg-ink/[0.06] text-ink-muted",
                )}
              >
                <FileSpreadsheet className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-ink">
                  {row.file?.name ?? row.label}
                </p>
                <p className="text-xs text-ink-muted">
                  {row.file
                    ? `${row.label} · ${uk.upload.statusReady}`
                    : `${row.label} · ${uk.upload.statusMissing}`}
                </p>
              </div>
            </div>
            {row.file ? (
              <button
                type="button"
                onClick={row.onRemove}
                className="flex h-7 w-7 items-center justify-center rounded-lg text-ink-muted hover:bg-surface hover:text-ink"
                aria-label={uk.upload.remove}
              >
                <X className="h-4 w-4" />
              </button>
            ) : (
              <span className="text-xs text-ink-muted">—</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function UploadPage() {
  const [zemFile, setZemFile] = useState<File | null>(null);
  const [nerFile, setNerFile] = useState<File | null>(null);
  const [label, setLabel] = useState("");
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [matchResult, setMatchResult] = useState<MatcherRunResponse | null>(null);
  const qc = useQueryClient();

  const uploadMut = useMutation({
    mutationFn: (body: { zem: File; ner: File; label: string }) => uploadDataset(body),
    onSuccess: (data) => {
      setResult(data);
      qc.invalidateQueries({ queryKey: ["datasets"] });
    },
  });

  const matcherMut = useMutation({
    mutationFn: (datasetId: string) => runMatcher(datasetId),
    onSuccess: (data) => {
      setMatchResult(data);
      qc.invalidateQueries({ queryKey: ["datasets"] });
      qc.invalidateQueries({ queryKey: ["findings"] });
    },
  });

  const canSubmit = !!zemFile && !!nerFile && label.trim().length > 0 && !uploadMut.isPending;
  const filesSelected = [zemFile, nerFile].filter(Boolean).length;

  // Step 1 = upload; 2 = analyze; 3 = review
  const uploadStepDone = !!result;
  const analyzeStepDone = !!matchResult;
  const steps: { label: string; state: StepState }[] = [
    {
      label: uk.upload.steps.upload,
      state: uploadStepDone ? "done" : "active",
    },
    {
      label: uk.upload.steps.analyze,
      state: analyzeStepDone ? "done" : uploadStepDone ? "active" : "pending",
    },
    {
      label: uk.upload.steps.review,
      state: analyzeStepDone ? "active" : "pending",
    },
  ];

  return (
    <BackOfficeShell>
      <div className="mx-auto flex max-w-3xl flex-col gap-8">
        <div className="flex flex-col gap-3">
          <span className="text-[11px] font-medium uppercase tracking-wider text-ink-muted">
            {uk.eyebrow.upload}
          </span>
          <h1 className="text-display text-ink">{uk.upload.title}</h1>
          <p className="text-small">{uk.upload.subtitle}</p>
          <div className="mt-2">
            <StepIndicator steps={steps} />
          </div>
        </div>

        {!result ? (
          <Card>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!zemFile || !nerFile) return;
                uploadMut.mutate({ zem: zemFile, ner: nerFile, label: label.trim() });
              }}
            >
              <CardHeader>
                <CardTitle>{uk.upload.emptyHeading}</CardTitle>
                <CardDescription>{uk.upload.emptyBody}</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-6">
                <div className="flex flex-col gap-2">
                  <Label htmlFor="label">{uk.upload.labelLabel}</Label>
                  <Input
                    id="label"
                    value={label}
                    placeholder={uk.upload.placeholderLabel}
                    onChange={(e) => setLabel(e.target.value)}
                    required
                  />
                  <p className="text-meta text-ink-muted">{uk.upload.labelHint}</p>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <Dropzone
                    id="zem"
                    label={uk.upload.zemLabel}
                    hint={uk.upload.zemHint}
                    file={zemFile}
                    onChange={setZemFile}
                  />
                  <Dropzone
                    id="ner"
                    label={uk.upload.nerLabel}
                    hint={uk.upload.nerHint}
                    file={nerFile}
                    onChange={setNerFile}
                  />
                </div>

                {filesSelected > 0 ? (
                  <FileList
                    rows={[
                      {
                        role: "zem",
                        label: uk.upload.zemLabel,
                        file: zemFile,
                        onRemove: () => setZemFile(null),
                      },
                      {
                        role: "ner",
                        label: uk.upload.nerLabel,
                        file: nerFile,
                        onRemove: () => setNerFile(null),
                      },
                    ]}
                  />
                ) : (
                  <div className="flex items-start gap-3 rounded-2xl border border-warning/25 bg-warning/10 px-4 py-3 text-sm text-[#8C6B1F]">
                    <Info className="mt-0.5 h-4 w-4 flex-shrink-0" />
                    <p>{uk.upload.requirement}</p>
                  </div>
                )}

                {uploadMut.error ? (
                  <p className="text-sm text-rose-700">
                    {(uploadMut.error as Error).message}
                  </p>
                ) : null}
              </CardContent>
              <CardFooter className="flex items-center justify-between border-t border-ink/[0.06]">
                <span className="text-small text-ink-muted">
                  {`${uk.upload.filesSelected}: ${filesSelected}/2`}
                </span>
                <Button type="submit" disabled={!canSubmit} size="lg">
                  {uploadMut.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      {uk.upload.submitting}
                    </>
                  ) : (
                    <>
                      {uk.upload.ctaStart}
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </Button>
              </CardFooter>
            </form>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-forest-700" />
                {uk.upload.resultTitle}
              </CardTitle>
              <CardDescription>{result.label}</CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-3 gap-4 text-small">
              <div className="rounded-2xl bg-surface-muted p-4">
                <div className="text-meta">{uk.upload.fields.zem}</div>
                <div className="text-h2 tabular text-ink">
                  {formatInt(result.zem_rows)}
                </div>
              </div>
              <div className="rounded-2xl bg-surface-muted p-4">
                <div className="text-meta">{uk.upload.fields.ner}</div>
                <div className="text-h2 tabular text-ink">
                  {formatInt(result.ner_rows)}
                </div>
              </div>
              <div className="rounded-2xl bg-surface-muted p-4">
                <div className="text-meta">{uk.upload.fields.persons}</div>
                <div className="text-h2 tabular text-ink">
                  {formatInt(result.persons)}
                </div>
              </div>
            </CardContent>
            <CardFooter className="flex flex-wrap items-center justify-between gap-3 border-t border-ink/[0.06]">
              {matchResult ? (
                <span className="text-small text-ink-muted">
                  Знайдено:{" "}
                  <strong className="text-ink">
                    {formatInt(matchResult.findings_created)}
                  </strong>
                </span>
              ) : (
                <span className="text-small text-ink-muted">
                  {uk.upload.steps.analyze}
                </span>
              )}
              <Button
                onClick={() => matcherMut.mutate(result.dataset_id)}
                disabled={matcherMut.isPending || matchResult !== null}
                size="lg"
              >
                {matcherMut.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {uk.common.loading}
                  </>
                ) : matchResult ? (
                  <>
                    <Check className="h-4 w-4" />
                    {uk.upload.steps.review}
                  </>
                ) : (
                  <>
                    {uk.upload.runMatcher}
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </Button>
            </CardFooter>
          </Card>
        )}
      </div>
    </BackOfficeShell>
  );
}
