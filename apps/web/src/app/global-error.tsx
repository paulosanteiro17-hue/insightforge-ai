"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Unexpected application error", error);
  }, [error]);

  return (
    <html lang="en">
      <body className="grid min-h-screen place-items-center bg-[#f7f9fb] px-6 font-sans text-[#0d1a2b]">
        <main className="max-w-md text-center">
          <p className="text-sm font-semibold text-[#0b8f82]">
            Something went wrong
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight">
            InsightForge could not open this page.
          </h1>
          <p className="mt-3 text-sm leading-6 text-[#405873]">
            Try the page again. If the problem continues, use the request
            details shown by the previous screen when contacting support.
          </p>
          <button
            type="button"
            onClick={reset}
            className="mt-6 h-11 rounded-xl bg-[#07111f] px-5 text-sm font-semibold text-white"
          >
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}
