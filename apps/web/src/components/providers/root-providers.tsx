"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

export function RootProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            gcTime: 5 * 60_000,
            retry: (failureCount, error) => {
              const status =
                error && typeof error === "object" && "problem" in error
                  ? (error as { problem?: { status?: number } }).problem?.status
                  : undefined;

              if (status && status >= 400 && status < 500 && status !== 429) {
                return false;
              }

              return failureCount < 2;
            },
            refetchOnWindowFocus: false
          },
          mutations: {
            retry: false
          }
        }
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <div
        id="toast-region"
        className="pointer-events-none fixed right-4 bottom-4 z-[100]"
        aria-live="polite"
        aria-atomic="true"
      />
    </QueryClientProvider>
  );
}
