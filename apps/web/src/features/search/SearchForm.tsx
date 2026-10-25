import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";

import type { TravelClass } from "../../api/types";
import { Button } from "../../components/Button";
import { SelectField, TextField } from "../../components/Field";
import { StationPicker, type StationValue } from "../../components/StationPicker";
import { ADVANCE_RESERVATION_DAYS, CLASS_NAMES, addDays, todayIst } from "../../lib/format";

export type SearchValues = {
  from: StationValue;
  to: StationValue;
  date: string;
  cls: TravelClass | "";
};

type Errors = Partial<Record<"from" | "to" | "date", string>>;

export function validateSearch(values: SearchValues, today: string): Errors {
  const errors: Errors = {};
  if (!values.from) errors.from = "Choose a station from the list.";
  if (!values.to) errors.to = "Choose a station from the list.";
  if (values.from && values.to && values.from.code === values.to.code) {
    errors.to = "Destination must be different from the source.";
  }
  if (!values.date) errors.date = "Choose a journey date.";
  else if (values.date < today) errors.date = "The date is in the past.";
  else if (values.date > addDays(today, ADVANCE_RESERVATION_DAYS)) {
    errors.date = `Bookings open ${ADVANCE_RESERVATION_DAYS} days ahead.`;
  }
  return errors;
}

export function searchUrl(values: SearchValues): string {
  const params = new URLSearchParams({
    from: values.from!.code,
    fromName: values.from!.name,
    to: values.to!.code,
    toName: values.to!.name,
    date: values.date,
  });
  if (values.cls) params.set("cls", values.cls);
  return `/trains?${params}`;
}

const CLASS_OPTIONS = [
  { value: "", label: "All classes" },
  ...Object.entries(CLASS_NAMES).map(([value, name]) => ({ value, label: `${name} (${value})` })),
];

export function SearchForm({
  initial,
  compact = false,
}: {
  initial?: SearchValues;
  compact?: boolean;
}) {
  const navigate = useNavigate();
  const today = todayIst();
  const [values, setValues] = useState<SearchValues>(
    initial ?? { from: null, to: null, date: addDays(today, 1), cls: "" },
  );
  const [errors, setErrors] = useState<Errors>({});
  const [swapCount, setSwapCount] = useState(0);

  function submit(event: FormEvent) {
    event.preventDefault();
    const found = validateSearch(values, today);
    setErrors(found);
    if (Object.keys(found).length === 0) navigate(searchUrl(values));
  }

  function swap() {
    setValues((v) => ({ ...v, from: v.to, to: v.from }));
    setSwapCount((n) => n + 1);
  }

  return (
    <form
      onSubmit={submit}
      noValidate
      aria-label="Search trains"
      className={`grid gap-4 ${compact ? "md:grid-cols-[1fr_auto_1fr_10rem_10rem_auto]" : "md:grid-cols-[1fr_auto_1fr]"} items-start`}
    >
      <StationPicker
        key={`from-${swapCount}`}
        label="From"
        value={values.from}
        onChange={(from) => setValues((v) => ({ ...v, from }))}
        error={errors.from}
      />
      <div className="md:pt-6">
        <Button variant="secondary" onClick={swap} aria-label="Swap source and destination">
          <span aria-hidden>⇄</span>
        </Button>
      </div>
      <StationPicker
        key={`to-${swapCount}`}
        label="To"
        value={values.to}
        onChange={(to) => setValues((v) => ({ ...v, to }))}
        error={errors.to}
      />
      <div className={compact ? "contents" : "grid gap-4 sm:grid-cols-2 md:col-span-3"}>
        <TextField
          label="Journey date"
          type="date"
          min={today}
          max={addDays(today, ADVANCE_RESERVATION_DAYS)}
          value={values.date}
          onChange={(e) => setValues((v) => ({ ...v, date: e.target.value }))}
          error={errors.date}
        />
        <SelectField
          label="Class"
          value={values.cls}
          onChange={(e) => setValues((v) => ({ ...v, cls: e.target.value as TravelClass | "" }))}
          options={CLASS_OPTIONS}
        />
      </div>
      <div className={compact ? "md:pt-6" : "md:col-span-3"}>
        <Button type="submit" className={compact ? "w-full" : "w-full md:w-auto"}>
          Search trains
        </Button>
      </div>
    </form>
  );
}
