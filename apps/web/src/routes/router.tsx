import { createBrowserRouter, isRouteErrorResponse, Link, useRouteError } from "react-router";

import { Layout } from "../components/Layout";
import { AccountPage } from "../features/auth/AccountPage";
import { LoginPage } from "../features/auth/LoginPage";
import { RegisterPage } from "../features/auth/RegisterPage";
import { AdminLayout } from "../features/admin/AdminLayout";
import { ChartPage } from "../features/admin/ChartPage";
import { DashboardPage } from "../features/admin/DashboardPage";
import { JobsPage } from "../features/admin/JobsPage";
import { RunsPage } from "../features/admin/RunsPage";
import { StationsPage } from "../features/admin/StationsPage";
import { TrainEditPage } from "../features/admin/TrainEditPage";
import { TrainsPage } from "../features/admin/TrainsPage";
import { BookingDetailPage } from "../features/booking/BookingDetailPage";
import { BookPage } from "../features/booking/BookPage";
import { MyBookingsPage } from "../features/booking/MyBookingsPage";
import { PaymentPage } from "../features/booking/PaymentPage";
import { PnrPage } from "../features/pnr/PnrPage";
import { ResultsPage } from "../features/search/ResultsPage";
import { SearchPage } from "../features/search/SearchPage";
import { RequireAdmin, RequireAuth } from "../lib/auth";

function NotFound() {
  return (
    <section className="py-12 text-center">
      <h1 className="text-xl font-semibold">Page not found</h1>
      <Link to="/" className="mt-3 inline-block text-brand-700 underline">
        Go to search
      </Link>
    </section>
  );
}

function RouteError() {
  const error = useRouteError();
  if (isRouteErrorResponse(error) && error.status === 404) return <NotFound />;
  return (
    <section className="py-12 text-center">
      <h1 className="text-xl font-semibold">Something went wrong</h1>
      <p className="mt-2 text-slate-600">Please reload the page or try again later.</p>
    </section>
  );
}

export const router = createBrowserRouter([
  {
    element: <Layout />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: <SearchPage /> },
      { path: "trains", element: <ResultsPage /> },
      { path: "pnr", element: <PnrPage /> },
      { path: "pnr/:pnr", element: <PnrPage /> },
      { path: "login", element: <LoginPage /> },
      { path: "register", element: <RegisterPage /> },
      {
        element: <RequireAuth />,
        children: [
          { path: "book", element: <BookPage /> },
          { path: "bookings", element: <MyBookingsPage /> },
          { path: "bookings/:id", element: <BookingDetailPage /> },
          { path: "bookings/:id/pay", element: <PaymentPage /> },
          { path: "account", element: <AccountPage /> },
        ],
      },
      {
        path: "admin",
        element: <RequireAdmin />,
        children: [
          {
            element: <AdminLayout />,
            children: [
              { index: true, element: <DashboardPage /> },
              { path: "stations", element: <StationsPage /> },
              { path: "trains", element: <TrainsPage /> },
              { path: "trains/:number", element: <TrainEditPage /> },
              { path: "runs", element: <RunsPage /> },
              { path: "runs/:runId/chart", element: <ChartPage /> },
              { path: "jobs", element: <JobsPage /> },
            ],
          },
        ],
      },
      { path: "*", element: <NotFound /> },
    ],
  },
]);
