import type { TravelClass } from "../../api/types";
import { CLASS_NAMES, formatDate, formatDuration, formatTime } from "../../lib/format";

type Props = {
  trainNumber: string;
  trainName: string;
  travelClass: TravelClass;
  from: { code: string; name: string };
  to: { code: string; name: string };
  departureAt: string;
  arrivalAt: string;
};

export function JourneySummary(props: Props) {
  const minutes = Math.round(
    (new Date(props.arrivalAt).getTime() - new Date(props.departureAt).getTime()) / 60_000,
  );
  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600">
        <span className="font-mono font-semibold text-brand-700">{props.trainNumber}</span>{" "}
        {props.trainName} · {props.travelClass} ({CLASS_NAMES[props.travelClass]})
      </p>
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        <div>
          <p className="text-lg font-semibold">{formatTime(props.departureAt)}</p>
          <p className="text-sm">{props.from.name}</p>
          <p className="text-xs text-slate-500">{formatDate(props.departureAt, true)}</p>
        </div>
        <span className="text-xs text-slate-500">{formatDuration(minutes)}</span>
        <div className="text-right">
          <p className="text-lg font-semibold">{formatTime(props.arrivalAt)}</p>
          <p className="text-sm">{props.to.name}</p>
          <p className="text-xs text-slate-500">{formatDate(props.arrivalAt, true)}</p>
        </div>
      </div>
    </div>
  );
}
