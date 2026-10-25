import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router";

import { api, call, errorMessage } from "../../api/client";
import type { SearchResult, TravelClass } from "../../api/types";
import { Button } from "../../components/Button";
import { SelectField } from "../../components/Field";
import { Alert, Card, EmptyState } from "../../components/Feedback";
import { Spinner } from "../../components/Spinner";
import { AvailabilityBadge } from "../../components/StatusBadge";
import {
  CLASS_NAMES,
  formatDate,
  formatDuration,
  formatInr,
  formatTime,
  sameIstDay,
} from "../../lib/format";
import { SearchForm, type SearchValues } from "./SearchForm";

type Sort = "departure" | "duration";

export function useSearchParamsValues(): SearchValues & { valid: boolean } {
  const [params] = useSearchParams();
  const from = params.get("from");
  const to = params.get("to");
  const date = params.get("date") ?? "";
  return {
    from: from ? { code: from, name: params.get("fromName") ?? from } : null,
    to: to ? { code: to, name: params.get("toName") ?? to } : null,
    date,
    cls: (params.get("cls") ?? "") as TravelClass | "",
    valid: Boolean(from && to && date),
  };
}

export function ResultsPage() {
  const values = useSearchParamsValues();
  const [sort, setSort] = useState<Sort>("departure");

  const search = useQuery({
    queryKey: ["search", values.from?.code, values.to?.code, values.date, values.cls],
    queryFn: () =>
      call(
        api.GET("/api/v1/trains/search", {
          params: {
            query: {
              from: values.from!.code,
              to: values.to!.code,
              date: values.date,
              cls: values.cls || undefined,
            },
          },
        }),
      ),
    enabled: values.valid,
  });

  const results = [...(search.data ?? [])].sort((a, b) =>
    sort === "duration"
      ? a.duration_minutes - b.duration_minutes
      : a.departure_at.localeCompare(b.departure_at),
  );

  return (
    <section className="space-y-6">
      <Card>
        <SearchForm key={JSON.stringify(values)} initial={values} compact />
      </Card>

      {values.valid && (
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold">
              {values.from!.name} to {values.to!.name}
            </h1>
            <p className="text-sm text-slate-600">
              {formatDate(values.date, true)}
              {search.data &&
                ` · ${search.data.length} train${search.data.length === 1 ? "" : "s"}`}
            </p>
          </div>
          <SelectField
            label="Sort by"
            className="w-44"
            value={sort}
            onChange={(e) => setSort(e.target.value as Sort)}
            options={[
              { value: "departure", label: "Departure time" },
              { value: "duration", label: "Journey time" },
            ]}
          />
        </div>
      )}

      {search.isPending && values.valid && <Spinner label="Searching trains" />}
      {search.isError && <Alert tone="error">{errorMessage(search.error)}</Alert>}
      {search.data && results.length === 0 && (
        <EmptyState title="No trains on this date">
          No train runs from {values.from!.name} to {values.to!.name} on {formatDate(values.date)}.
          Try another date.
        </EmptyState>
      )}
      <ul className="space-y-4">
        {results.map((result) => (
          <li key={result.run_id}>
            <TrainCard result={result} date={values.date} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function TrainCard({ result, date }: { result: SearchResult; date: string }) {
  const navigate = useNavigate();
  const arrivesLater = !sameIstDay(result.departure_at, result.arrival_at);

  function book(cls: TravelClass) {
    const params = new URLSearchParams({
      run: String(result.run_id),
      cls,
      from: result.from_station.code,
      fromName: result.from_station.name,
      to: result.to_station.code,
      toName: result.to_station.name,
      date,
    });
    navigate(`/book?${params}`);
  }

  return (
    <article className="rounded border border-slate-200 bg-white">
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-slate-100 px-4 py-3">
        <h2 className="font-semibold text-slate-900">
          <span className="font-mono text-brand-700">{result.train_number}</span>{" "}
          {result.train_name}
        </h2>
        <span className="text-xs text-slate-500">{result.distance_km} km</span>
      </header>

      <div className="grid grid-cols-[auto_1fr_auto] items-center gap-3 px-4 py-4">
        <div>
          <p className="text-xl font-semibold">{formatTime(result.departure_at)}</p>
          <p className="text-xs text-slate-600">
            {result.from_station.code} · {formatDate(result.departure_at)}
          </p>
        </div>
        <div className="flex flex-col items-center text-xs text-slate-500">
          <span>{formatDuration(result.duration_minutes)}</span>
          <span aria-hidden className="mt-1 h-px w-full bg-slate-300" />
        </div>
        <div className="text-right">
          <p className="text-xl font-semibold">{formatTime(result.arrival_at)}</p>
          <p className="text-xs text-slate-600">
            {result.to_station.code} · {formatDate(result.arrival_at)}
            {arrivesLater && <span className="sr-only"> (arrives on a later day)</span>}
          </p>
        </div>
      </div>

      <ul className="grid gap-px border-t border-slate-100 bg-slate-100 sm:grid-cols-2 lg:grid-cols-4">
        {result.classes.map((c) => {
          const bookable = c.status === "AVAILABLE" || c.status === "WAITLIST";
          return (
            <li key={c.travel_class} className="flex flex-col gap-2 bg-white px-4 py-3">
              <div className="flex items-baseline justify-between">
                <span className="font-semibold">{c.travel_class}</span>
                <span className="text-xs text-slate-500">{CLASS_NAMES[c.travel_class]}</span>
              </div>
              <div className="flex items-center justify-between">
                <AvailabilityBadge status={c.status} count={c.count} />
                <span className="font-semibold">{formatInr(c.fare.total_paise)}</span>
              </div>
              <Button
                size="sm"
                variant={bookable ? "primary" : "secondary"}
                disabled={!bookable}
                onClick={() => book(c.travel_class)}
                aria-label={`Book ${c.travel_class} on ${result.train_number}`}
              >
                {c.status === "WAITLIST" ? "Book waitlist" : "Book"}
              </Button>
            </li>
          );
        })}
      </ul>
    </article>
  );
}
