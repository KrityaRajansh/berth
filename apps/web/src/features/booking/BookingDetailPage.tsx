import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useLocation, useParams } from "react-router";

import { api, call, errorMessage } from "../../api/client";
import type { BookingOut, RefundQuote } from "../../api/types";
import { Button, ButtonLink, buttonClass } from "../../components/Button";
import { Alert, Card, PageHeader } from "../../components/Feedback";
import { Spinner } from "../../components/Spinner";
import { StatusBadge } from "../../components/StatusBadge";
import { formatDateTime, formatInr } from "../../lib/format";
import { JourneySummary } from "./JourneySummary";

export function BookingDetailPage() {
  const { id = "" } = useParams();
  const location = useLocation();
  const justBooked = Boolean((location.state as { justBooked?: boolean } | null)?.justBooked);

  const booking = useQuery({
    queryKey: ["booking", id],
    queryFn: () =>
      call(api.GET("/api/v1/bookings/{booking_id}", { params: { path: { booking_id: id } } })),
  });

  if (booking.isPending) return <Spinner label="Loading booking" />;
  if (booking.isError) return <Alert tone="error">{errorMessage(booking.error)}</Alert>;
  const b = booking.data;
  const waitlisted = b.passengers.filter((p) => p.current_status.startsWith("WL")).length;

  return (
    <section className="space-y-6">
      <PageHeader
        title={b.pnr ? `PNR ${b.pnr}` : "Booking"}
        subtitle={<StatusBadge status={b.status} />}
        actions={
          <>
            {b.status === "PENDING_PAYMENT" && (
              <ButtonLink to={`/bookings/${b.id}/pay`}>Pay now</ButtonLink>
            )}
            {b.pnr && (
              <a
                href={`/api/v1/bookings/${b.id}/ticket.pdf`}
                className={buttonClass("secondary")}
                download
              >
                Download e-ticket (PDF)
              </a>
            )}
          </>
        }
      />

      {justBooked && b.status === "BOOKED" && (
        <Alert tone={waitlisted ? "warning" : "success"} title="Booking confirmed">
          {waitlisted
            ? `${waitlisted} passenger${waitlisted > 1 ? "s are" : " is"} on the waitlist and will be confirmed automatically if berths become free before the chart is prepared.`
            : "All passengers have confirmed berths."}
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <div className="space-y-6">
          <Card>
            <JourneySummary
              trainNumber={b.train_number}
              trainName={b.train_name}
              travelClass={b.travel_class}
              from={b.from_station}
              to={b.to_station}
              departureAt={b.departure_at}
              arrivalAt={b.arrival_at}
            />
          </Card>
          <PassengersCard booking={b} />
        </div>
        <aside className="space-y-4">
          <Card>
            <h2 className="mb-3 font-semibold">Payment</h2>
            <dl className="space-y-1 text-sm">
              <div className="flex justify-between">
                <dt>Total fare</dt>
                <dd className="font-semibold">{formatInr(b.total_fare_paise)}</dd>
              </div>
              {b.refunded_paise > 0 && (
                <div className="flex justify-between">
                  <dt>Refunded</dt>
                  <dd>{formatInr(b.refunded_paise)}</dd>
                </div>
              )}
              <div className="flex justify-between text-slate-500">
                <dt>Booked on</dt>
                <dd>{formatDateTime(b.created_at)}</dd>
              </div>
            </dl>
          </Card>
          {b.chart_prepared && b.status === "BOOKED" && (
            <Alert tone="info">The chart has been prepared. Berths are final.</Alert>
          )}
        </aside>
      </div>
    </section>
  );
}

function PassengersCard({ booking }: { booking: BookingOut }) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<number[]>([]);
  const [quote, setQuote] = useState<RefundQuote | null>(null);
  const cancellable = booking.passengers.filter(
    (p) => p.current_status.startsWith("CNF") || p.current_status.startsWith("WL"),
  );
  const path = { params: { path: { booking_id: booking.id } } };

  const getQuote = useMutation({
    mutationFn: () =>
      call(
        api.POST("/api/v1/bookings/{booking_id}/cancellation-quote", {
          ...path,
          body: { passenger_ids: selected },
        }),
      ),
    onSuccess: setQuote,
  });
  const cancel = useMutation({
    mutationFn: () =>
      call(
        api.POST("/api/v1/bookings/{booking_id}/cancellations", {
          ...path,
          body: { passenger_ids: selected },
        }),
      ),
    onSuccess: (updated) => {
      queryClient.setQueryData(["booking", booking.id], updated);
      queryClient.invalidateQueries({ queryKey: ["bookings"] });
      setSelected([]);
      setQuote(null);
    },
  });

  function toggle(id: number) {
    setQuote(null);
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  return (
    <Card>
      <h2 className="mb-3 font-semibold">Passengers</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-slate-500 uppercase">
            <tr>
              {booking.can_cancel && <th className="py-2 pr-2">Cancel</th>}
              <th className="py-2 pr-3">#</th>
              <th className="py-2 pr-3">Name</th>
              <th className="py-2 pr-3">Age</th>
              <th className="py-2 pr-3">Booked as</th>
              <th className="py-2 pr-3">Current status</th>
              <th className="py-2 text-right">Refund</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {booking.passengers.map((p) => {
              const active = cancellable.some((c) => c.id === p.id);
              return (
                <tr key={p.id}>
                  {booking.can_cancel && (
                    <td className="py-2 pr-2">
                      {active && (
                        <input
                          type="checkbox"
                          aria-label={`Select ${p.name} for cancellation`}
                          checked={selected.includes(p.id)}
                          onChange={() => toggle(p.id)}
                        />
                      )}
                    </td>
                  )}
                  <td className="py-2 pr-3">{p.seq_no}</td>
                  <td className="py-2 pr-3">{p.name}</td>
                  <td className="py-2 pr-3">
                    {p.age} {p.gender}
                  </td>
                  <td className="py-2 pr-3 font-mono text-xs">{p.booking_status ?? "-"}</td>
                  <td className="py-2 pr-3">
                    <StatusBadge status={p.current_status} />
                  </td>
                  <td className="py-2 text-right">
                    {p.refund_paise ? formatInr(p.refund_paise) : "-"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {booking.can_cancel && (
        <div className="mt-4 space-y-3 border-t border-slate-100 pt-4">
          {(getQuote.isError || cancel.isError) && (
            <Alert tone="error">{errorMessage(getQuote.error ?? cancel.error)}</Alert>
          )}
          {quote ? (
            <Alert tone="warning" title={`Refund: ${formatInr(quote.total_refund_paise)}`}>
              <p>Cancelling {quote.lines.map((l) => l.name).join(", ")} cannot be undone.</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  variant="danger"
                  size="sm"
                  busy={cancel.isPending}
                  onClick={() => cancel.mutate()}
                >
                  Confirm cancellation
                </Button>
                <Button variant="secondary" size="sm" onClick={() => setQuote(null)}>
                  Keep tickets
                </Button>
              </div>
            </Alert>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              disabled={selected.length === 0}
              busy={getQuote.isPending}
              onClick={() => getQuote.mutate()}
            >
              Check refund for {selected.length || "selected"} passenger
              {selected.length === 1 ? "" : "s"}
            </Button>
          )}
        </div>
      )}
    </Card>
  );
}
