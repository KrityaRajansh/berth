import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";

import { api, call, errorMessage } from "../../api/client";
import { Alert, EmptyState, PageHeader } from "../../components/Feedback";
import { Spinner } from "../../components/Spinner";
import { StatusBadge } from "../../components/StatusBadge";

export function ChartPage() {
  const { runId = "" } = useParams();
  const chart = useQuery({
    queryKey: ["admin", "chart", runId],
    queryFn: () =>
      call(
        api.GET("/api/v1/admin/runs/{run_id}/chart", {
          params: { path: { run_id: Number(runId) } },
        }),
      ),
  });

  return (
    <section className="space-y-4">
      <PageHeader
        title="Passenger chart"
        subtitle={
          <Link to="/admin/runs" className="text-brand-700 underline">
            Back to train runs
          </Link>
        }
      />
      {chart.isPending ? (
        <Spinner />
      ) : chart.isError ? (
        <Alert tone="error">{errorMessage(chart.error)}</Alert>
      ) : chart.data.length === 0 ? (
        <EmptyState title="No passengers on this run yet" />
      ) : (
        <div className="overflow-x-auto rounded border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500 uppercase">
              <tr>
                <th className="px-3 py-2">Class</th>
                <th className="px-3 py-2">Coach / berth</th>
                <th className="px-3 py-2">Passenger</th>
                <th className="px-3 py-2">From - to</th>
                <th className="px-3 py-2">PNR</th>
                <th className="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {chart.data.map((row, i) => (
                <tr key={`${row.pnr}-${i}`}>
                  <td className="px-3 py-2">{row.travel_class}</td>
                  <td className="px-3 py-2 font-mono">
                    {row.coach_code ? `${row.coach_code}/${row.berth_no} ${row.berth_type}` : "-"}
                  </td>
                  <td className="px-3 py-2">
                    {row.passenger} ({row.age} {row.gender})
                  </td>
                  <td className="px-3 py-2 font-mono">
                    {row.from_code} - {row.to_code}
                  </td>
                  <td className="px-3 py-2 font-mono">{row.pnr}</td>
                  <td className="px-3 py-2">
                    <StatusBadge status={row.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
