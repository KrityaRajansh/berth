import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";

import { api, call, errorMessage } from "../../api/client";
import type { BookingSummary } from "../../api/types";
import { ButtonLink } from "../../components/Button";
import { Alert, EmptyState, PageHeader } from "../../components/Feedback";
import { Spinner } from "../../components/Spinner";
import { StatusBadge } from "../../components/StatusBadge";
import { formatDateTime, formatInr } from "../../lib/format";

export function MyBookingsPage() {
  // Read the clock once per visit so the split does not change between renders.
  const [now] = useState(() => Date.now());
  const bookings = useQuery({
    queryKey: ["bookings"],
    queryFn: () => call(api.GET("/api/v1/bookings")),
  });

  if (bookings.isPending) return <Spinner label="Loading your bookings" />;
  if (bookings.isError) return <Alert tone="error">{errorMessage(bookings.error)}</Alert>;

  const upcoming = bookings.data
    .filter((b) => b.status === "BOOKED" && new Date(b.departure_at).getTime() > now)
    .sort((a, b) => a.departure_at.localeCompare(b.departure_at));
  const past = bookings.data.filter((b) => !upcoming.includes(b));

  return (
    <section className="space-y-8">
      <PageHeader title="My bookings" actions={<ButtonLink to="/">Book a ticket</ButtonLink>} />
      <BookingList title="Upcoming journeys" bookings={upcoming} empty="No upcoming journeys." />
      <BookingList title="Past and cancelled" bookings={past} empty="Nothing here yet." />
    </section>
  );
}

function BookingList({
  title,
  bookings,
  empty,
}: {
  title: string;
  bookings: BookingSummary[];
  empty: string;
}) {
  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">{title}</h2>
      {bookings.length === 0 ? (
        <EmptyState title={empty} />
      ) : (
        <ul className="divide-y divide-slate-100 rounded border border-slate-200 bg-white">
          {bookings.map((b) => (
            <li key={b.id}>
              <Link
                to={`/bookings/${b.id}`}
                className="grid gap-1 px-4 py-3 hover:bg-slate-50 sm:grid-cols-[1fr_auto] sm:items-center"
              >
                <div>
                  <p className="font-medium">
                    {b.from_station.name} to {b.to_station.name}
                  </p>
                  <p className="text-sm text-slate-600">
                    <span className="font-mono">{b.train_number}</span> {b.train_name} ·{" "}
                    {b.travel_class} · {formatDateTime(b.departure_at)}
                  </p>
                  <p className="text-xs text-slate-500">
                    PNR {b.pnr ?? "-"} · {b.passenger_count} passenger
                    {b.passenger_count === 1 ? "" : "s"} · {formatInr(b.total_fare_paise)}
                  </p>
                </div>
                <StatusBadge status={b.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
