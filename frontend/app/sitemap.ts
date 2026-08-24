// Was a 404. Without this, discovery of anything past the homepage depends
// entirely on internal links being crawled, which is slow for a site with
// almost no inbound links.

import type { MetadataRoute } from "next";
import { INDEXABLE_ROUTES, SITE_URL } from "@/lib/seo";
import { RELEASES } from "@/lib/version";

/** Build-time constant: the date of the newest shipped release. Using a real
 *  date beats new Date(), which would claim every page changed on every
 *  deploy and teach crawlers to ignore the field. */
const LAST_MODIFIED = new Date(RELEASES[0].date);

export default function sitemap(): MetadataRoute.Sitemap {
  return INDEXABLE_ROUTES.map((route) => ({
    url: route === "/" ? SITE_URL : `${SITE_URL}${route}`,
    lastModified: LAST_MODIFIED,
    // The homepage and /about are the two pages that should answer a search
    // for the person, so they lead.
    priority: route === "/" ? 1 : route === "/about" ? 0.9 : 0.6,
    changeFrequency: route === "/" || route === "/screen" ? "weekly" : "monthly",
  }));
}
