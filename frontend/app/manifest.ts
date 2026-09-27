import type { MetadataRoute } from "next";

import { SCHEME_COUNT } from "@/lib/site";

/** PWA manifest (R8). Installability is the whole point: a home-screen icon
 * an ASHA worker or NGO volunteer can hand someone, opening straight into the
 * wizard with no browser chrome. Colors mirror globals.css (terracotta accent
 * on warm ivory). Icons are full-bleed, so one asset serves `any` and
 * `maskable` alike. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Adhikaar — know what you're owed",
    short_name: "Adhikaar",
    description: `Answer a few plain-language questions and Adhikaar checks ${SCHEME_COUNT} Indian central and Uttar Pradesh welfare schemes — every verdict cited to the official scheme text.`,
    start_url: "/",
    display: "standalone",
    background_color: "#faf7f1",
    theme_color: "#96431f",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "maskable" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
