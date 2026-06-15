"use client";

// Reset-password page (route /reset-password): reads ?token= from
// window.location.search after mount (no useSearchParams, so no Suspense
// boundary — same approach as login/register). Submits a new password to
// POST /api/auth/reset-password. Without a token, shows the missing-token
// state and a link back to /forgot-password.

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import { ApiError, resetPassword } from "@/lib/api";

export default function ResetPasswordPage() {
  // null = not yet read (server / first paint); "" = read, absent.
  const [token, setToken] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const value = new URLSearchParams(window.location.search).get("token");
    setToken(value ?? "");
  }, []);

  const mismatch = confirm.length > 0 && password !== confirm;

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (token === null || token === "") return;
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const res = await resetPassword(token, password);
      setMessage(res.detail);
    } catch (err: unknown) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Could not reset the password. The link may have expired.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  // Missing-token state. token === null means "still reading"; render the
  // form shell quietly until the effect resolves to avoid a flash.
  const tokenMissing = token === "";

  return (
    <div className="flex min-h-[calc(100vh-3rem)] flex-col px-4 py-8 sm:px-8">
      <div className="flex flex-1 items-center justify-center">
        <Card className="w-full max-w-sm">
          <h1 className="font-display text-lg font-semibold text-ink">
            Set a new password
          </h1>

          {tokenMissing ? (
            <>
              <p className="mt-2 text-sm text-ink-secondary">
                This reset link is missing or invalid.
              </p>
              <p className="mt-4 text-sm text-ink-muted">
                <Link
                  href="/forgot-password"
                  className="font-medium text-brand-text underline-offset-2 hover:underline"
                >
                  Request a new reset link
                </Link>
              </p>
            </>
          ) : message !== null ? (
            <>
              <p className="mt-2 text-sm text-ink-secondary" role="status">
                {message}
              </p>
              <p className="mt-4 text-sm text-ink-muted">
                <Link
                  href="/login"
                  className="font-medium text-brand-text underline-offset-2 hover:underline"
                >
                  Continue to log in
                </Link>
              </p>
            </>
          ) : (
            <>
              <p className="mt-1 text-sm text-ink-muted">
                Choose a new password for your account.
              </p>
              <form onSubmit={onSubmit} className="mt-5 space-y-4" noValidate>
                <label className="block text-sm font-medium text-ink-secondary">
                  New password
                  <input
                    type="password"
                    autoComplete="new-password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="input mt-1"
                  />
                  <span className="mt-1 block text-xs font-normal text-ink-muted">
                    At least 8 characters.
                  </span>
                </label>
                <label className="block text-sm font-medium text-ink-secondary">
                  Confirm password
                  <input
                    type="password"
                    autoComplete="new-password"
                    required
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    aria-invalid={mismatch || undefined}
                    className="input mt-1"
                  />
                  {mismatch && (
                    <span className="mt-1 block text-xs font-normal text-negative-text">
                      Passwords do not match.
                    </span>
                  )}
                </label>

                {error !== null && (
                  <p className="text-sm text-negative-text" role="alert">
                    {error}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={submitting || token === null}
                  className="btn btn-primary w-full px-3 py-2 text-sm"
                >
                  {submitting ? "Setting password" : "Set new password"}
                </button>
              </form>
            </>
          )}
        </Card>
      </div>
      <Disclaimer />
    </div>
  );
}
