import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api, call, errorMessage } from "../../api/client";
import { TextField } from "../../components/Field";
import { Alert, PageHeader } from "../../components/Feedback";
import { Spinner } from "../../components/Spinner";
import { StatusBadge } from "../../components/StatusBadge";
import { addDays, formatDateTime, formatInr, todayIst } from "../../lib/format";

export function DashboardPage() {
  const today = todayIst();
  const [start, setStart] = useState(addDays(today, -29));
  const [end, setEnd] = useState(today);

  const stats = useQuery({
    queryKey: ["admin", "stats", start, end],
    queryFn: () => call(api.GET("/api/v1/admin/stats", { params: { query: { start, end } } })),
    enabled: Boolean(start && end && start <= end),
  });
  const jobs = useQuery({
    queryKey: ["admin", "jobs"],
    queryFn: () => call(api.GET("/api/v1/admin/jobs")),
  });

  return (
    <section className="space-y-6">
      <PageHeader
        title="Dashboard"
        subtitle="Bookings made in the selected period."
        actions={
          <div className="flex gap-3">
            <TextField
              label="From"
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
            <TextField
              label="To"
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </div>
        }
      />
      {stats.isError && <Alert tone="error">{errorMessage(stats.error)}</Alert>}
      {stats.isPending ? (
        <Spinner />
      ) : (
        stats.data && (
          <dl className="grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <Tile label="Bookings" value={String(stats.data.bookings)} />
            <Tile label="Passengers" value={String(stats.data.passengers)} />
            <Tile label="Passengers cancelled" value={String(stats.data.cancellations)} />
            <Tile label="Payments received" value={formatInr(stats.data.revenue_paise)} />
            <Tile label="Refunds issued" value={formatInr(stats.data.refunds_paise)} />
          </dl>
        )
      )}

      <div>
        <h2 className="mb-3 font-semibold">Recent job runs</h2>
        {jobs.data && jobs.data.length === 0 && (
          <p className="text-sm text-slate-600">No jobs have run yet.</p>
        )}
        <ul className="divide-y divide-slate-100 rounded border border-slate-200 bg-white text-sm">
          {jobs.data?.slice(0, 6).map((job) => (
            <li
              key={job.id}
              className="flex flex-wrap items-center justify-between gap-2 px-4 py-2"
            >
              <span className="font-mono">{job.job_name}</span>
              <span className="text-slate-500">
                {formatDateTime(job.started_at)} · {job.items_processed} processed ·{" "}
                {job.triggered_by}
              </span>
              <StatusBadge status={job.status} />
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-slate-200 bg-white px-4 py-3">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-1 text-xl font-semibold tabular-nums">{value}</dd>
    </div>
  );
}
