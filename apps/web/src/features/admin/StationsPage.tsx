import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { api, call, errorMessage } from "../../api/client";
import type { StationIn, StationOut } from "../../api/types";
import { Button } from "../../components/Button";
import { TextField } from "../../components/Field";
import { Alert, Card, PageHeader } from "../../components/Feedback";
import { Spinner } from "../../components/Spinner";

const EMPTY: StationIn = { code: "", name: "", city: "", is_active: true };

export function StationsPage() {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<StationOut | null>(null);
  const [form, setForm] = useState<StationIn>(EMPTY);

  const stations = useQuery({
    queryKey: ["admin", "stations"],
    queryFn: () => call(api.GET("/api/v1/admin/stations")),
  });

  const save = useMutation({
    mutationFn: () =>
      editing
        ? call(
            api.PUT("/api/v1/admin/stations/{station_id}", {
              params: { path: { station_id: editing.id } },
              body: form,
            }),
          )
        : call(api.POST("/api/v1/admin/stations", { body: form })),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "stations"] });
      setEditing(null);
      setForm(EMPTY);
    },
  });

  function edit(station: StationOut) {
    setEditing(station);
    setForm({
      code: station.code,
      name: station.name,
      city: station.city,
      is_active: station.is_active,
    });
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    save.mutate();
  }

  return (
    <section className="space-y-6">
      <PageHeader title="Stations" />
      <Card>
        <h2 className="mb-3 font-semibold">{editing ? `Edit ${editing.code}` : "Add a station"}</h2>
        <form
          onSubmit={submit}
          className="grid items-start gap-3 sm:grid-cols-[8rem_1fr_1fr_auto_auto]"
        >
          <TextField
            label="Code"
            value={form.code}
            maxLength={8}
            onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
          />
          <TextField
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <TextField
            label="City"
            value={form.city}
            onChange={(e) => setForm({ ...form, city: e.target.value })}
          />
          <label className="flex items-center gap-2 text-sm sm:pt-8">
            <input
              type="checkbox"
              checked={form.is_active ?? true}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            Active
          </label>
          <div className="flex gap-2 sm:pt-6">
            <Button type="submit" busy={save.isPending}>
              {editing ? "Save" : "Add"}
            </Button>
            {editing && (
              <Button variant="secondary" onClick={() => (setEditing(null), setForm(EMPTY))}>
                Cancel
              </Button>
            )}
          </div>
        </form>
        {save.isError && (
          <div className="mt-3">
            <Alert tone="error">{errorMessage(save.error)}</Alert>
          </div>
        )}
      </Card>

      {stations.isPending ? (
        <Spinner />
      ) : stations.isError ? (
        <Alert tone="error">{errorMessage(stations.error)}</Alert>
      ) : (
        <div className="overflow-x-auto rounded border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500 uppercase">
              <tr>
                <th className="px-4 py-2">Code</th>
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">City</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {stations.data.map((s) => (
                <tr key={s.id}>
                  <td className="px-4 py-2 font-mono">{s.code}</td>
                  <td className="px-4 py-2">{s.name}</td>
                  <td className="px-4 py-2">{s.city}</td>
                  <td className="px-4 py-2">{s.is_active ? "Active" : "Inactive"}</td>
                  <td className="px-4 py-2 text-right">
                    <Button variant="ghost" size="sm" onClick={() => edit(s)}>
                      Edit
                    </Button>
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
