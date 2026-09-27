import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { LIFE_EVENTS, lifeEventByKey } from "@/lib/life-events";

import { LifeEventContent } from "./life-event-content";

export function generateStaticParams() {
  return LIFE_EVENTS.map((event) => ({ event: event.key }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ event: string }>;
}): Promise<Metadata> {
  const { event } = await params;
  const lifeEvent = lifeEventByKey(event);
  return { title: lifeEvent?.metaTitle ?? "Check your eligibility" };
}

export default async function LifeEventPage({
  params,
}: {
  params: Promise<{ event: string }>;
}) {
  const { event } = await params;
  if (!lifeEventByKey(event)) notFound();
  return <LifeEventContent eventKey={event} />;
}
