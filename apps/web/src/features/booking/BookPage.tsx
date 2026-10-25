import { useMutation, useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";

import { api, call, errorMessage } from "../../api/client";
import type { TravelClass } from "../../api/types";
import { Button } from "../../components/Button";
import { Alert, Card, PageHeader } from "../../components/Feedback";
import { Spinner } from "../../components/Spinner";
import { AvailabilityBadge } from "../../components/StatusBadge";
import { useMe } from "../../lib/auth";
import { formatInr } from "../../lib/format";
import { JourneySummary } from "./JourneySummary";
import {
  PassengerForm,
  emptyPassenger,
  validatePassenger,
  type PassengerDraft,
  type PassengerErrors,
} from "./PassengerForm";

export function BookPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { data: user } = useMe();
  const runId = Number(params.get("run"));
  const cls = params.get("cls") as TravelClass;
  const from = params.get("from") ?? "";
  const to = params.get("to") ?? "";
  const date = params.get("date") ?? "";

  // Re-read the train from search so the page also works after a reload.
  const search = useQuery({
    queryKey: ["search", from, to, date, cls],
    queryFn: () =>
      call(api.GET("/api/v1/trains/search", { params: { query: { from, to, date, cls } } })),
    enabled: Boolean(runId && cls && from && to && date),
  });
  const result = search.data?.find((r) => r.run_id === runId);
  const availability = result?.classes.find((c) => c.travel_class === cls);

  const [passengers, setPassengers] = useState<PassengerDraft[]>(() => [
    { ...emptyPassenger(), name: user?.full_name ?? "" },
  ]);
  const [errors, setErrors] = useState<PassengerErrors[]>([]);
  const [confirmOnly, setConfirmOnly] = useState(false);

  const create = useMutation({
    mutationFn: () =>
      call(
        api.POST("/api/v1/bookings", {
          body: {
            run_id: runId,
            travel_class: cls,
            from_code: from,
            to_code: to,
            confirm_only: confirmOnly,
            passengers: passengers.map((p) => ({
              name: p.name.trim(),
              age: Number(p.age),
              gender: p.gender as "M" | "F" | "T",
              berth_pref: p.berth_pref || null,
            })),
          },
        }),
      ),
    onSuccess: (booking) => navigate(`/bookings/${booking.id}/pay`),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    const found = passengers.map(validatePassenger);
    setErrors(found);
    if (found.every((e) => Object.keys(e).length === 0)) create.mutate();
  }

  if (search.isPending) return <Spinner label="Loading train details" />;
  if (search.isError) return <Alert tone="error">{errorMessage(search.error)}</Alert>;
  if (!result || !availability) {
    return (
      <Alert tone="warning" title="This train is no longer available for booking">
        <Link to="/" className="underline">
          Search again
        </Link>
      </Alert>
    );
  }

  const farePerPassenger = availability.fare.total_paise;
  const bookable = availability.status === "AVAILABLE" || availability.status === "WAITLIST";

  return (
    <section>
      <PageHeader title="Passenger details" subtitle="Step 1 of 2: enter travellers, then pay." />
      <div className="grid gap-6 lg:grid-cols-[1fr_20rem] [&>*]:min-w-0">
        <form onSubmit={submit} noValidate className="space-y-6">
          <Card>
            <PassengerForm passengers={passengers} errors={errors} onChange={setPassengers} />
          </Card>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              className="mt-0.5"
              checked={confirmOnly}
              onChange={(e) => setConfirmOnly(e.target.checked)}
            />
            <span>
              Book only if every passenger gets a confirmed berth. If not, the booking is rejected
              and nothing is charged.
            </span>
          </label>
          {create.isError && <Alert tone="error">{errorMessage(create.error)}</Alert>}
          <Button type="submit" busy={create.isPending} disabled={!bookable}>
            Continue to payment
          </Button>
        </form>

        <aside className="space-y-4">
          <Card>
            <JourneySummary
              trainNumber={result.train_number}
              trainName={result.train_name}
              travelClass={cls}
              from={result.from_station}
              to={result.to_station}
              departureAt={result.departure_at}
              arrivalAt={result.arrival_at}
            />
            <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
              <span className="text-sm text-slate-600">Availability</span>
              <AvailabilityBadge status={availability.status} count={availability.count} />
            </div>
          </Card>
          <Card>
            <h2 className="mb-3 font-semibold">Fare</h2>
            <dl className="space-y-1 text-sm">
              <Row label="Base fare" value={formatInr(availability.fare.base_paise)} />
              <Row
                label="Reservation charge"
                value={formatInr(availability.fare.reservation_paise)}
              />
              <Row label="GST" value={formatInr(availability.fare.gst_paise)} />
              <Row label="Per passenger" value={formatInr(farePerPassenger)} strong />
              <Row
                label={`Total for ${passengers.length}`}
                value={formatInr(farePerPassenger * passengers.length)}
                strong
              />
            </dl>
          </Card>
        </aside>
      </div>
    </section>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className={`flex justify-between ${strong ? "font-semibold" : ""}`}>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
