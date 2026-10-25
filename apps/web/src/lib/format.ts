import type { BerthType, TravelClass } from "../api/types";

const IST = "Asia/Kolkata";

export const CLASS_NAMES: Record<TravelClass, string> = {
  SL: "Sleeper",
  "3A": "AC 3 Tier",
  "2A": "AC 2 Tier",
  "1A": "AC First Class",
};

export const BERTH_NAMES: Record<BerthType, string> = {
  LB: "Lower",
  MB: "Middle",
  UB: "Upper",
  SL: "Side lower",
  SU: "Side upper",
};

export const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export const ADVANCE_RESERVATION_DAYS = 60;

export function formatInr(paise: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: paise % 100 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(paise / 100);
}

export function formatTime(iso: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: IST,
  }).format(new Date(iso));
}

/** Works for both ISO dates ("2026-11-02") and ISO date-times. */
export function formatDate(iso: string, withYear = false): string {
  return new Intl.DateTimeFormat("en-IN", {
    weekday: "short",
    day: "numeric",
    month: "short",
    ...(withYear ? { year: "numeric" } : {}),
    timeZone: IST,
  }).format(new Date(iso));
}

export function formatDateTime(iso: string): string {
  return `${formatDate(iso, true)}, ${formatTime(iso)}`;
}

export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return hours ? `${hours}h ${String(rest).padStart(2, "0")}m` : `${rest}m`;
}

/** Today's date in India as YYYY-MM-DD. */
export function todayIst(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: IST }).format(now);
}

export function addDays(isoDate: string, days: number): string {
  const date = new Date(`${isoDate}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

/** Same calendar day in IST? */
export function sameIstDay(a: string, b: string): boolean {
  return todayIst(new Date(a)) === todayIst(new Date(b));
}
