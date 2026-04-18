"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, UploadCloud } from "lucide-react";
import { useState } from "react";

import { BackOfficeShell } from "@/components/back-office-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { uk } from "@/i18n/uk";
import { formatInt } from "@/i18n/format";
import { runMatcher, uploadDataset } from "@/lib/api/endpoints";
import type { MatcherRunResponse, UploadResponse } from "@/lib/api/types";

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

  const canSubmit = zemFile && nerFile && label.trim().length > 0 && !uploadMut.isPending;

  return (
    <BackOfficeShell>
      <div className="mx-auto flex max-w-2xl flex-col gap-6">
        <div className="flex flex-col gap-1">
          <h1 className="text-display text-ink">{uk.upload.title}</h1>
          <p className="text-small">{uk.upload.subtitle}</p>
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
                <CardTitle className="flex items-center gap-2">
                  <UploadCloud className="h-5 w-5 text-forest-700" />
                  {uk.upload.title}
                </CardTitle>
                <CardDescription>{uk.upload.subtitle}</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <div className="flex flex-col gap-1.5">
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
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="zem">{uk.upload.zemLabel}</Label>
                  <Input
                    id="zem"
                    type="file"
                    accept=".xlsx"
                    onChange={(e) => setZemFile(e.target.files?.[0] ?? null)}
                    required
                  />
                  <p className="text-meta text-ink-muted">{uk.upload.zemHint}</p>
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="ner">{uk.upload.nerLabel}</Label>
                  <Input
                    id="ner"
                    type="file"
                    accept=".xlsx"
                    onChange={(e) => setNerFile(e.target.files?.[0] ?? null)}
                    required
                  />
                  <p className="text-meta text-ink-muted">{uk.upload.nerHint}</p>
                </div>
                {uploadMut.error ? (
                  <p className="text-sm text-rose-700">
                    {(uploadMut.error as Error).message}
                  </p>
                ) : null}
              </CardContent>
              <CardFooter>
                <Button type="submit" disabled={!canSubmit}>
                  {uploadMut.isPending ? uk.upload.submitting : uk.upload.submit}
                </Button>
              </CardFooter>
            </form>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-forest-700">
                <CheckCircle2 className="h-5 w-5" />
                {uk.upload.resultTitle}
              </CardTitle>
              <CardDescription>{result.label}</CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-3 gap-4 text-small">
              <div>
                <div className="text-meta">{uk.upload.fields.zem}</div>
                <div className="text-h2 tabular text-ink">{formatInt(result.zem_rows)}</div>
              </div>
              <div>
                <div className="text-meta">{uk.upload.fields.ner}</div>
                <div className="text-h2 tabular text-ink">{formatInt(result.ner_rows)}</div>
              </div>
              <div>
                <div className="text-meta">{uk.upload.fields.persons}</div>
                <div className="text-h2 tabular text-ink">{formatInt(result.persons)}</div>
              </div>
            </CardContent>
            <CardFooter className="flex flex-wrap gap-2">
              <Button
                onClick={() => matcherMut.mutate(result.dataset_id)}
                disabled={matcherMut.isPending || matchResult !== null}
              >
                {matcherMut.isPending ? uk.common.loading : uk.upload.runMatcher}
              </Button>
              {matchResult ? (
                <span className="text-small">
                  Знайдено: <strong className="text-ink">{formatInt(matchResult.findings_created)}</strong>
                </span>
              ) : null}
            </CardFooter>
          </Card>
        )}
      </div>
    </BackOfficeShell>
  );
}
