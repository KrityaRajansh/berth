import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";

import { api, call, errorMessage } from "../../api/client";
import type { TrainOut } from "../../api/types";
import { Button } from "../../components/Button";
import { TextField } from "../../components/Field";
import { Alert, Card, PageHeader } from "../../components/Feedback";
import { Spinner } from "../../components/Spinner";
import { DAY_NAMES } from "../../lib/format";
import { DayPicker } from "./DayPicker";

export function describeDays(days: number[]): string {
  return days.length === 7 ? "Daily" : days.map((d) => DAY_NAMES[d]).join(", ");
}

function coachSummary(train: TrainOut): string {
  const counts = new Map<string, number>();
  for (const c of train.coaches) counts.set(c.travel_class, (counts.get(c.travel_class) ?? 0) + 1);
  return [...counts].map(([cls, n]) => `${n} x ${cls}`).join(", ") || "None";
}

export function TrainsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [number, setNumber] = useState("");
  const [name, setName] = useState("");
  const [days, setDays] = useState<number[]>([0, 1, 2, 3, 4, 5, 6]);

  const trains = useQuery({
    queryKey: ["admin", "trains"],
    queryFn: () => call(api.GET("/api/v1/admin/trains")),
  });

  const create = useMutation({
    mutationFn: () =>
      call(api.POST("/api/v1/admin/trains", { body: { number, name, running_days: days } })),
    onSuccess: (train) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "trains"] });
      navigate(`/admin/trains/${train.number}`);
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }

  return (
    <section className="space-y-6">
      <PageHeader title="Trains" />
      <Card>
        <h2 className="mb-3 font-semibold">Add a train</h2>
        <form
          onSubmit={submit}
          className="grid items-start gap-3 md:grid-cols-[8rem_1fr_auto_auto]"
        >
          <TextField
            label="Number"
            inputMode="numeric"
            maxLength={5}
            value={number}
            onChange={(e) => setNumber(e.target.value.replace(/\D/g, ""))}
          />
          <TextField label="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <DayPicker value={days} onChange={setDays} />
          <div className="md:pt-6">
            <Button type="submit" busy={create.isPending}>
              Add and edit route
            </Button>
          </div>
        </form>
        {create.isError && (
          <div className="mt-3">
            <Alert tone="error">{errorMessage(create.error)}</Alert>
          </div>
        )}
      </Card>

      {trains.isPending ? (
        <Spinner />
      ) : trains.isError ? (
        <Alert tone="error">{errorMessage(trains.error)}</Alert>
      ) : (
        <div className="overflow-x-auto rounded border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500 uppercase">
              <tr>
                <th className="px-4 py-2">Train</th>
                <th className="px-4 py-2">Route</th>
                <th className="px-4 py-2">Runs on</th>
                <th className="px-4 py-2">Coaches</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {trains.data.map((t) => (
                <tr key={t.id} className={t.is_active ? "" : "text-slate-400"}>
                  <td className="px-4 py-2">
                    <Link to={`/admin/trains/${t.number}`} className="text-brand-700 underline">
                      <span className="font-mono">{t.number}</span> {t.name}
                    </Link>
                  </td>
                  <td className="px-4 py-2 font-mono text-xs">
                    {t.stops.length
                      ? `${t.stops[0].station_code} - ${t.stops[t.stops.length - 1].station_code} (${t.stops.length} stops)`
                      : "No route"}
                  </td>
                  <td className="px-4 py-2">{describeDays(t.running_days)}</td>
                  <td className="px-4 py-2">{coachSummary(t)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
