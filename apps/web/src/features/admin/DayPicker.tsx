import { DAY_NAMES } from "../../lib/format";

export function DayPicker({
  value,
  onChange,
}: {
  value: number[];
  onChange: (days: number[]) => void;
}) {
  function toggle(day: number) {
    onChange(
      value.includes(day) ? value.filter((d) => d !== day) : [...value, day].sort((a, b) => a - b),
    );
  }
  return (
    <fieldset>
      <legend className="mb-1 text-sm font-medium text-slate-700">Runs on</legend>
      <div className="flex flex-wrap gap-1">
        {DAY_NAMES.map((name, day) => (
          <label
            key={name}
            className={`cursor-pointer rounded border px-2 py-1.5 text-xs font-medium ${
              value.includes(day)
                ? "border-brand-600 bg-brand-50 text-brand-700"
                : "border-slate-300 bg-white text-slate-600"
            }`}
          >
            <input
              type="checkbox"
              className="sr-only"
              checked={value.includes(day)}
              onChange={() => toggle(day)}
            />
            {name}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
