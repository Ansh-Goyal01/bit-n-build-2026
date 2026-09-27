import type { Metadata } from "next";

import { SCHEME_COUNT } from "@/lib/site";

export const metadata: Metadata = {
  title: "Your eligibility report",
  description: `Where you stand with ${SCHEME_COUNT} central and Uttar Pradesh schemes — every verdict cited to the official scheme text, with an application packet for each scheme you qualify for.`,
};

export default function ResultsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
