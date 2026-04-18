const NBSP = "\u00A0";

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
});
const dateTimeFormatter = new Intl.DateTimeFormat("uk-UA", {
  dateStyle: "medium",
  timeStyle: "short",
});

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
  const date = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) return "—";
  return dateFormatter.format(date);
}

export function formatDateTime(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const date = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) return "—";
  return dateTimeFormatter.format(date);
}
