"use client";

// Login page: minimal centered form. On success the JWT is stored by
// lib/auth and the user is redirected to "/" or the ?next= path.

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

// Reads ?next= from the URL without useSearchParams (avoids the Suspense
// boundary requirement); only same-origin paths are accepted.
function safeNextPath(): string {
  if (typeof window === "undefined") return "/";
  const next = new URLSearchParams(window.location.search).get("next");
  if (next !== null && next.startsWith("/") && !next.startsWith("//")) {
    return next;
  }
  return "/";
}

const INPUT_CLASS =
  "mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm text-ink focus:border-brand focus:outline-none";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nextParam, setNextParam] = useState<string | null>(null);

  useEffect(() => {
    const next = safeNextPath();
    setNextParam(next === "/" ? null : next);
  }, []);

  const registerHref =
    nextParam !== null
      ? `/register?next=${encodeURIComponent(nextParam)}`
      : "/register";

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      router.replace(safeNextPath());
    } catch (err: unknown) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Could not log in. Try again.",
      );
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col px-8 py-8">
      <div className="flex flex-1 items-center justify-center">
        <Card className="w-full max-w-sm">
          <h1 className="text-lg font-semibold text-ink">Log in</h1>
          <p className="mt-1 text-sm text-slate-500">
            Required only for saving deals. Analysis pages are public.
          </p>

          <form onSubmit={onSubmit} className="mt-5 space-y-4" noValidate>
            <label className="block text-sm font-medium text-slate-700">
              Email
              <input
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={INPUT_CLASS}
              />
            </label>
            <label className="block text-sm font-medium text-slate-700">
              Password
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={INPUT_CLASS}
              />
            </label>

            {error !== null && (
              <p className="text-sm text-negative" role="alert">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded bg-brand px-3 py-2 text-sm font-medium text-white hover:bg-brand/90 disabled:opacity-50"
            >
              {submitting ? "Logging in" : "Log in"}
            </button>
          </form>

          <p className="mt-4 text-sm text-slate-500">
            No account?{" "}
            <Link
              href={registerHref}
              className="font-medium text-brand underline-offset-2 hover:underline"
            >
              Register
            </Link>
          </p>
        </Card>
      </div>
      <Disclaimer />
    </div>
  );
}
