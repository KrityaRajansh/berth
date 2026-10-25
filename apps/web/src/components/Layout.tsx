import { Link, NavLink, Outlet, useNavigate } from "react-router";

import { useLogout, useMe } from "../lib/auth";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded px-3 py-2 text-sm font-medium ${
    isActive ? "bg-brand-700 text-white" : "text-brand-50 hover:bg-brand-700/60"
  }`;

export function Layout() {
  const { data: user } = useMe();
  const logout = useLogout();
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2"
      >
        Skip to content
      </a>
      <header className="bg-brand-900">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3">
          <Link to="/" className="text-lg font-semibold tracking-tight text-white">
            Berth
          </Link>
          <nav
            aria-label="Main"
            className="order-3 flex w-full flex-wrap gap-1 sm:order-2 sm:w-auto"
          >
            <NavLink to="/" end className={navLinkClass}>
              Search trains
            </NavLink>
            <NavLink to="/pnr" className={navLinkClass}>
              PNR status
            </NavLink>
            {user && (
              <NavLink to="/bookings" className={navLinkClass}>
                My bookings
              </NavLink>
            )}
            {user?.role === "ADMIN" && (
              <NavLink to="/admin" className={navLinkClass}>
                Admin
              </NavLink>
            )}
          </nav>
          <div className="order-2 flex items-center gap-2 text-sm sm:order-3">
            {user ? (
              <>
                <NavLink to="/account" className={navLinkClass}>
                  {user.full_name.split(" ")[0]}
                </NavLink>
                <button
                  type="button"
                  className="rounded px-3 py-2 font-medium text-brand-50 hover:bg-brand-700/60"
                  onClick={() => logout.mutate(undefined, { onSuccess: () => navigate("/") })}
                >
                  Log out
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login" className={navLinkClass}>
                  Log in
                </NavLink>
                <Link
                  to="/register"
                  className="rounded bg-white px-3 py-2 font-medium text-brand-900 hover:bg-brand-50"
                >
                  Register
                </Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 py-4 text-center text-xs text-slate-500">
        Berth is a CSC702 course project. Train data is fictional and payments are simulated.
      </footer>
    </div>
  );
}
