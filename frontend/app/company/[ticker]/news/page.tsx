"use client";

// Company news page (BUILD_SPEC section 19.6): headline list from
// GET /api/companies/{ticker}/news with the provider shown in the header.
// In mock mode the backend returns an empty list with a live-only warning,
// which is rendered as the empty state.

import { useCompany } from "@/components/company/CompanyContext";
import NewsList from "@/components/news/NewsList";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import SectionHeader from "@/components/ui/SectionHeader";
import WarningList from "@/components/ui/WarningList";
import { getNews } from "@/lib/api";
import { useApi } from "@/lib/hooks";

export default function NewsPage() {
  const { profile } = useCompany();
  const ticker = profile.ticker;

  const { data, error, loading, retry } = useApi(() => getNews(ticker), [
    ticker,
  ]);

  if (loading) {
    return (
      <div>
        <SectionHeader variant="page" title="News" />
        <LoadingState lines={8} />
        <Disclaimer />
      </div>
    );
  }

  if (error !== null || data === null) {
    return (
      <div>
        <SectionHeader variant="page" title="News" />
        <ErrorState
          message={
            error !== null ? error.message : `Could not load news for ${ticker}.`
          }
          onRetry={retry}
        />
        <Disclaimer />
      </div>
    );
  }

  return (
    <div>
      <section>
        <SectionHeader
          variant="page"
          title="News"
          subtitle={`Provider: ${data.provider}`}
        />
        {data.items.length === 0 ? (
          <Card>
            <p className="text-sm text-warn-text">
              {data.warnings.length > 0
                ? data.warnings.join(" ")
                : `No recent news is available for ${ticker}.`}
            </p>
          </Card>
        ) : (
          <>
            <WarningList warnings={data.warnings} className="mb-4" />
            <Card>
              <NewsList items={data.items} />
            </Card>
          </>
        )}
      </section>

      <Disclaimer />
    </div>
  );
}
