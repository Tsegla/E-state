const NBSP = "\u00A0";
const ISO_WITH_TIMEZONE = /(?:[zZ]|[+-]\d{2}:\d{2})$/;
const ISO_DATETIME_WITHOUT_TIMEZONE = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$/;

const numberFormatter = new Intl.NumberFormat("uk-UA");
const areaFormatter = new Intl.NumberFormat("uk-UA", {
  maximumFractionDigits: 2,
});
const currencyFormatter = new Intl.NumberFormat("uk-UA", {
  style: "currency",
  currency: "UAH",
  maximumFractionDigits: 0,
});
const dateFormatter = new Intl.DateTimeFormat("uk-UA", {
  dateStyle: "medium",
  timeZone: "Europe/Kyiv",
});
const dateTimeFormatter = new Intl.DateTimeFormat("uk-UA", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "Europe/Kyiv",
});
const reportDateTimeFormatter = new Intl.DateTimeFormat("uk-UA", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "Europe/Kyiv",
});

function parseDateInput(value: string | Date): Date {
  if (value instanceof Date) return value;
  const normalized = value.trim();
  if (
    ISO_DATETIME_WITHOUT_TIMEZONE.test(normalized) &&
    !ISO_WITH_TIMEZONE.test(normalized)
  ) {
    return new Date(`${normalized.replace(" ", "T")}Z`);
  }
  return new Date(normalized);
}

export function formatInt(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return numberFormatter.format(value);
}

export function formatArea(m2: number | null | undefined): string {
  if (m2 === null || m2 === undefined || Number.isNaN(m2)) return "—";
  return `${areaFormatter.format(m2)}${NBSP}м²`;
}

export function formatHectares(m2: number | null | undefined): string {
  if (m2 === null || m2 === undefined || Number.isNaN(m2)) return "—";
  return `${areaFormatter.format(m2 / 10_000)}${NBSP}га`;
}

export function formatCurrency(uah: number | null | undefined): string {
  if (uah === null || uah === undefined || Number.isNaN(uah)) return "—";
  return currencyFormatter.format(uah);
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const date = parseDateInput(value);
  if (Number.isNaN(date.getTime())) return "—";
  return dateFormatter.format(date);
}

export function formatDateTime(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const date = parseDateInput(value);
  if (Number.isNaN(date.getTime())) return "—";
  return dateTimeFormatter.format(date);
}

export function formatReportDateTime(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const date = parseDateInput(value);
  if (Number.isNaN(date.getTime())) return "—";
  return `${reportDateTimeFormatter.format(date)} за Києвом`;
}
