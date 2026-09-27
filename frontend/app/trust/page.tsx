import type { Metadata } from "next";

import { TrustContent } from "./trust-content";

export const metadata: Metadata = {
  title: "Trust & sources",
  description:
    "The provenance of Adhikaar's rule base: every eligibility rule links to the exact government source, and a freshness monitor tracks when that source was last verified.",
};

export default function TrustPage() {
  return <TrustContent />;
}
