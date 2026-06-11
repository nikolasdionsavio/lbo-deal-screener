"use client";

// Saved deals watchlist. Auth required: without a token the page shows a
// centered prompt linking to login/register. With a token it lists saved
// deals (GET /api/deals) as cards with score, rating, dates, assumptions
// summary, embedded memo snapshot, and delete.

import Link from "next/link";
import DealCard from "@/components/deals/DealCard";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import SectionHeader from "@/components/ui/SectionHeader";
import { listDeals } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";

function LoginPrompt() {
  return (
    <div className="flex flex-1 items-center justify-center py-24">
      <Card className="w-full max-w-sm text-center">
        <h1 className="text-lg font-semibold text-ink">Saved deals</h1>
        <p className="mt-2 text-sm text-slate-600">
          Saving deals to a watchlist requires an account. Analysis pages
          remain available without one.
        </p>
        <div className="mt-5 flex justify-center gap-3">
          <Link
            href="/login?next=%2Fdeals"
            className="rounded bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand/90"
          >
            Log in
          </Link>
          <Link
            href="/register?next=%2Fdeals"
            className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Register
          </Link>
        </div>
      </Card>
    </div>
  );
}

function DealsList() {
  const { data, error, loading, retry } = useApi(() => listDeals(), []);

  if (loading) {
    return <LoadingState lines={8} />;
  }

  if (error !== null || data === null) {
    return (
      <ErrorState
        message={error !== null ? error.message : "Could not load saved deals."}
        onRetry={retry}
      />
    );
  }

  if (data.length === 0) {
    return (
      <Card>
        <p className="text-sm text-slate-600">
          No saved deals yet. Open a company memo and use Save to watchlist to
          add one.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {data.map((deal) => (
        <DealCard key={deal.id} deal={deal} onDeleted={retry} />
      ))}
    </div>
  );
}

export default function DealsPage() {
  const { user, loading } = useAuth();

  return (
    <div className="flex min-h-screen flex-col px-8 py-8">
      {loading ? (
        <LoadingState lines={6} />
      ) : user === null ? (
        <LoginPrompt />
      ) : (
        <div className="mx-auto w-full max-w-4xl">
          <SectionHeader
            title="Saved deals"
            subtitle={`Signed in as ${user.email}. Scores and memos are snapshots taken when each deal was saved or last updated.`}
          />
          <DealsList />
        </div>
      )}
      <Disclaimer />
    </div>
  );
}
