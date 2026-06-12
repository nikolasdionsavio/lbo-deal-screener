"use client";

// Peer comparables page (BUILD_SPEC section 19.5): quartile stat cards,
// peers table with the target pinned and highlighted, and an EV/EBITDA bar
// chart with the target in the accent color. Data from
// GET /api/companies/{ticker}/peers; the first uncached load fetches
// fundamentals for every peer and can take a while — say so while loading.

import { useCompany } from "@/components/company/CompanyContext";
import EvEbitdaChart from "@/components/peers/EvEbitdaChart";
import PeerStatCards from "@/components/peers/PeerStatCards";
import PeersTable from "@/components/peers/PeersTable";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import SectionHeader from "@/components/ui/SectionHeader";
import WarningList from "@/components/ui/WarningList";
import { getPeers } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useApi } from "@/lib/hooks";

export default function PeersPage() {
  const { profile } = useCompany();
  const ticker = profile.ticker;

  const { data, error, loading, retry } = useApi(
    () => getPeers(ticker),
    [ticker],
  );

  if (loading) {
    return (
      <div>
        <SectionHeader variant="page" as="h2" title="Peer comparables" />
        <p className="mb-4 text-sm text-ink-muted">
          Pulling peer fundamentals from SEC filings. The first load can take
          half a minute; later visits come from cache.
        </p>
        <LoadingState lines={8} />
        <Disclaimer />
      </div>
    );
  }

  if (error !== null || data === null) {
    return (
      <div>
        <SectionHeader variant="page" as="h2" title="Peer comparables" />
        <ErrorState
          message={
            error !== null
              ? error.message
              : `Could not load peer comparables for ${ticker}.`
          }
          onRetry={retry}
        />
        <Disclaimer />
      </div>
    );
  }

  const hasPeers = data.peers.length > 0;

  return (
    <div>
      <section>
        <SectionHeader
          variant="page"
          as="h2"
          title="Peer comparables"
          subtitle={`Peer source: ${data.peer_source} · Data as of ${fmtDate(data.as_of)}`}
        />
        <WarningList warnings={data.warnings} className="mb-4" />
        {hasPeers ? (
          <PeerStatCards stats={data.stats} />
        ) : (
          <Card>
            <p className="text-sm text-ink-muted">
              No peers are available for {ticker}.
            </p>
          </Card>
        )}
      </section>

      {hasPeers && (
        <>
          {/* Shape first (where the target sits in the group), detail second. */}
          <section className="divider-dashed mt-8 pt-8">
            <SectionHeader
              title="EV / EBITDA"
              subtitle="Target shown in the accent color"
            />
            <Card>
              <EvEbitdaChart target={data.target} peers={data.peers} />
            </Card>
          </section>

          <section className="divider-dashed mt-8 pt-8">
            <SectionHeader
              title="Comparables table"
              subtitle="Target pinned to the top; figures in each company's reporting currency"
            />
            <Card>
              <PeersTable target={data.target} peers={data.peers} />
            </Card>
          </section>
        </>
      )}

      <Disclaimer />
    </div>
  );
}
