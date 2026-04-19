/**
 * Named endpoint functions. Components never format URLs themselves.
 */

import { apiDownload, apiFetch, apiFetchWithMeta } from "./client";
import type {
  AssignInspectorRequest,
  BudgetImpact,
  CitizenLookupResponse,
  DatasetSummary,
  FindingDetail,
  FindingStatus,
  FindingSummary,
  InspectorVisit,
  InspectorVisitCreate,
  MatcherRunResponse,
  SubscriptionQuote,
  ExecutiveSummary,
  Severity,
  UploadResponse,
} from "./types";

export const listDatasets = () => apiFetch<DatasetSummary[]>("/api/datasets");

export function uploadDataset(params: {
  zem: File;
  ner: File;
  label: string;
}): Promise<UploadResponse> {
  const form = new FormData();
  form.append("zem", params.zem);
  form.append("ner", params.ner);
  form.append("label", params.label);
  return apiFetch<UploadResponse>("/api/upload", { method: "POST", form });
}

export const runMatcher = (datasetId: string) =>
  apiFetch<MatcherRunResponse>("/api/matcher/run", {
    method: "POST",
    body: { dataset_id: datasetId },
  });

export const listFindings = (params: {
  datasetId: string;
  severity?: Severity;
  status?: FindingStatus;
  findingType?: string;
  koatuu?: string;
  q?: string;
  page?: number;
  limit?: number;
}) =>
  apiFetchWithMeta<FindingSummary[]>("/api/findings", {
    query: {
      dataset_id: params.datasetId,
      severity: params.severity,
      status: params.status,
      finding_type: params.findingType,
      koatuu: params.koatuu,
      q: params.q,
      page: params.page,
      limit: params.limit,
    },
  });

export const getFinding = (findingId: string) =>
  apiFetch<FindingDetail>(`/api/findings/${findingId}`);

export const assignFindingToInspector = (
  findingId: string,
  body: AssignInspectorRequest,
) =>
  apiFetch<FindingDetail>(`/api/findings/${findingId}/assign`, {
    method: "POST",
    body,
  });

export const inspectorFindings = (datasetId: string) =>
  apiFetch<FindingSummary[]>("/api/inspector/findings", {
    query: { dataset_id: datasetId },
  });

export const getInspectorFinding = (findingId: string) =>
  apiFetch<FindingDetail>(`/api/inspector/findings/${findingId}`);

export const createInspectorVisit = (body: InspectorVisitCreate) =>
  apiFetch<InspectorVisit>("/api/inspector/visits", { method: "POST", body });

export const budgetImpact = (datasetId: string) =>
  apiFetch<BudgetImpact>("/api/reports/budget-impact", { query: { dataset_id: datasetId } });

export const subscriptionQuoteForDataset = (datasetId: string) =>
  apiFetch<SubscriptionQuote>("/api/pricing/quote", {
    query: { dataset_id: datasetId },
  });

export function subscriptionQuoteFromUpload(file: File): Promise<SubscriptionQuote> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<SubscriptionQuote>("/api/pricing/quote-upload", {
    method: "POST",
    form,
    anonymous: true,
  });
}

export const executiveSummary = (params: {
  datasetId: string;
  severity?: Severity;
  status?: FindingStatus;
  findingType?: string;
  koatuu?: string;
  q?: string;
}) =>
  apiFetch<ExecutiveSummary>("/api/reports/executive-summary", {
    query: {
      dataset_id: params.datasetId,
      severity: params.severity,
      status: params.status,
      finding_type: params.findingType,
      koatuu: params.koatuu,
      q: params.q,
    },
  });

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadFindingsCsv(params: {
  datasetId: string;
  severity?: Severity;
  status?: FindingStatus;
  findingType?: string;
  koatuu?: string;
  q?: string;
}): Promise<void> {
  const { blob, filename } = await apiDownload("/api/reports/findings-export", {
    query: {
      dataset_id: params.datasetId,
      severity: params.severity,
      status: params.status,
      finding_type: params.findingType,
      koatuu: params.koatuu,
      q: params.q,
    },
  });
  downloadBlob(blob, filename ?? "findings.csv");
}

export async function downloadFindingsXlsx(params: {
  datasetId: string;
  severity?: Severity;
  status?: FindingStatus;
  findingType?: string;
  koatuu?: string;
  q?: string;
}): Promise<void> {
  const { blob, filename } = await apiDownload("/api/reports/findings-export.xlsx", {
    query: {
      dataset_id: params.datasetId,
      severity: params.severity,
      status: params.status,
      finding_type: params.findingType,
      koatuu: params.koatuu,
      q: params.q,
    },
  });
  downloadBlob(blob, filename ?? "findings.xlsx");
}

export async function downloadExecutivePdf(params: {
  datasetId: string;
  severity?: Severity;
  status?: FindingStatus;
  findingType?: string;
  koatuu?: string;
  q?: string;
}): Promise<void> {
  const { blob, filename } = await apiDownload("/api/reports/executive.pdf", {
    query: {
      dataset_id: params.datasetId,
      severity: params.severity,
      status: params.status,
      finding_type: params.findingType,
      koatuu: params.koatuu,
      q: params.q,
    },
  });
  downloadBlob(blob, filename ?? "executive-report.pdf");
}

export const citizenLookup = (body: { tax_id: string; captcha_token: string; consent: boolean }) =>
  apiFetch<CitizenLookupResponse>("/api/citizen/lookup", {
    method: "POST",
    body,
    anonymous: true,
  });
