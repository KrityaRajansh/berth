import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";

import { ApiError, api, call, errorMessage } from "../../api/client";
import { Button } from "../../components/Button";
import { TextField } from "../../components/Field";
import { Alert, Card } from "../../components/Feedback";
import { ME_KEY } from "../../lib/auth";
import { safeNext } from "./LoginPage";

type Form = { full_name: string; email: string; mobile: string; password: string; confirm: string };
type Errors = Partial<Record<keyof Form, string>>;

export function validateRegistration(form: Form): Errors {
  const errors: Errors = {};
  if (form.full_name.trim().length < 2) errors.full_name = "Enter your full name.";
  if (!/^\S+@\S+\.\S+$/.test(form.email)) errors.email = "Enter a valid e-mail address.";
  if (!/^[6-9]\d{9}$/.test(form.mobile)) errors.mobile = "Enter a 10-digit mobile number.";
  if (form.password.length < 8 || !/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)) {
    errors.password = "At least 8 characters, with a letter and a digit.";
  }
  if (form.confirm !== form.password) errors.confirm = "Passwords do not match.";
  return errors;
}

export function RegisterPage() {
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<Form>({
    full_name: "",
    email: "",
    mobile: "",
    password: "",
    confirm: "",
  });
  const [errors, setErrors] = useState<Errors>({});

  const register = useMutation({
    mutationFn: () =>
      call(
        api.POST("/api/v1/auth/register", {
          body: {
            full_name: form.full_name,
            email: form.email,
            mobile: form.mobile,
            password: form.password,
          },
        }),
      ),
    onSuccess: (user) => {
      queryClient.setQueryData(ME_KEY, user);
      navigate(next, { replace: true });
    },
    onError: (error) => {
      if (error instanceof ApiError) {
        setErrors(Object.fromEntries(error.details.map((d) => [d.field, d.message])));
      }
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    const found = validateRegistration(form);
    setErrors(found);
    if (Object.keys(found).length === 0) register.mutate();
  }

  const field = (key: keyof Form) => ({
    value: form[key],
    error: errors[key],
    onChange: (e: { target: { value: string } }) =>
      setForm((f) => ({ ...f, [key]: e.target.value })),
  });

  return (
    <section className="mx-auto max-w-md space-y-6">
      <h1 className="text-2xl font-semibold">Create an account</h1>
      <Card>
        <form onSubmit={submit} noValidate className="space-y-4">
          {register.isError && <Alert tone="error">{errorMessage(register.error)}</Alert>}
          <TextField label="Full name" autoComplete="name" {...field("full_name")} />
          <TextField label="E-mail" type="email" autoComplete="email" {...field("email")} />
          <TextField
            label="Mobile number"
            inputMode="numeric"
            autoComplete="tel-national"
            maxLength={10}
            {...field("mobile")}
          />
          <TextField
            label="Password"
            type="password"
            autoComplete="new-password"
            hint="At least 8 characters, with a letter and a digit."
            {...field("password")}
          />
          <TextField
            label="Confirm password"
            type="password"
            autoComplete="new-password"
            {...field("confirm")}
          />
          <Button type="submit" busy={register.isPending} className="w-full">
            Create account
          </Button>
        </form>
      </Card>
      <p className="text-center text-sm text-slate-600">
        Already registered?{" "}
        <Link to={`/login?next=${encodeURIComponent(next)}`} className="text-brand-700 underline">
          Log in
        </Link>
      </p>
    </section>
  );
}
