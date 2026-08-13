import { ApiProblemError } from "@/lib/api/contracts";

export const fieldClassName =
  "mt-2 h-11 w-full rounded-xl border border-ink-200 bg-white px-3 text-sm text-ink-900 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-500/15 disabled:cursor-not-allowed disabled:bg-ink-50 disabled:text-ink-500";

export function getApiErrorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiProblemError ? error.problem.detail : fallback;
}

export function downloadTextArtifact(artifact: {
  filename: string;
  mime_type: string;
  content: string;
}): void {
  const blob = new Blob([artifact.content], { type: artifact.mime_type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = artifact.filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
