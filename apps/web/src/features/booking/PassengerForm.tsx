import type { BerthType, Gender } from "../../api/types";
import { Button } from "../../components/Button";
import { SelectField, TextField } from "../../components/Field";
import { BERTH_NAMES } from "../../lib/format";

export const MAX_PASSENGERS = 6;

export type PassengerDraft = {
  name: string;
  age: string;
  gender: Gender | "";
  berth_pref: BerthType | "";
};
export type PassengerErrors = Partial<Record<keyof PassengerDraft, string>>;

export const emptyPassenger = (): PassengerDraft => ({
  name: "",
  age: "",
  gender: "",
  berth_pref: "",
});

const NAME = /^[A-Za-z][A-Za-z .']*[A-Za-z.]$/;

export function validatePassenger(p: PassengerDraft): PassengerErrors {
  const errors: PassengerErrors = {};
  const name = p.name.trim();
  if (name.length < 2 || name.length > 50 || !NAME.test(name)) {
    errors.name = "2 to 50 letters; spaces, dots and apostrophes allowed.";
  }
  const age = Number(p.age);
  if (!p.age || !Number.isInteger(age) || age < 1 || age > 120) {
    errors.age = "Age must be 1 to 120.";
  }
  if (!p.gender) errors.gender = "Select a gender.";
  return errors;
}

const GENDERS = [
  { value: "", label: "Select" },
  { value: "F", label: "Female" },
  { value: "M", label: "Male" },
  { value: "T", label: "Transgender" },
];

const BERTHS = [
  { value: "", label: "No preference" },
  ...Object.entries(BERTH_NAMES).map(([value, label]) => ({ value, label })),
];

type Props = {
  passengers: PassengerDraft[];
  errors: PassengerErrors[];
  onChange: (passengers: PassengerDraft[]) => void;
};

export function PassengerForm({ passengers, errors, onChange }: Props) {
  function update(index: number, patch: Partial<PassengerDraft>) {
    onChange(passengers.map((p, i) => (i === index ? { ...p, ...patch } : p)));
  }

  return (
    <fieldset className="space-y-4">
      <legend className="mb-2 font-semibold">Passengers</legend>
      {passengers.map((p, i) => (
        <div
          key={i}
          className="grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-[2fr_5rem_8rem_9rem_auto] sm:items-start"
        >
          <TextField
            label={`Passenger ${i + 1} name`}
            value={p.name}
            maxLength={50}
            onChange={(e) => update(i, { name: e.target.value })}
            error={errors[i]?.name}
          />
          <TextField
            label="Age"
            inputMode="numeric"
            maxLength={3}
            value={p.age}
            onChange={(e) => update(i, { age: e.target.value.replace(/\D/g, "") })}
            error={errors[i]?.age}
          />
          <SelectField
            label="Gender"
            value={p.gender}
            options={GENDERS}
            onChange={(e) => update(i, { gender: e.target.value as Gender | "" })}
            error={errors[i]?.gender}
          />
          <SelectField
            label="Berth"
            value={p.berth_pref}
            options={BERTHS}
            onChange={(e) => update(i, { berth_pref: e.target.value as BerthType | "" })}
          />
          <div className="sm:pt-6">
            <Button
              variant="ghost"
              size="sm"
              disabled={passengers.length === 1}
              onClick={() => onChange(passengers.filter((_, j) => j !== i))}
              aria-label={`Remove passenger ${i + 1}`}
            >
              Remove
            </Button>
          </div>
        </div>
      ))}
      <Button
        variant="secondary"
        size="sm"
        disabled={passengers.length >= MAX_PASSENGERS}
        onClick={() => onChange([...passengers, emptyPassenger()])}
      >
        Add passenger
      </Button>
      {passengers.length >= MAX_PASSENGERS && (
        <p className="text-xs text-slate-500">
          A booking can have up to {MAX_PASSENGERS} passengers.
        </p>
      )}
    </fieldset>
  );
}
