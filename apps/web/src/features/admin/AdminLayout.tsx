import { NavLink, Outlet } from "react-router";

const LINKS = [
  { to: "/admin", label: "Dashboard", end: true },
  { to: "/admin/stations", label: "Stations" },
  { to: "/admin/trains", label: "Trains" },
  { to: "/admin/runs", label: "Train runs" },
  { to: "/admin/jobs", label: "Jobs" },
];

export function AdminLayout() {
  return (
    <div className="space-y-6">
      <nav aria-label="Administration" className="flex flex-wrap gap-1 border-b border-slate-200">
        {LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className={({ isActive }) =>
              `-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
                isActive
                  ? "border-brand-600 text-brand-700"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              }`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}
