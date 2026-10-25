type Tone = "green" | "amber" | "red" | "slate" | "blue";

const TONES: Record<Tone, string> = {
  green: "bg-green-100 text-green-800",
  amber: "bg-amber-100 text-amber-900",
  red: "bg-red-100 text-red-800",
  slate: "bg-slate-200 text-slate-700",
  blue: "bg-brand-50 text-brand-700",
};

const LABELS: Record<string, string> = {
  PENDING_PAYMENT: "Awaiting payment",
  BOOKED: "Booked",
  FAILED: "Failed",
  EXPIRED: "Expired",
  CANCELLED: "Cancelled",
  COMPLETED: "Completed",
  SCHEDULED: "Scheduled",
  CHART_PREPARED: "Chart prepared",
  RUNNING: "Running",
  SUCCEEDED: "Succeeded",
  CAN: "Cancelled",
  PENDING: "Pending",
};

export function statusTone(status: string): Tone {
  if (status.startsWith("CNF")) return "green";
  if (status.startsWith("WL")) return "amber";
  switch (status) {
    case "BOOKED":
    case "SUCCEEDED":
    case "SCHEDULED":
      return "green";
    case "PENDING_PAYMENT":
    case "PENDING":
    case "RUNNING":
      return "amber";
    case "FAILED":
    case "CANCELLED":
    case "CAN":
      return "red";
    case "COMPLETED":
    case "CHART_PREPARED":
      return "blue";
    default:
      return "slate";
  }
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-xs font-semibold whitespace-nowrap ${TONES[statusTone(status)]}`}
    >
      {LABELS[status] ?? status}
    </span>
  );
}

/** Availability for a class on a train, as shown in search results. */
export function AvailabilityBadge({ status, count }: { status: string; count: number }) {
  const [tone, text]: [Tone, string] =
    status === "AVAILABLE"
      ? ["green", `Available ${count}`]
      : status === "WAITLIST"
        ? ["amber", `WL ${count}`]
        : status === "NOT_AVAILABLE"
          ? ["red", "Not available"]
          : status === "CANCELLED"
            ? ["red", "Train cancelled"]
            : ["slate", "Booking closed"];
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${TONES[tone]}`}>
      {text}
    </span>
  );
}
