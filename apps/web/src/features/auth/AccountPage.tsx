import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { api, call, errorMessage } from "../../api/client";
import type { UserOut } from "../../api/types";
import { Button } from "../../components/Button";
import { TextField } from "../../components/Field";
import { Alert, Card, PageHeader } from "../../components/Feedback";
import { ME_KEY, useMe } from "../../lib/auth";

export function AccountPage() {
  const { data: user } = useMe();
  if (!user) return null;
  return (
    <section>
      <PageHeader title="Account" subtitle={user.email} />
      <div className="grid gap-6 md:grid-cols-2">
        <ProfileForm user={user} />
        <PasswordForm />
      </div>
    </section>
  );
}

function ProfileForm({ user }: { user: UserOut }) {
  const queryClient = useQueryClient();
  const [fullName, setFullName] = useState(user.full_name);
  const [mobile, setMobile] = useState(user.mobile);
  const save = useMutation({
    mutationFn: () =>
      call(api.PATCH("/api/v1/users/me", { body: { full_name: fullName, mobile } })),
    onSuccess: (updated) => queryClient.setQueryData(ME_KEY, updated),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    save.mutate();
  }

  return (
    <Card>
      <h2 className="mb-4 font-semibold">Profile</h2>
      <form onSubmit={submit} className="space-y-4">
        {save.isError && <Alert tone="error">{errorMessage(save.error)}</Alert>}
        {save.isSuccess && <Alert tone="success">Profile saved.</Alert>}
        <TextField
          label="Full name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
        <TextField
          label="Mobile number"
          inputMode="numeric"
          maxLength={10}
          value={mobile}
          onChange={(e) => setMobile(e.target.value)}
        />
        <Button type="submit" busy={save.isPending}>
          Save profile
        </Button>
      </form>
    </Card>
  );
}

function PasswordForm() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const change = useMutation({
    mutationFn: () =>
      call(
        api.POST("/api/v1/users/me/password", {
          body: { current_password: current, new_password: next },
        }),
      ),
    onSuccess: () => {
      setCurrent("");
      setNext("");
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    change.mutate();
  }

  return (
    <Card>
      <h2 className="mb-4 font-semibold">Change password</h2>
      <form onSubmit={submit} className="space-y-4">
        {change.isError && <Alert tone="error">{errorMessage(change.error)}</Alert>}
        {change.isSuccess && <Alert tone="success">Password changed.</Alert>}
        <TextField
          label="Current password"
          type="password"
          autoComplete="current-password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
        />
        <TextField
          label="New password"
          type="password"
          autoComplete="new-password"
          hint="At least 8 characters, with a letter and a digit."
          value={next}
          onChange={(e) => setNext(e.target.value)}
        />
        <Button type="submit" busy={change.isPending}>
          Change password
        </Button>
      </form>
    </Card>
  );
}
