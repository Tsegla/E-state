/**
 * Named endpoint functions. Components never format URLs themselves.
 */

import { apiFetch } from "./client";
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
  page?: number;
  limit?: number;
}) =>
  apiFetch<FindingSummary[]>("/api/findings", {
    query: {
      dataset_id: params.datasetId,
      severity: params.severity,
      status: params.status,
      finding_type: params.findingType,
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

export const citizenLookup = (body: { tax_id: string; captcha_token: string; consent: boolean }) =>
  apiFetch<CitizenLookupResponse>("/api/citizen/lookup", {
    method: "POST",
    body,
    anonymous: true,
  });
