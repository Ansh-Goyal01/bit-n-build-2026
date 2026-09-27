import type { Metadata } from "next";

import { CATALOG_COUNT, SCHEME_COUNT } from "@/lib/site";

import { SchemesContent } from "./schemes-content";

export const metadata: Metadata = {
  title: "Explore schemes",
  description: `Browse ${CATALOG_COUNT} central and Uttar Pradesh welfare schemes — benefits, eligibility rules, documents, and official sources. ${SCHEME_COUNT} are covered by the eligibility check today.`,
};

export default function SchemesPage() {
  return <SchemesContent />;
}
