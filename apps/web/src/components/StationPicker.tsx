import { useQuery } from "@tanstack/react-query";
import { useId, useState, type KeyboardEvent } from "react";

import { api, call } from "../api/client";
import type { StationOut } from "../api/types";
import { useDebounced } from "../lib/useDebounced";
import { controlClass } from "./Field";

export type StationValue = { code: string; name: string } | null;

type Props = {
  label: string;
  value: StationValue;
  onChange: (station: StationValue) => void;
  error?: string;
};

/** Accessible combobox that suggests stations as the user types (FR-SRCH-01). */
export function StationPicker({ label, value, onChange, error }: Props) {
  const id = useId();
  const listId = `${id}-list`;
  const [text, setText] = useState(value ? `${value.name} (${value.code})` : "");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const query = useDebounced(text.trim(), 200);

  const { data: suggestions = [] } = useQuery({
    queryKey: ["stations", query],
    queryFn: () => call(api.GET("/api/v1/stations", { params: { query: { q: query } } })),
    enabled: open && query.length >= 1,
    staleTime: 60_000,
  });

  function choose(station: StationOut) {
    onChange({ code: station.code, name: station.name });
    setText(`${station.name} (${station.code})`);
    setOpen(false);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!open && event.key === "ArrowDown") {
      setOpen(true);
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (event.key === "Enter" && open && suggestions[active]) {
      event.preventDefault();
      choose(suggestions[active]);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  const showList = open && suggestions.length > 0;
  return (
    <div className="relative">
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-slate-700">
        {label}
      </label>
      <input
        id={id}
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={showList ? `${listId}-${active}` : undefined}
        aria-invalid={Boolean(error)}
        autoComplete="off"
        placeholder="Station name or code"
        className={controlClass}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          setOpen(true);
          setActive(0);
          if (value) onChange(null);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={onKeyDown}
      />
      {showList && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded border border-slate-200 bg-white py-1 shadow-lg"
        >
          {suggestions.map((station, i) => (
            <li
              key={station.code}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              className={`flex cursor-pointer justify-between gap-3 px-3 py-2 text-sm ${
                i === active ? "bg-brand-50" : ""
              }`}
              onMouseDown={(e) => e.preventDefault()}
              onMouseEnter={() => setActive(i)}
              onClick={() => choose(station)}
            >
              <span>{station.name}</span>
              <span className="font-mono text-xs text-slate-500">{station.code}</span>
            </li>
          ))}
        </ul>
      )}
      {error && <p className="mt-1 text-xs text-red-700">{error}</p>}
    </div>
  );
}
