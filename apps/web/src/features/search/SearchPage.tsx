import { Link } from "react-router";

import { Card } from "../../components/Feedback";
import { addDays, todayIst } from "../../lib/format";
import { SearchForm, searchUrl } from "./SearchForm";

const POPULAR_ROUTES = [
  { from: { code: "NDLS", name: "New Delhi" }, to: { code: "MMCT", name: "Mumbai Central" } },
  { from: { code: "NDLS", name: "New Delhi" }, to: { code: "HWH", name: "Howrah Jn" } },
  { from: { code: "NDLS", name: "New Delhi" }, to: { code: "BPL", name: "Bhopal Jn" } },
  {
    from: { code: "MAS", name: "MGR Chennai Central" },
    to: { code: "SBC", name: "KSR Bengaluru" },
  },
];

export function SearchPage() {
  const tomorrow = addDays(todayIst(), 1);
  return (
    <section aria-labelledby="search-heading" className="space-y-8">
      <div>
        <h1 id="search-heading" className="text-2xl font-semibold text-slate-900">
          Search trains
        </h1>
        <p className="mt-1 text-slate-600">
          Find trains between two stations and check berth availability by class.
        </p>
      </div>

      <Card>
        <SearchForm />
      </Card>

      <div>
        <h2 className="text-sm font-semibold tracking-wide text-slate-500 uppercase">
          Popular routes, tomorrow
        </h2>
        <ul className="mt-3 grid gap-2 sm:grid-cols-2">
          {POPULAR_ROUTES.map(({ from, to }) => (
            <li key={`${from.code}-${to.code}`}>
              <Link
                to={searchUrl({ from, to, date: tomorrow, cls: "" })}
                className="flex items-center justify-between rounded border border-slate-200 bg-white px-4 py-3 text-sm hover:border-brand-600"
              >
                <span>
                  {from.name} to {to.name}
                </span>
                <span className="font-mono text-xs text-slate-500">
                  {from.code} - {to.code}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
