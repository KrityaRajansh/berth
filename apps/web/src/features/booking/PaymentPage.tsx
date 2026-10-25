import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router";

import { ApiError, api, call, errorMessage } from "../../api/client";
import { Button } from "../../components/Button";
import { TextField } from "../../components/Field";
import { Alert, Card, PageHeader } from "../../components/Feedback";
import { Spinner } from "../../components/Spinner";
import { formatInr } from "../../lib/format";
import { JourneySummary } from "./JourneySummary";

type Method = "card" | "upi";

function useCountdown(until: string | undefined): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  return until ? Math.max(0, Math.floor((new Date(until).getTime() - now) / 1000)) : 0;
}

export function PaymentPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [method, setMethod] = useState<Method>("card");
  const [cardNumber, setCardNumber] = useState("");
  const [upiId, setUpiId] = useState("");

  const booking = useQuery({
    queryKey: ["booking", id],
    queryFn: () =>
      call(api.GET("/api/v1/bookings/{booking_id}", { params: { path: { booking_id: id } } })),
  });
  const secondsLeft = useCountdown(booking.data?.expires_at);

  const pay = useMutation({
    mutationFn: () =>
      call(
        api.POST("/api/v1/bookings/{booking_id}/payments", {
          params: { path: { booking_id: id } },
          body:
            method === "card"
              ? { method, card_number: cardNumber.replace(/\s/g, "") }
              : { method, upi_id: upiId.trim() },
        }),
      ),
    onSuccess: (paid) => {
      queryClient.setQueryData(["booking", id], paid);
      queryClient.invalidateQueries({ queryKey: ["bookings"] });
      queryClient.invalidateQueries({ queryKey: ["search"] });
      navigate(`/bookings/${id}`, { replace: true, state: { justBooked: true } });
    },
    onError: (error) => {
      // Anything other than a declined card changes the booking's status.
      if (error instanceof ApiError && error.status !== 402) {
        queryClient.invalidateQueries({ queryKey: ["booking", id] });
      }
    },
  });

  if (booking.isPending) return <Spinner label="Loading booking" />;
  if (booking.isError) return <Alert tone="error">{errorMessage(booking.error)}</Alert>;
  const b = booking.data;
  if (b.status === "BOOKED") return <Navigate to={`/bookings/${id}`} replace />;

  const expired = b.status === "EXPIRED" || secondsLeft === 0;
  const closed = b.status !== "PENDING_PAYMENT";

  function submit(event: FormEvent) {
    event.preventDefault();
    pay.mutate();
  }

  return (
    <section>
      <PageHeader title="Payment" subtitle="Step 2 of 2: pay to confirm your booking." />
      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <div className="space-y-4">
          {closed || expired ? (
            <Alert tone="warning" title="This booking can no longer be paid for">
              {b.status === "FAILED"
                ? "There were not enough berths or waitlist places when you paid. Nothing was charged."
                : "The 15-minute payment window has closed. Nothing was charged."}{" "}
              <Link to="/" className="underline">
                Search again
              </Link>
            </Alert>
          ) : (
            <Card>
              <p className="mb-4 text-sm text-slate-600" aria-live="polite">
                Complete payment within{" "}
                <strong>
                  {Math.floor(secondsLeft / 60)}:{String(secondsLeft % 60).padStart(2, "0")}
                </strong>{" "}
                minutes.
              </p>
              <div role="tablist" aria-label="Payment method" className="mb-4 flex gap-2">
                {(["card", "upi"] as const).map((m) => (
                  <Button
                    key={m}
                    role="tab"
                    aria-selected={method === m}
                    variant={method === m ? "primary" : "secondary"}
                    size="sm"
                    onClick={() => setMethod(m)}
                  >
                    {m === "card" ? "Card" : "UPI"}
                  </Button>
                ))}
              </div>
              <form onSubmit={submit} className="space-y-4">
                {pay.isError && (
                  <Alert tone="error">
                    {errorMessage(pay.error)}
                    {pay.error instanceof ApiError &&
                      pay.error.status === 402 &&
                      " You can try again."}
                  </Alert>
                )}
                {method === "card" ? (
                  <TextField
                    label="Card number"
                    inputMode="numeric"
                    autoComplete="off"
                    placeholder="4111 1111 1111 1111"
                    value={cardNumber}
                    onChange={(e) => setCardNumber(e.target.value)}
                  />
                ) : (
                  <TextField
                    label="UPI ID"
                    autoComplete="off"
                    placeholder="name@bank"
                    value={upiId}
                    onChange={(e) => setUpiId(e.target.value)}
                  />
                )}
                <Button type="submit" busy={pay.isPending}>
                  Pay {formatInr(b.total_fare_paise)}
                </Button>
              </form>
            </Card>
          )}
          <Alert tone="info" title="Simulated payment">
            No real money is charged. To approve, use card <code>4111 1111 1111 1111</code> or UPI{" "}
            <code>success@berth</code>. To see a decline, use card <code>4000 0000 0000 0002</code>{" "}
            or UPI <code>failure@berth</code>.
          </Alert>
        </div>

        <aside className="space-y-4">
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
          <Card>
            <h2 className="mb-2 font-semibold">Travellers</h2>
            <ul className="space-y-1 text-sm">
              {b.passengers.map((p) => (
                <li key={p.id} className="flex justify-between">
                  <span>{p.name}</span>
                  <span className="text-slate-500">
                    {p.age} {p.gender}
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-3 flex justify-between border-t border-slate-100 pt-3 font-semibold">
              <span>Total</span>
              <span>{formatInr(b.total_fare_paise)}</span>
            </p>
          </Card>
        </aside>
      </div>
    </section>
  );
}
