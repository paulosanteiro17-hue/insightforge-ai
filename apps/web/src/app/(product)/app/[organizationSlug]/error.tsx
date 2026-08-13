"use client";

import { useEffect } from "react";
import { ErrorState } from "@/components/ui/states";

export default function OrganizationError({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Unexpected workspace error", error);
  }, [error]);
  return (
    <ErrorState
      title="This workspace could not be opened"
      message="An unexpected error interrupted the page. Try again without leaving your current organization."
      requestId={error.digest}
      onRetry={reset}
    />
  );
}
