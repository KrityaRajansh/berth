import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router";

import { api, call, errorMessage } from "../../api/client";
import { Button } from "../../components/Button";
import { TextField } from "../../components/Field";
import { Alert, Card, PageHeader } from "../../components/Feedback";
import { Spinner } from "../../components/Spinner";
import { StatusBadge } from "../../components/StatusBadge";
import { JourneySummary } from "../booking/JourneySummary";

export function PnrPage() {
  const { pnr = "" } = useParams();
  const navigate = useNavigate();
  const [input, setInput] = useState(pnr);
  const [error, setError] = useState("");

  const status = useQuery({
    queryKey: ["pnr", pnr],
    queryFn: () => call(api.GET("/api/v1/pnr/{pnr}", { params: { path: { pnr } } })),
    enabled: /^\d{10}$/.test(pnr),
    retry: false,
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!/^\d{10}$/.test(input)) {
      setError("A PNR has 10 digits.");
      return;
    }
    setError("");
    navigate(`/pnr/${input}`);
  }

  return (
    <section className="space-y-6">
      <PageHeader title="PNR status" subtitle="Check a booking without logging in." />
      <Card>
        <form onSubmit={submit} noValidate className="flex flex-wrap items-start gap-3">
          <TextField
            label="PNR number"
            inputMode="numeric"
            maxLength={10}
            className="w-56"
            value={input}
            onChange={(e) => setInput(e.target.value.replace(/\D/g, ""))}
            error={error}
          />
          <Button type="submit" className="mt-6">
            Check status
          </Button>
        </form>
      </Card>

      {status.isFetching && <Spinner label="Checking PNR" />}
      {status.isError && <Alert tone="error">{errorMessage(status.error)}</Alert>}
      {status.data && (
        <Card>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-semibold">PNR {status.data.pnr}</h2>
            <div className="flex gap-2">
              <StatusBadge status={status.data.booking_status} />
              {status.data.chart_prepared && <StatusBadge status="CHART_PREPARED" />}
            </div>
          </div>
          <JourneySummary
            trainNumber={status.data.train_number}
            trainName={status.data.train_name}
            travelClass={status.data.travel_class}
            from={status.data.from_station}
            to={status.data.to_station}
            departureAt={status.data.departure_at}
            arrivalAt={status.data.arrival_at}
          />
          <table className="mt-4 w-full text-left text-sm">
            <thead className="text-xs text-slate-500 uppercase">
              <tr>
                <th className="py-2">#</th>
                <th className="py-2">Name</th>
                <th className="py-2">Booked as</th>
                <th className="py-2">Current status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {status.data.passengers.map((p) => (
                <tr key={p.seq_no}>
                  <td className="py-2">{p.seq_no}</td>
                  <td className="py-2">{p.name}</td>
                  <td className="py-2 font-mono text-xs">{p.booking_status ?? "-"}</td>
                  <td className="py-2">
                    <StatusBadge status={p.current_status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </section>
  );
}
