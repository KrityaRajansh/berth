import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate, Outlet, useLocation } from "react-router";

import { api, call } from "../api/client";
import type { UserOut } from "../api/types";
import { Spinner } from "../components/Spinner";

export const ME_KEY = ["me"] as const;

export function useMe() {
  return useQuery({
    queryKey: ME_KEY,
    queryFn: async (): Promise<UserOut | null> => {
      const { data, response } = await api.GET("/api/v1/auth/me");
      if (response.status === 401) return null;
      if (!response.ok || !data) throw new Error("Could not load your account.");
      return data;
    },
    staleTime: 5 * 60_000,
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => call(api.POST("/api/v1/auth/logout")),
    onSuccess: () => {
      queryClient.clear();
      queryClient.setQueryData(ME_KEY, null);
    },
  });
}

function useLoginRedirect() {
  const location = useLocation();
  return `/login?next=${encodeURIComponent(location.pathname + location.search)}`;
}

export function RequireAuth() {
  const { data: user, isPending } = useMe();
  const loginUrl = useLoginRedirect();
  if (isPending) return <Spinner label="Checking your session" />;
  if (!user) return <Navigate to={loginUrl} replace />;
  return <Outlet />;
}

export function RequireAdmin() {
  const { data: user, isPending } = useMe();
  const loginUrl = useLoginRedirect();
  if (isPending) return <Spinner label="Checking your session" />;
  if (!user) return <Navigate to={loginUrl} replace />;
  if (user.role !== "ADMIN") {
    return (
      <section className="py-12 text-center">
        <h1 className="text-xl font-semibold">Administrators only</h1>
        <p className="mt-2 text-slate-600">Your account does not have access to this area.</p>
      </section>
    );
  }
  return <Outlet />;
}
