"use client";

// Minimal toast: one polite live region, short-lived confirmations only
// ("code copied", "answers saved"). Errors belong inline, not in toasts.
import * as React from "react";

const ToastContext = React.createContext<(message: string) => void>(() => {});

export function useToast() {
  return React.useContext(ToastContext);
}

const TOAST_MS = 3500;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [message, setMessage] = React.useState<string | null>(null);
  const timer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const toast = React.useCallback((next: string) => {
    if (timer.current) clearTimeout(timer.current);
    setMessage(next);
    timer.current = setTimeout(() => setMessage(null), TOAST_MS);
  }, []);

  React.useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div
        role="status"
        aria-live="polite"
        className="print-hidden pointer-events-none fixed inset-x-0 bottom-6 z-50 flex justify-center px-4"
      >
        {message && (
          <div className="rounded-lg border border-border bg-foreground px-4 py-2.5 text-sm font-medium text-background shadow-raised">
            {message}
          </div>
        )}
      </div>
    </ToastContext.Provider>
  );
}
