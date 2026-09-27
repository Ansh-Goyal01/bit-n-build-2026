import type { Metadata } from "next";

import { HowItWorksContent } from "./how-it-works-content";

export const metadata: Metadata = {
  title: "How it works",
  description:
    "How Adhikaar turns your answers into a cited eligibility report: official rules, a deterministic rules engine, and a verifier that checks every claim against the source.",
};

export default function HowItWorksPage() {
  return <HowItWorksContent />;
}
