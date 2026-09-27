/** Yearly total for the report's value headline. Pure, import-free (node --test).
 *
 * Government pensions are generally not paid together: the UP widow and
 * divyang pensions exclude anyone "receiving pension from any other scheme of
 * the state or central government". So the total counts only the largest
 * pension; the others are still listed with their own amounts. */

export interface ValueEntry {
  schemeId: string;
  category: string;
  amountInr: number;
  period: string;
}

const RECURRING = new Set(["year", "month"]);

export function isRecurring(entry: ValueEntry): boolean {
  return RECURRING.has(entry.period);
}

export function annualTotal(entries: ValueEntry[]): { total: number; pensionsNotSummed: string[] } {
  const recurring = entries.filter(isRecurring);
  const pensions = recurring
    .filter((e) => e.category === "pension")
    .sort((a, b) => b.amountInr - a.amountInr);
  const counted = [...recurring.filter((e) => e.category !== "pension"), ...pensions.slice(0, 1)];
  return {
    total: counted.reduce((sum, e) => sum + e.amountInr, 0),
    pensionsNotSummed: pensions.slice(1).map((e) => e.schemeId),
  };
}
