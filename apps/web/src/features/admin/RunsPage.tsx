import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link } from "react-router";

import { api, call, errorMessage } from "../../api/client";
import type { RunOut } from "../../api/types";
import { Button } from "../../components/Button";
import { TextField } from "../../components/Field";
import { Alert, Card, EmptyState, PageHeader } from "../../components/Feedback";
import { Spinner } from "../../components/Spinner";
import { StatusBadge } from "../../components/StatusBadge";
import { addDays, formatDate, todayIst } from "../../lib/format";

export function RunsPage() {
  const today = todayIst();
  const [date, setDate] = useState(addDays(today, 1));
  const [train, setTrain] = useState("");

  const runs = useQuery({
    queryKey: ["admin", "runs", date, train],
    queryFn: () =>
      call(
        api.GET("/api/v1/admin/runs", {
          params: { query: { date: date || undefined, train: train || undefined } },
        }),
      ),
  });

  return (
    <section className="space-y-6">
      <PageHeader title="Train runs" />
      <GenerateForm />
      <Card>
        <div className="mb-4 flex flex-wrap gap-3">
          <TextField
            label="Run date"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
          <TextField
            label="Train number"
            inputMode="numeric"
            maxLength={5}
            value={train}
            onChange={(e) => setTrain(e.target.value.replace(/\D/g, ""))}
          />
        </div>
        {runs.isPending ? (
          <Spinner />
        ) : runs.isError ? (
          <Alert tone="error">{errorMessage(runs.error)}</Alert>
        ) : runs.data.length === 0 ? (
          <EmptyState title="No runs match these filters" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-slate-500 uppercase">
                <tr>
                  <th className="py-2 pr-3">Date</th>
                  <th className="py-2 pr-3">Train</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Confirmed / berths, waitlist</th>
                  <th className="py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {runs.data.map((run) => (
                  <RunRow key={run.id} run={run} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </section>
  );
}

function RunRow({ run }: { run: RunOut }) {
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const cancel = useMutation({
    mutationFn: () =>
      call(
        api.POST("/api/v1/admin/runs/{run_id}/cancel", { params: { path: { run_id: run.id } } }),
      ),
    onSuccess: () => {
      setConfirming(false);
      queryClient.invalidateQueries({ queryKey: ["admin", "runs"] });
    },
  });
  const cancellable = run.status === "SCHEDULED" || run.status === "CHART_PREPARED";

  return (
    <tr className="align-top">
      <td className="py-2 pr-3 whitespace-nowrap">{formatDate(run.run_date)}</td>
      <td className="py-2 pr-3">
        <span className="font-mono">{run.train_number}</span> {run.train_name}
      </td>
      <td className="py-2 pr-3">
        <StatusBadge status={run.status} />
      </td>
      <td className="py-2 pr-3 font-mono text-xs">
        {run.classes.map((c) => (
          <div key={c.travel_class}>
            {c.travel_class}: {c.confirmed}/{c.berth_capacity}
            {c.waitlisted ? `, WL ${c.waitlisted}` : ""}
          </div>
        ))}
      </td>
      <td className="py-2 text-right whitespace-nowrap">
        <Link to={`/admin/runs/${run.id}/chart`} className="mr-2 text-sm text-brand-700 underline">
          Chart
        </Link>
        {cancellable &&
          (confirming ? (
            <span className="inline-flex gap-1">
              <Button
                variant="danger"
                size="sm"
                busy={cancel.isPending}
                onClick={() => cancel.mutate()}
              >
                Cancel run and refund all
              </Button>
              <Button variant="secondary" size="sm" onClick={() => setConfirming(false)}>
                Keep
              </Button>
            </span>
          ) : (
            <Button variant="ghost" size="sm" onClick={() => setConfirming(true)}>
              Cancel run
            </Button>
          ))}
        {cancel.isError && (
          <p className="mt-1 text-xs text-red-700">{errorMessage(cancel.error)}</p>
        )}
      </td>
    </tr>
  );
}

function GenerateForm() {
  const queryClient = useQueryClient();
  const today = todayIst();
  const [start, setStart] = useState(today);
  const [end, setEnd] = useState(addDays(today, 60));
  const [train, setTrain] = useState("");
  const generate = useMutation({
    mutationFn: () =>
      call(
        api.POST("/api/v1/admin/runs/generate", {
          body: { start, end, train_number: train || null },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "runs"] }),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    generate.mutate();
  }

  return (
    <Card>
      <h2 className="mb-1 font-semibold">Open bookings</h2>
      <p className="mb-3 text-xs text-slate-500">
        Creates runs for every running day in the range. The nightly job does this automatically for
        the next 60 days.
      </p>
      <form onSubmit={submit} className="flex flex-wrap items-start gap-3">
        <TextField
          label="From"
          type="date"
          value={start}
          onChange={(e) => setStart(e.target.value)}
        />
        <TextField label="To" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        <TextField
          label="Train (optional)"
          inputMode="numeric"
          maxLength={5}
          value={train}
          onChange={(e) => setTrain(e.target.value.replace(/\D/g, ""))}
        />
        <Button type="submit" className="mt-6" busy={generate.isPending}>
          Generate runs
        </Button>
      </form>
      {generate.isSuccess && (
        <div className="mt-3">
          <Alert tone="success">{generate.data.created} new runs created.</Alert>
        </div>
      )}
      {generate.isError && (
        <div className="mt-3">
          <Alert tone="error">{errorMessage(generate.error)}</Alert>
        </div>
      )}
    </Card>
  );
}
