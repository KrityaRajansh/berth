import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router";

import { api, call, errorMessage } from "../../api/client";
import type { CoachIn, RouteStopIn, TrainOut, TravelClass } from "../../api/types";
import { Button } from "../../components/Button";
import { SelectField, TextField, controlClass } from "../../components/Field";
import { Alert, Card, PageHeader } from "../../components/Feedback";
import { Spinner } from "../../components/Spinner";
import { CLASS_NAMES } from "../../lib/format";
import { DayPicker } from "./DayPicker";

export function TrainEditPage() {
  const { number = "" } = useParams();
  const train = useQuery({
    queryKey: ["admin", "train", number],
    queryFn: () => call(api.GET("/api/v1/admin/trains/{number}", { params: { path: { number } } })),
  });

  if (train.isPending) return <Spinner />;
  if (train.isError) return <Alert tone="error">{errorMessage(train.error)}</Alert>;
  return (
    <section className="space-y-6">
      <PageHeader
        title={`${train.data.number} ${train.data.name}`}
        subtitle="Train details, route and coaches"
      />
      <DetailsForm key={`d-${train.data.number}`} train={train.data} />
      <RouteEditor key={`r-${train.data.number}`} train={train.data} />
      <CoachEditor key={`c-${train.data.number}`} train={train.data} />
    </section>
  );
}

function useSaveTrain(number: string) {
  const queryClient = useQueryClient();
  return (data: TrainOut) => {
    queryClient.setQueryData(["admin", "train", data.number], data);
    queryClient.invalidateQueries({ queryKey: ["admin", "trains"] });
    return data.number !== number;
  };
}

