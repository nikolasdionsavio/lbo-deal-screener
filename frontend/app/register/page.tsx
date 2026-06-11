"use client";

// Register page: minimal centered form (password minimum 8 characters,
// per BUILD_SPEC section 12). On success the JWT is stored by lib/auth
// and the user is redirected to "/" or the ?next= path.

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

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nextParam, setNextParam] = useState<string | null>(null);

  useEffect(() => {
    const next = safeNextPath();
    setNextParam(next === "/" ? null : next);
  }, []);

  const loginHref =
    nextParam !== null
      ? `/login?next=${encodeURIComponent(nextParam)}`
      : "/login";

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await register(email, password);
      router.replace(safeNextPath());
    } catch (err: unknown) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Could not create the account. Try again.",
      );
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col px-8 py-8">
      <div className="flex flex-1 items-center justify-center">
        <Card className="w-full max-w-sm">
          <h1 className="text-lg font-semibold text-ink">Register</h1>
          <p className="mt-1 text-sm text-slate-500">
            An account is required only for saving deals to a watchlist.
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
                autoComplete="new-password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={INPUT_CLASS}
              />
              <span className="mt-1 block text-xs font-normal text-slate-500">
                At least 8 characters.
              </span>
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
              {submitting ? "Creating account" : "Create account"}
            </button>
          </form>

          <p className="mt-4 text-sm text-slate-500">
            Already registered?{" "}
            <Link
              href={loginHref}
              className="font-medium text-brand underline-offset-2 hover:underline"
            >
              Log in
            </Link>
          </p>
        </Card>
      </div>
      <Disclaimer />
    </div>
  );
}
