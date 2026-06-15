"use client";

// Forgot-password page (route /forgot-password): centered card matching the
// login/register layout. Submits the email to POST /api/auth/forgot-password
// and always shows the generic { detail } message the API returns — the
// response never reveals whether the account exists.

import Link from "next/link";
import { useState, type FormEvent } from "react";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import { ApiError, forgotPassword } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const res = await forgotPassword(email);
      setMessage(res.detail);
    } catch (err: unknown) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Could not send the reset link. Try again.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-3rem)] flex-col px-4 py-8 sm:px-8">
      <div className="flex flex-1 items-center justify-center">
        <Card className="w-full max-w-sm">
          <h1 className="font-display text-lg font-semibold text-ink">
            Reset your password
          </h1>
          <p className="mt-1 text-sm text-ink-muted">
            Enter the email for your account and we will send a reset link.
          </p>

          {message !== null ? (
            <p
              className="mt-5 text-sm text-ink-secondary"
              role="status"
            >
              {message}
            </p>
          ) : (
            <form onSubmit={onSubmit} className="mt-5 space-y-4" noValidate>
              <label className="block text-sm font-medium text-ink-secondary">
                Email
                <input
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input mt-1"
                />
              </label>

              {error !== null && (
                <p className="text-sm text-negative-text" role="alert">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="btn btn-primary w-full px-3 py-2 text-sm"
              >
                {submitting ? "Sending" : "Send reset link"}
              </button>
            </form>
          )}

          <p className="mt-4 text-sm text-ink-muted">
            Remembered it?{" "}
            <Link
              href="/login"
              className="font-medium text-brand-text underline-offset-2 hover:underline"
            >
              Back to log in
            </Link>
          </p>
        </Card>
      </div>
      <Disclaimer />
    </div>
  );
}
