import { Link, NavLink, Outlet } from "react-router";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded px-3 py-2 text-sm font-medium ${
    isActive ? "bg-brand-700 text-white" : "text-brand-50 hover:bg-brand-700/60"
  }`;

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="bg-brand-900">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="text-lg font-semibold tracking-tight text-white">
            Berth
          </Link>
          <nav aria-label="Main" className="flex gap-1">
            <NavLink to="/" end className={navLinkClass}>
              Search trains
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 py-4 text-center text-xs text-slate-500">
        Berth is a CSC702 course project. Payments are simulated.
      </footer>
    </div>
  );
}
