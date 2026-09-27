import type { AssessResponse, UserProfile } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export interface FeedbackReport {
  category: "wrong_verdict" | "missing_scheme" | "translation" | "documents" | "other";
  scheme_id: string | null;
  message: string;
  lang: string;
}

/** Submit a PII-free issue report. The endpoint accepts nothing personal —
 * no profile, no name, no contact — and redacts pasted identifiers. */
export async function sendFeedback(report: FeedbackReport): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(report),
    });
  } catch {
    throw new ApiError(
      "We couldn't reach the feedback service. Please check your connection and try again.",
    );
  }
  if (!response.ok) {
    throw new ApiError("Your report couldn't be recorded. Please try again in a moment.");
  }
}

export async function assess(
  message: string,
  profile: UserProfile | null,
  lang: string = "en",
): Promise<AssessResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/assess`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // lang translates PROSE only, server-side at the edge; verdicts, scheme
      // names, amounts, and citations are language-invariant.
      body: JSON.stringify({ message, profile, lang }),
    });
  } catch {
    throw new ApiError(
      "We couldn't reach the assessment service. Please check your connection and try again.",
    );
  }
  if (!response.ok) {
    throw new ApiError(
      "Something went wrong while checking the schemes. Please try again in a moment.",
    );
  }
  return (await response.json()) as AssessResponse;
}
