"use client";

// Company profile context. The /company/[ticker] layout fetches the profile
// once and provides it here; all company pages read it via useCompany().
// This API is a contract for other page modules — do not change its shape.

import { createContext, useContext } from "react";
import type { CompanyProfile } from "@/lib/types";

export interface CompanyContextValue {
  profile: CompanyProfile;
  refetch: () => void;
}

export const CompanyContext = createContext<CompanyContextValue | null>(null);

export function useCompany(): CompanyContextValue {
  const ctx = useContext(CompanyContext);
  if (ctx === null) {
    throw new Error(
      "useCompany must be used within the /company/[ticker] layout",
    );
  }
  return ctx;
}
