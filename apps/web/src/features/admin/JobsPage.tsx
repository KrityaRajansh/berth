import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, call, errorMessage } from "../../api/client";
import { Button } from "../../components/Button";
import { Alert, Card, PageHeader } from "../../components/Feedback";
import { Spinner } from "../../components/Spinner";
import { StatusBadge } from "../../components/StatusBadge";
import { formatDateTime } from "../../lib/format";

const JOBS = [
  { name: "run-generation", description: "Open bookings for the next 60 days." },
  {
    name: "chart-preparation",
    description: "Close bookings and settle the waitlist for runs past their cut-off.",
  },
  { name: "journey-completion", description: "Mark finished journeys as completed." },
  { name: "payment-expiry", description: "Expire bookings not paid within 15 minutes." },
];

export function JobsPage() {
  const queryClient = useQueryClient();
  const history = useQuery({
    queryKey: ["admin", "jobs"],
    queryFn: () => call(api.GET("/api/v1/admin/jobs")),
  });
  const run = useMutation({
    mutationFn: (name: string) =>
      call(api.POST("/api/v1/admin/jobs/{name}/run", { params: { path: { name } } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin"] }),
  });

  return (
    <section className="space-y-6">
      <PageHeader
        title="Scheduled jobs"
        subtitle="These run automatically every day. Run one now to apply it immediately."
      />
      {run.isError && <Alert tone="error">{errorMessage(run.error)}</Alert>}
      {run.isSuccess && (
        <Alert tone={run.data.status === "SUCCEEDED" ? "success" : "error"}>
          {run.data.job_name}: {run.data.status.toLowerCase()}, {run.data.items_processed}{" "}
          processed.
          {run.data.detail && ` ${run.data.detail}`}
        </Alert>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        {JOBS.map((job) => (
          <Card key={job.name} className="flex flex-col justify-between gap-3">
            <div>
              <h2 className="font-mono text-sm font-semibold">{job.name}</h2>
              <p className="mt-1 text-sm text-slate-600">{job.description}</p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              busy={run.isPending && run.variables === job.name}
              disabled={run.isPending}
              onClick={() => run.mutate(job.name)}
            >
              Run now
            </Button>
          </Card>
        ))}
      </div>

      <div>
        <h2 className="mb-3 font-semibold">History</h2>
        {history.isPending ? (
          <Spinner />
        ) : history.isError ? (
          <Alert tone="error">{errorMessage(history.error)}</Alert>
        ) : (
          <div className="overflow-x-auto rounded border border-slate-200 bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500 uppercase">
                <tr>
                  <th className="px-3 py-2">Job</th>
                  <th className="px-3 py-2">Started</th>
                  <th className="px-3 py-2">Trigger</th>
                  <th className="px-3 py-2">Processed</th>
                  <th className="px-3 py-2">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {history.data.map((job) => (
                  <tr key={job.id}>
                    <td className="px-3 py-2 font-mono">{job.job_name}</td>
                    <td className="px-3 py-2">{formatDateTime(job.started_at)}</td>
                    <td className="px-3 py-2">{job.triggered_by}</td>
                    <td className="px-3 py-2">{job.items_processed}</td>
                    <td className="px-3 py-2">
                      <StatusBadge status={job.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
