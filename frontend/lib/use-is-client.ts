"use client";

import * as React from "react";

const emptySubscribe = () => () => {};

/** False during SSR and the hydration pass, true after — without effects,
 *  so client-only UI (localStorage-backed forms) can render mismatch-free. */
export function useIsClient(): boolean {
  return React.useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );
}
