// Typed API client for the Investment Intelligence backend (docs/BUILD_SPEC.md section 12).
// Plain fetch, one function per endpoint, Bearer token from localStorage when present.

import type {
  CompanyProfile,
  FilingsResponse,
  FinancialsResponse,
  KpiResponse,
  LboAssumptions,
  LboDefaultsResponse,
  LboResponse,
  MarketStats,
  MemoResponse,
  RiskResponse,
  NewsResponse,
  PeersResponse,
  SavedDeal,
  SaveDealRequest,
  ScoreResponse,
  ScreenFacets,
  ScreenQuery,
  ScreenResponse,
  ScreenSector,
  SearchResult,
  StatementsResponse,
  TokenResponse,
  User,
  ValuationRequest,
  ValuationResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// OAuth sign-in is begun via a full-page navigation that must land on the
// domain whose redirect URI is registered with Google/GitHub. In production
// that is nikolasproject.com (it proxies /api/auth/oauth/* to the backend), so
// the provider's screen shows that domain rather than the hf.space host. Falls
// back to API_BASE for local dev.
const OAUTH_BASE = process.env.NEXT_PUBLIC_OAUTH_BASE ?? API_BASE;

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = window.localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function parseDetail(res: Response): Promise<string> {
  try {
    const body: unknown = await res.json();
    if (
      body !== null &&
      typeof body === "object" &&
      "detail" in body &&
      typeof (body as { detail: unknown }).detail === "string"
    ) {
      return (body as { detail: string }).detail;
    }
  } catch {
    // Non-JSON error body; fall through to status text.
  }
  return res.statusText || `Request failed with status ${res.status}`;
}

async function request<T>(
  path: string,
  init: { method?: string; body?: unknown } = {},
): Promise<T> {
  const headers: Record<string, string> = { ...authHeaders() };
  let body: string | undefined;
  if (init.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(init.body);
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: init.method ?? "GET",
      headers,
      body,
    });
  } catch {
    throw new ApiError(0, "Could not reach the API. Check that the backend is running.");
  }

  if (!res.ok) {
    throw new ApiError(res.status, await parseDetail(res));
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

// ---------------------------------------------------------------------------
// Search and company data
// ---------------------------------------------------------------------------

export function searchCompanies(q: string): Promise<SearchResult[]> {
  return request<SearchResult[]>(`/api/search?q=${encodeURIComponent(q)}`);
}

export function getProfile(ticker: string): Promise<CompanyProfile> {
  return request<CompanyProfile>(
    `/api/companies/${encodeURIComponent(ticker)}/profile`,
  );
}

export function getMarketStats(ticker: string): Promise<MarketStats> {
  return request<MarketStats>(
    `/api/companies/${encodeURIComponent(ticker)}/market-stats`,
  );
}

export function getRisks(ticker: string): Promise<RiskResponse> {
  return request<RiskResponse>(
    `/api/companies/${encodeURIComponent(ticker)}/risks`,
  );
}

export function getFinancials(ticker: string): Promise<FinancialsResponse> {
  return request<FinancialsResponse>(
    `/api/companies/${encodeURIComponent(ticker)}/financials`,
  );
}

export function getStatements(ticker: string): Promise<StatementsResponse> {
  return request<StatementsResponse>(
    `/api/companies/${encodeURIComponent(ticker)}/statements`,
  );
}

export function getKpis(ticker: string): Promise<KpiResponse> {
  return request<KpiResponse>(
    `/api/companies/${encodeURIComponent(ticker)}/kpis`,
  );
}

export function getPeers(ticker: string): Promise<PeersResponse> {
  return request<PeersResponse>(
    `/api/companies/${encodeURIComponent(ticker)}/peers`,
  );
}

export function getFilings(ticker: string): Promise<FilingsResponse> {
  return request<FilingsResponse>(
    `/api/companies/${encodeURIComponent(ticker)}/filings`,
  );
}

export function getNews(
  ticker: string,
  limit?: number,
): Promise<NewsResponse> {
  const query = limit !== undefined ? `?limit=${limit}` : "";
  return request<NewsResponse>(
    `/api/companies/${encodeURIComponent(ticker)}/news${query}`,
  );
}

// ---------------------------------------------------------------------------
// Valuation, LBO, score, memo
// ---------------------------------------------------------------------------

export function runValuation(
  ticker: string,
  assumptions: ValuationRequest = {},
): Promise<ValuationResponse> {
  return request<ValuationResponse>(
    `/api/companies/${encodeURIComponent(ticker)}/valuation`,
    { method: "POST", body: assumptions },
  );
}

export function getLboDefaults(ticker: string): Promise<LboDefaultsResponse> {
  return request<LboDefaultsResponse>(
    `/api/companies/${encodeURIComponent(ticker)}/lbo/defaults`,
  );
}

export function runLbo(
  ticker: string,
  assumptions: LboAssumptions,
): Promise<LboResponse> {
  return request<LboResponse>(
    `/api/companies/${encodeURIComponent(ticker)}/lbo`,
    { method: "POST", body: assumptions },
  );
}

export function getScore(ticker: string): Promise<ScoreResponse> {
  return request<ScoreResponse>(
    `/api/companies/${encodeURIComponent(ticker)}/score`,
  );
}

export function generateMemo(
  ticker: string,
  lboAssumptions: LboAssumptions | null = null,
): Promise<MemoResponse> {
  return request<MemoResponse>(
    `/api/companies/${encodeURIComponent(ticker)}/memo`,
    { method: "POST", body: { lbo_assumptions: lboAssumptions } },
  );
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export function register(email: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>("/api/auth/register", {
    method: "POST",
    body: { email, password },
  });
}

export function login(email: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>("/api/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

export function me(): Promise<User> {
  return request<User>("/api/auth/me");
}

// Social sign-in (Google / GitHub). The OAuth dance is a full browser
// navigation to the backend, so these helpers build a URL rather than fetch.
export type OAuthProvider = "google" | "github";

export function getOAuthProviders(): Promise<Record<string, boolean>> {
  return request<Record<string, boolean>>("/api/auth/oauth/providers");
}

export function oauthLoginUrl(
  provider: OAuthProvider,
  next?: string | null,
): string {
  const params = new URLSearchParams();
  if (typeof window !== "undefined") {
    params.set("origin", window.location.origin);
  }
  if (next) params.set("next", next);
  const qs = params.toString();
  return `${OAUTH_BASE}/api/auth/oauth/${provider}/login${qs ? `?${qs}` : ""}`;
}

// Password reset. Both endpoints return a generic { detail } message; the
// forgot-password response never reveals whether the account exists.
export function forgotPassword(email: string): Promise<{ detail: string }> {
  return request<{ detail: string }>("/api/auth/forgot-password", {
    method: "POST",
    body: { email },
  });
}

export function resetPassword(
  token: string,
  password: string,
): Promise<{ detail: string }> {
  return request<{ detail: string }>("/api/auth/reset-password", {
    method: "POST",
    body: { token, password },
  });
}

// ---------------------------------------------------------------------------
// Saved deals
// ---------------------------------------------------------------------------

export function listDeals(): Promise<SavedDeal[]> {
  return request<SavedDeal[]>("/api/deals");
}

export function saveDeal(payload: SaveDealRequest): Promise<SavedDeal> {
  return request<SavedDeal>("/api/deals", { method: "POST", body: payload });
}

export function updateDealAssumptions(
  id: number,
  lboAssumptions: LboAssumptions,
): Promise<SavedDeal> {
  return request<SavedDeal>(`/api/deals/${id}/assumptions`, {
    method: "PUT",
    body: { lbo_assumptions: lboAssumptions },
  });
}

export function deleteDeal(id: number): Promise<void> {
  return request<void>(`/api/deals/${id}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// US screening index
// ---------------------------------------------------------------------------

export function getScreen(query: ScreenQuery = {}): Promise<ScreenResponse> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    // Skip unset filters so the backend applies its own defaults rather than
    // receiving "null" as a literal string.
    if (value === null || value === undefined || value === "") continue;
    params.set(key, String(value));
  }
  const qs = params.toString();
  return request<ScreenResponse>(`/api/screen${qs ? `?${qs}` : ""}`);
}

export function getScreenSectors(): Promise<ScreenSector[]> {
  return request<ScreenSector[]>("/api/screen/sectors");
}

export function getScreenFacets(): Promise<ScreenFacets> {
  return request<ScreenFacets>("/api/screen/facets");
}
