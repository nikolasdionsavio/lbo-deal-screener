"use client";

// OAuth return target. The backend redirects here with the app JWT (and any
// post-login path) in the URL fragment, e.g. /auth/callback#token=...&next=/deals.
// The fragment never reaches a server. We store the token, scrub the URL, and
// move the user along.

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import Card from "@/components/ui/Card";
import { useAuth } from "@/lib/auth";

function parseHash(): URLSearchParams {
  if (typeof window === "undefined") return new URLSearchParams();
  const raw = window.location.hash.replace(/^#/, "");
  return new URLSearchParams(raw);
}

function safeNext(next: string | null): string {
  if (next && next.startsWith("/") && !next.startsWith("//")) return next;
  return "/";
}

export default function OAuthCallbackPage() {
  const router = useRouter();
  const { applyExternalToken } = useAuth();
  const [failed, setFailed] = useState(false);
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    const params = parseHash();
    const token = params.get("token");
    const next = safeNext(params.get("next"));

    if (params.get("error") || !token) {
      router.replace("/login?error=oauth");
      return;
    }

    // Drop the token from the address bar before doing anything else.
    window.history.replaceState(null, "", window.location.pathname);

    applyExternalToken(token)
      .then(() => router.replace(next))
      .catch(() => setFailed(true));
  }, [applyExternalToken, router]);

  return (
    <div className="flex min-h-[calc(100vh-3rem)] items-center justify-center px-4 py-8">
      <Card className="w-full max-w-sm text-center">
        {failed ? (
          <>
            <p className="text-sm text-negative-text" role="alert">
              We could not finish signing you in. Please try again.
            </p>
            <a
              href="/login"
              className="mt-3 inline-block text-sm font-medium text-brand-text hover:underline"
            >
              Back to log in
            </a>
          </>
        ) : (
          <p className="text-sm text-ink-muted">Signing you in</p>
        )}
      </Card>
    </div>
  );
}
