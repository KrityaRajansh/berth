import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";

import { api, call, errorMessage } from "../../api/client";
import { Button } from "../../components/Button";
import { TextField } from "../../components/Field";
import { Alert, Card } from "../../components/Feedback";
import { ME_KEY } from "../../lib/auth";

export function safeNext(next: string | null): string {
  // Only allow same-site paths, never an absolute URL to another site.
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}

export function LoginPage() {
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const login = useMutation({
    mutationFn: () => call(api.POST("/api/v1/auth/login", { body: { email, password } })),
    onSuccess: (user) => {
      queryClient.setQueryData(ME_KEY, user);
      navigate(next, { replace: true });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    login.mutate();
  }

  return (
    <section className="mx-auto max-w-md space-y-6">
      <h1 className="text-2xl font-semibold">Log in</h1>
      <Card>
        <form onSubmit={submit} className="space-y-4">
          {login.isError && <Alert tone="error">{errorMessage(login.error)}</Alert>}
          <TextField
            label="E-mail"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <TextField
            label="Password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button type="submit" busy={login.isPending} className="w-full">
            Log in
          </Button>
        </form>
      </Card>
      <p className="text-center text-sm text-slate-600">
        New to Berth?{" "}
        <Link
          to={`/register?next=${encodeURIComponent(next)}`}
          className="text-brand-700 underline"
        >
          Create an account
        </Link>
      </p>
    </section>
  );
}
