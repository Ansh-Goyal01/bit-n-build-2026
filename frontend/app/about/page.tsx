import type { Metadata } from "next";

import { AboutContent } from "./about-content";

export const metadata: Metadata = {
  title: "About",
  description:
    "Why Adhikaar exists: welfare entitlements are rights, and finding out what you're owed shouldn't require an expert.",
};

export default function AboutPage() {
  return <AboutContent />;
}
