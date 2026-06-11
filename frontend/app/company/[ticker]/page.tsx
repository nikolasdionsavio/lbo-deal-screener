import { redirect } from "next/navigation";

// /company/[ticker] redirects to the dashboard view (BUILD_SPEC section 14).
export default function CompanyIndexPage({
  params,
}: {
  params: { ticker: string };
}) {
  redirect(`/company/${encodeURIComponent(params.ticker)}/dashboard`);
}
