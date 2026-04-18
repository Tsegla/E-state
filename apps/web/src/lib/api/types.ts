/**
 * Typed DTOs mirroring ``services/api/app/api/schemas.py``.
 * Post-hackathon these are regenerated via ``openapi-typescript`` — for now
 * they live by hand so the demo ships.
 */

export type Severity = "critical" | "warning" | "info";
export type FindingStatus = "open" | "in_review" | "resolved" | "dismissed";
export type FindingType =
  | "LAND_NO_REAL_ESTATE"
  | "REAL_ESTATE_NO_LAND"
  | "USE_VS_OBJECT_MISMATCH"
  | "AREA_PORTFOLIO_DELTA"
  | "OWNER_NAME_MISMATCH"
  | "TERMINATED_BUT_ACTIVE"
  | "TERMINATED_RIGHTS_MISMATCH"
  | "MISSING_OWNER"
  | "DUPLICATE_REGISTRATION";

export interface Meta {
  total: number;
  page: number;
  limit: number;
}

export interface ApiResponse<T> {
  success: true;
  data: T;
  meta?: Meta;
}

export interface ApiError {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    trace_id?: string;
  };
}

export interface DatasetSummary {
  id: string;
  label: string;
  uploaded_at: string;
  uploaded_by: string | null;
  status: string;
  zem_rows: number;
  ner_rows: number;
  findings_total: number;
}

export interface FindingSummary {
  id: string;
  dataset_id: string;
  person_tax_id_masked: string;
  finding_type: FindingType;
  severity: Severity;
  status: FindingStatus;
  computed_metrics: Record<string, unknown>;
  detected_at: string;
}

export interface FindingEvidence {
  kind: "land_parcel" | "real_estate";
  ref_id: string;
  snapshot: Record<string, unknown>;
}

export interface FindingDetail extends FindingSummary {
  evidence: FindingEvidence[];
  person_name_masked: string;
}

export interface MatcherRunResponse {
  dataset_id: string;
  findings_created: number;
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
  duration_ms: number;
}

export interface UploadResponse {
  dataset_id: string;
  label: string;
  zem_rows: number;
  ner_rows: number;
  persons: number;
}

export interface BudgetImpact {
  total_uah_per_year: number;
  by_type: Record<string, number>;
}

export interface CitizenAsset {
  kind: "land_parcel" | "real_estate";
  label: string;
  area_m2: number;
  location_masked: string | null;
}

export interface CitizenLookupResponse {
  owner_name_masked: string;
  assets: CitizenAsset[];
  unresolved_findings: number;
  last_checked_at: string;
}

export interface InspectorVisitCreate {
  finding_id: string;
  actual_object_type?: string | null;
  actual_area_m2?: number | null;
  actual_use?: string | null;
  notes?: string | null;
  gps?: { lat: number; lng: number } | null;
  photo_refs?: Record<string, unknown>[];
  resolution: FindingStatus;
}

export interface InspectorVisit {
  id: string;
  finding_id: string;
  inspector_id: string;
  actual_object_type: string | null;
  actual_area_m2: number | null;
  actual_use: string | null;
  notes: string | null;
  gps: { lat: number; lng: number } | null;
  photo_refs: Record<string, unknown>[];
  created_at: string;
}