function DetailsForm({ train }: { train: TrainOut }) {
  const navigate = useNavigate();
  const onSaved = useSaveTrain(train.number);
  const [name, setName] = useState(train.name);
  const [days, setDays] = useState(train.running_days);
  const [active, setActive] = useState(train.is_active);
  const save = useMutation({
    mutationFn: () =>
      call(
        api.PUT("/api/v1/admin/trains/{number}", {
          params: { path: { number: train.number } },
          body: { number: train.number, name, running_days: days, is_active: active },
        }),
      ),
    onSuccess: (data) => onSaved(data) && navigate(`/admin/trains/${data.number}`),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    save.mutate();
  }

  return (
    <Card>
      <h2 className="mb-3 font-semibold">Details</h2>
      <form onSubmit={submit} className="grid items-start gap-3 md:grid-cols-[1fr_auto_auto_auto]">
        <TextField label="Name" value={name} onChange={(e) => setName(e.target.value)} />
        <DayPicker value={days} onChange={setDays} />
        <label className="flex items-center gap-2 text-sm md:pt-8">
          <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
          Active
        </label>
        <div className="md:pt-6">
          <Button type="submit" busy={save.isPending}>
            Save details
          </Button>
        </div>
      </form>
      <Feedback mutation={save} success="Details saved." />
    </Card>
  );
}

type StopDraft = {
  station_code: string;
  arrival: string;
  departure: string;
  day_offset: string;
  distance_km: string;
};

function toDraft(train: TrainOut): StopDraft[] {
  return train.stops.map((s) => ({
    station_code: s.station_code,
    arrival: s.arrival?.slice(0, 5) ?? "",
    departure: s.departure?.slice(0, 5) ?? "",
    day_offset: String(s.day_offset),
    distance_km: String(s.distance_km),
  }));
}

const blankStop = (): StopDraft => ({
  station_code: "",
  arrival: "",
  departure: "",
  day_offset: "0",
  distance_km: "",
});

function RouteEditor({ train }: { train: TrainOut }) {
  const onSaved = useSaveTrain(train.number);
  const [stops, setStops] = useState<StopDraft[]>(() =>
    train.stops.length ? toDraft(train) : [blankStop(), blankStop()],
  );

  const save = useMutation({
    mutationFn: () =>
      call(
        api.PUT("/api/v1/admin/trains/{number}/route", {
          params: { path: { number: train.number } },
          body: stops.map((s): RouteStopIn => ({
            station_code: s.station_code.trim().toUpperCase(),
            arrival: s.arrival || null,
            departure: s.departure || null,
            day_offset: Number(s.day_offset) || 0,
            distance_km: Number(s.distance_km) || 0,
          })),
        }),
      ),
    onSuccess: (data) => {
      onSaved(data);
      setStops(toDraft(data));
    },
  });

  function update(i: number, patch: Partial<StopDraft>) {
    setStops((all) => all.map((s, j) => (j === i ? { ...s, ...patch } : s)));
  }

  function move(i: number, delta: number) {
    setStops((all) => {
      const next = [...all];
      [next[i], next[i + delta]] = [next[i + delta], next[i]];
      return next;
    });
  }

  const cell = `${controlClass} px-2 py-1`;
  return (
    <Card>
      <h2 className="mb-1 font-semibold">Route</h2>
      <p className="mb-3 text-xs text-slate-500">
        Day is the number of days after the train leaves its first station. The route cannot change
        once tickets have been booked on this train.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[40rem] text-left text-sm">
          <thead className="text-xs text-slate-500 uppercase">
            <tr>
              <th className="py-1 pr-2">#</th>
              <th className="py-1 pr-2">Station code</th>
              <th className="py-1 pr-2">Arrives</th>
              <th className="py-1 pr-2">Departs</th>
              <th className="py-1 pr-2">Day</th>
              <th className="py-1 pr-2">Km</th>
              <th className="py-1" />
            </tr>
          </thead>
          <tbody>
            {stops.map((s, i) => (
              <tr key={i}>
                <td className="py-1 pr-2 text-slate-500">{i + 1}</td>
                <td className="py-1 pr-2">
                  <input
                    aria-label={`Stop ${i + 1} station code`}
                    className={cell}
                    value={s.station_code}
                    onChange={(e) => update(i, { station_code: e.target.value.toUpperCase() })}
                  />
                </td>
                <td className="py-1 pr-2">
                  <input
                    aria-label={`Stop ${i + 1} arrival`}
                    type="time"
                    className={cell}
                    value={s.arrival}
                    disabled={i === 0}
                    onChange={(e) => update(i, { arrival: e.target.value })}
                  />
                </td>
                <td className="py-1 pr-2">
                  <input
                    aria-label={`Stop ${i + 1} departure`}
                    type="time"
                    className={cell}
                    value={s.departure}
                    disabled={i === stops.length - 1}
                    onChange={(e) => update(i, { departure: e.target.value })}
                  />
                </td>
                <td className="py-1 pr-2">
                  <input
                    aria-label={`Stop ${i + 1} day`}
                    inputMode="numeric"
                    className={`${cell} w-14`}
                    value={s.day_offset}
                    onChange={(e) => update(i, { day_offset: e.target.value.replace(/\D/g, "") })}
                  />
                </td>
                <td className="py-1 pr-2">
                  <input
                    aria-label={`Stop ${i + 1} distance`}
                    inputMode="numeric"
                    className={`${cell} w-20`}
                    value={s.distance_km}
                    onChange={(e) => update(i, { distance_km: e.target.value.replace(/\D/g, "") })}
                  />
                </td>
                <td className="py-1 whitespace-nowrap">
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={i === 0}
                    onClick={() => move(i, -1)}
                    aria-label={`Move stop ${i + 1} up`}
                  >
                    Up
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={i === stops.length - 1}
                    onClick={() => move(i, 1)}
                    aria-label={`Move stop ${i + 1} down`}
                  >
                    Down
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={stops.length <= 2}
                    onClick={() => setStops((all) => all.filter((_, j) => j !== i))}
                    aria-label={`Remove stop ${i + 1}`}
                  >
                    Remove
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setStops((all) => [...all, blankStop()])}
        >
          Add stop
        </Button>
        <Button size="sm" busy={save.isPending} onClick={() => save.mutate()}>
          Save route
        </Button>
      </div>
      <Feedback mutation={save} success="Route saved." />
    </Card>
  );
}

const CLASS_OPTIONS = Object.entries(CLASS_NAMES).map(([value, name]) => ({
  value,
  label: `${value} ${name}`,
}));

function CoachEditor({ train }: { train: TrainOut }) {
  const onSaved = useSaveTrain(train.number);
  const [coaches, setCoaches] = useState<CoachIn[]>(train.coaches);
  const save = useMutation({
    mutationFn: () =>
      call(
        api.PUT("/api/v1/admin/trains/{number}/coaches", {
          params: { path: { number: train.number } },
          body: coaches,
        }),
      ),
    onSuccess: (data) => {
      onSaved(data);
      setCoaches(data.coaches);
    },
  });

  function update(i: number, patch: Partial<CoachIn>) {
    setCoaches((all) => all.map((c, j) => (j === i ? { ...c, ...patch } : c)));
  }

  return (
    <Card>
      <h2 className="mb-1 font-semibold">Coaches</h2>
      <p className="mb-3 text-xs text-slate-500">
        Changes apply to train runs generated after saving. Existing runs keep their coaches.
      </p>
      <ul className="space-y-2">
        {coaches.map((c, i) => (
          <li key={i} className="grid items-end gap-2 sm:grid-cols-[6rem_1fr_7rem_auto]">
            <TextField
              label="Code"
              value={c.code}
              maxLength={4}
              onChange={(e) => update(i, { code: e.target.value.toUpperCase() })}
            />
            <SelectField
              label="Class"
              value={c.travel_class}
              options={CLASS_OPTIONS}
              onChange={(e) => update(i, { travel_class: e.target.value as TravelClass })}
            />
            <TextField
              label="Berths"
              inputMode="numeric"
              value={String(c.berth_count)}
              onChange={(e) =>
                update(i, { berth_count: Number(e.target.value.replace(/\D/g, "")) || 0 })
              }
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setCoaches((all) => all.filter((_, j) => j !== i))}
            >
              Remove
            </Button>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={() =>
            setCoaches((all) => [...all, { code: "", travel_class: "SL", berth_count: 72 }])
          }
        >
          Add coach
        </Button>
        <Button size="sm" busy={save.isPending} onClick={() => save.mutate()}>
          Save coaches
        </Button>
      </div>
      <Feedback mutation={save} success="Coaches saved." />
    </Card>
  );
}

function Feedback({
  mutation,
  success,
}: {
  mutation: { isError: boolean; isSuccess: boolean; error: unknown };
  success: string;
}) {
  if (mutation.isError)
    return (
      <div className="mt-3">
        <Alert tone="error">{errorMessage(mutation.error)}</Alert>
      </div>
    );
  if (mutation.isSuccess)
    return (
      <div className="mt-3">
        <Alert tone="success">{success}</Alert>
      </div>
    );
  return null;
}
