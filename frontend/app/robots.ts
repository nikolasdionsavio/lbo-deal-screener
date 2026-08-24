// Was a 404. A missing robots.txt is not fatal, but it also means nothing
// points a crawler at the sitemap, and the auth pages were as crawlable as
// the research ones.

import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // Nothing here belongs in a search result: signed-out shells of
      // signed-in pages, and one-pagers generated per ticker on demand.
      disallow: [
        "/login",
        "/register",
        "/forgot-password",
        "/reset-password",
        "/deals",
        "/onepager/",
      ],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
