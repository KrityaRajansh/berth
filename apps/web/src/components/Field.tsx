import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";

const CONTROL =
  "block w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 " +
  "placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 " +
  "focus:ring-brand-600/20 disabled:bg-slate-100 aria-[invalid=true]:border-red-600";

type FieldProps = {
  label: string;
  error?: string;
  hint?: ReactNode;
  className?: string;
  children: (props: {
    id: string;
    "aria-invalid": boolean;
    "aria-describedby"?: string;
  }) => ReactNode;
};

export function Field({ label, error, hint, className = "", children }: FieldProps) {
  const id = useId();
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-slate-700">
        {label}
      </label>
      {children({ id, "aria-invalid": Boolean(error), "aria-describedby": describedBy })}
      {error ? (
        <p id={`${id}-error`} className="mt-1 text-xs text-red-700">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="mt-1 text-xs text-slate-500">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
  hint?: ReactNode;
};

export function TextField({ label, error, hint, className, ...rest }: InputProps) {
  return (
    <Field label={label} error={error} hint={hint} className={className}>
      {(a11y) => <input className={CONTROL} {...a11y} {...rest} />}
    </Field>
  );
}

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  error?: string;
  options: { value: string; label: string }[];
};

export function SelectField({ label, error, options, className, ...rest }: SelectProps) {
  return (
    <Field label={label} error={error} className={className}>
      {(a11y) => (
        <select className={CONTROL} {...a11y} {...rest}>
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      )}
    </Field>
  );
}

export { CONTROL as controlClass };
