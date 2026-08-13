"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  CloudUpload,
  Download,
  FileCheck2,
  FileSpreadsheet,
  RefreshCw,
  ShieldCheck
} from "lucide-react";
import { useRef, useState, type DragEvent } from "react";
import { ListSkeleton } from "@/components/data/list-states";
import { PageHeader } from "@/components/data/page-header";
import { StatusBadge } from "@/components/data/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/states";
import {
  ApiProblemError,
  type ImportHistoryRecord,
  type ImportKind,
  type ImportPreview,
  type ImportTemplate,
  type OrganizationSummary
} from "@/lib/api/contracts";
import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";
import { insightForgeApi } from "@runtime-api";

const kinds: ImportKind[] = ["customers", "products", "orders"];

function templateDownloadHref(template: ImportTemplate): string {
  return `data:text/csv;charset=utf-8,${encodeURIComponent(template.sample_csv)}`;
}

export function ImportPreviewPanel({
  preview,
  committing,
  onConfirm
}: {
  preview: ImportPreview;
  committing: boolean;
  onConfirm: () => void;
}) {
  const ready = preview.status === "ready";
  return (
    <Card className="overflow-hidden">
      <div
        className={cn(
          "border-b p-5 sm:p-6",
          ready
            ? "border-teal-100 bg-teal-50/70"
            : "border-coral-100 bg-coral-50/60"
        )}
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <span
              className={cn(
                "grid size-10 shrink-0 place-items-center rounded-xl",
                ready
                  ? "bg-teal-100 text-teal-700"
                  : "bg-coral-100 text-coral-700"
              )}
            >
              {ready ? (
                <FileCheck2 className="size-5" aria-hidden="true" />
              ) : (
                <AlertTriangle className="size-5" aria-hidden="true" />
              )}
            </span>
            <div>
              <h2 className="text-ink-950 text-lg font-bold">
                {ready ? "Validation passed" : "Validation needs attention"}
              </h2>
              <p className="text-ink-600 mt-1 text-xs leading-5">
                {preview.filename} ·{" "}
                {preview.total_rows.toLocaleString("en-US")} data rows ·
                Duplicate policy: create only
              </p>
            </div>
          </div>
          <StatusBadge status={preview.status} />
        </div>
        <dl className="mt-5 grid grid-cols-3 gap-3">
          <div className="rounded-xl bg-white/80 p-3">
            <dt className="text-ink-400 text-[9px] font-bold uppercase">
              Total rows
            </dt>
            <dd className="text-ink-950 mt-1 text-xl font-bold">
              {preview.total_rows}
            </dd>
          </div>
          <div className="rounded-xl bg-white/80 p-3">
            <dt className="text-ink-400 text-[9px] font-bold uppercase">
              Valid rows
            </dt>
            <dd className="mt-1 text-xl font-bold text-teal-700">
              {preview.valid_rows}
            </dd>
          </div>
          <div className="rounded-xl bg-white/80 p-3">
            <dt className="text-ink-400 text-[9px] font-bold uppercase">
              Error rows
            </dt>
            <dd className="text-coral-700 mt-1 text-xl font-bold">
              {preview.error_rows}
            </dd>
          </div>
        </dl>
      </div>
      {preview.preview_rows.length ? (
        <div>
          <div className="border-ink-100 border-b px-5 py-4">
            <h3 className="text-ink-950 font-bold">Sanitized preview</h3>
            <p className="text-ink-500 mt-1 text-xs">
              Up to five rows are shown. Formula-like cells are never evaluated.
            </p>
          </div>
          <div className="scrollbar-subtle overflow-x-auto">
            <table className="min-w-full text-left text-xs">
              <caption className="sr-only">CSV validation preview</caption>
              <thead className="bg-ink-50 text-ink-500 text-[9px] font-bold uppercase">
                <tr>
                  {preview.headers.map((header) => (
                    <th
                      key={header}
                      className="px-4 py-3 font-mono whitespace-nowrap"
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-ink-100 divide-y">
                {preview.preview_rows.map((row, index) => (
                  <tr key={index}>
                    {preview.headers.map((header) => (
                      <td
                        key={header}
                        className="text-ink-700 max-w-52 truncate px-4 py-3 whitespace-nowrap"
                      >
                        {row[header]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
      {preview.errors.length ? (
        <div className="border-ink-100 border-t">
          <div className="px-5 py-4">
            <h3 className="text-ink-950 font-bold">
              Structured validation errors
            </h3>
            <p className="text-ink-500 mt-1 text-xs">
              Showing a capped set of 25 safe errors
              {preview.errors_truncated
                ? "; additional errors were omitted"
                : ""}
              .
            </p>
          </div>
          <div className="divide-ink-100 max-h-80 divide-y overflow-y-auto">
            {preview.errors.map((error) => (
              <div
                key={error.id}
                className="grid gap-2 px-5 py-3 text-xs sm:grid-cols-[70px_150px_1fr]"
              >
                <span className="text-ink-500">
                  Row {error.row_number || "File"}
                </span>
                <span className="text-coral-700 font-mono text-[10px]">
                  {error.column} · {error.code}
                </span>
                <p className="text-ink-700">{error.message}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      <div className="border-ink-100 bg-ink-50/60 flex flex-col gap-3 border-t px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-ink-500 text-xs">
          Confirmation performs a final deterministic validation before the
          all-or-nothing commit.
        </p>
        <Button disabled={!ready || committing} onClick={onConfirm}>
          {committing ? (
            <RefreshCw className="size-4 animate-spin" aria-hidden="true" />
          ) : (
            <CheckCircle2 className="size-4" aria-hidden="true" />
          )}
          {committing ? "Importing rows" : "Confirm import"}
        </Button>
      </div>
    </Card>
  );
}

function ImportHistory({ records }: { records: ImportHistoryRecord[] }) {
  return (
    <Card className="overflow-hidden">
      <div className="border-ink-100 border-b px-5 py-4">
        <h2 className="text-ink-950 text-lg font-bold">Import history</h2>
        <p className="text-ink-500 mt-1 text-xs">
          Validation and commit outcomes from this workspace.
        </p>
      </div>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">CSV import history</caption>
          <thead className="bg-ink-50 text-ink-500 text-[10px] font-bold uppercase">
            <tr>
              <th className="px-5 py-3">File</th>
              <th className="px-5 py-3">Kind</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3 text-right">Imported</th>
              <th className="px-5 py-3 text-right">Errors</th>
              <th className="px-5 py-3">Uploaded</th>
            </tr>
          </thead>
          <tbody className="divide-ink-100 divide-y">
            {records.map((record) => (
              <tr key={record.id}>
                <td className="px-5 py-4">
                  <p className="text-ink-950 font-semibold">
                    {record.filename}
                  </p>
                </td>
                <td className="text-ink-600 px-5 py-4 capitalize">
                  {record.kind}
                </td>
                <td className="px-5 py-4">
                  <StatusBadge status={record.status} />
                </td>
                <td className="text-ink-800 px-5 py-4 text-right font-semibold">
                  {record.imported_rows}/{record.total_rows}
                </td>
                <td className="text-coral-700 px-5 py-4 text-right">
                  {record.error_rows}
                </td>
                <td className="text-ink-500 px-5 py-4 text-xs whitespace-nowrap">
                  {formatDateTime(record.created_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="divide-ink-100 divide-y md:hidden">
        {records.map((record) => (
          <article key={record.id} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-ink-950 truncate text-sm font-bold">
                  {record.filename}
                </p>
                <p className="text-ink-400 mt-1 text-[10px] capitalize">
                  {record.kind} · {formatDateTime(record.created_at)}
                </p>
              </div>
              <StatusBadge status={record.status} />
            </div>
            <p className="text-ink-600 mt-3 text-xs">
              {record.imported_rows} of {record.total_rows} rows imported ·{" "}
              {record.error_rows} errors
            </p>
          </article>
        ))}
      </div>
    </Card>
  );
}

export function DataSourcesPage({
  organization
}: {
  organization: OrganizationSummary;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const rawKind = searchParams.get("kind");
  const kind: ImportKind = kinds.includes(rawKind as ImportKind)
    ? (rawKind as ImportKind)
    : "customers";
  const templatesQuery = useQuery({
    queryKey: ["imports", "templates"],
    queryFn: ({ signal }) => insightForgeApi.imports.templates(signal)
  });
  const historyQuery = useQuery({
    queryKey: ["organization", organization.id, "imports", "history"],
    queryFn: ({ signal }) =>
      insightForgeApi.imports.history(organization.id, signal)
  });
  const validateImport = useMutation({
    mutationFn: async (file: File) =>
      insightForgeApi.imports.validate(organization.id, {
        kind,
        filename: file.name,
        size_bytes: file.size,
        mime_type: file.type,
        content: await file.text()
      }),
    onSuccess: (result) => {
      setPreview(result);
      setFeedback(
        result.status === "ready"
          ? "Validation passed. Review the preview before confirming."
          : "Validation finished with structured errors."
      );
    },
    onError: () =>
      setFeedback(
        "The file could not be validated. Confirm that it is a UTF-8 CSV and try again."
      )
  });
  const commitImport = useMutation({
    mutationFn: (importId: string) =>
      insightForgeApi.imports.commit(organization.id, importId),
    onSuccess: async (record) => {
      setFeedback(
        `${record.filename} imported ${record.imported_rows} rows successfully.`
      );
      setPreview(null);
      setSelectedFile(null);
      if (inputRef.current) inputRef.current.value = "";
      await queryClient.invalidateQueries({
        queryKey: ["organization", organization.id, "imports", "history"]
      });
    },
    onError: (error) =>
      setFeedback(
        error instanceof ApiProblemError
          ? error.problem.detail
          : "The import could not be confirmed."
      )
  });
  function chooseKind(nextKind: ImportKind) {
    const next = new URLSearchParams(searchParams.toString());
    next.set("kind", nextKind);
    router.replace(`${pathname}?${next.toString()}`, { scroll: false });
    setPreview(null);
    setSelectedFile(null);
    setFeedback(null);
  }
  function acceptFile(file: File | undefined) {
    if (!file) return;
    setSelectedFile(file);
    setPreview(null);
    setFeedback(null);
    validateImport.mutate(file);
  }
  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    acceptFile(event.dataTransfer.files[0]);
  }
  const selectedTemplate = templatesQuery.data?.find(
    (template) => template.kind === kind
  );

  return (
    <div>
      <PageHeader
        eyebrow="Private data ingestion"
        title="Data Sources"
        description={`Validate and import structured business data into ${organization.name} through a staged, all-or-nothing CSV workflow.`}
        badge="10 MiB · 50,000 row limit"
      />
      {feedback ? (
        <div
          role="status"
          className={cn(
            "mb-4 rounded-xl border px-4 py-3 text-sm font-medium",
            preview?.status === "validation_failed"
              ? "border-coral-200 bg-coral-50 text-coral-800"
              : "border-teal-200 bg-teal-50 text-teal-800"
          )}
        >
          {feedback}
        </div>
      ) : null}
      {templatesQuery.isPending ? <ListSkeleton rows={3} /> : null}
      {templatesQuery.isError ? (
        <ErrorState
          message="Import schemas could not be loaded."
          onRetry={() => void templatesQuery.refetch()}
        />
      ) : null}
      {templatesQuery.data ? (
        <div className="space-y-6">
          <section aria-labelledby="schemas-title">
            <div className="mb-3 flex items-end justify-between gap-3">
              <div>
                <h2
                  id="schemas-title"
                  className="text-ink-950 text-lg font-bold"
                >
                  Choose an exact v1 schema
                </h2>
                <p className="text-ink-500 mt-1 text-xs">
                  Headers are case-sensitive, ordered, and always English.
                </p>
              </div>
            </div>
            <div className="grid gap-4 lg:grid-cols-3">
              {templatesQuery.data.map((template) => (
                <Card
                  key={template.kind}
                  className={cn(
                    "p-4 transition",
                    kind === template.kind &&
                      "border-teal-400 ring-3 ring-teal-500/10"
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <button
                      type="button"
                      onClick={() => chooseKind(template.kind)}
                      className="min-w-0 text-left"
                    >
                      <span className="bg-ink-100 text-ink-700 grid size-9 place-items-center rounded-xl">
                        <FileSpreadsheet
                          className="size-4"
                          aria-hidden="true"
                        />
                      </span>
                      <h3 className="text-ink-950 mt-3 font-bold">
                        {template.name}
                      </h3>
                      <p className="text-ink-500 mt-1 text-xs leading-5">
                        {template.description}
                      </p>
                    </button>
                    {kind === template.kind ? (
                      <Badge className="border-teal-500/20 bg-teal-50 text-teal-700">
                        Selected
                      </Badge>
                    ) : null}
                  </div>
                  <code className="text-ink-500 bg-ink-50 mt-4 block max-h-16 overflow-hidden rounded-lg p-2 text-[9px] leading-4 break-all">
                    {template.headers.join(",")}
                  </code>
                  <a
                    href={templateDownloadHref(template)}
                    download={template.filename}
                    className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-teal-700 hover:text-teal-800"
                  >
                    <Download className="size-3.5" aria-hidden="true" />{" "}
                    Download {template.kind} sample
                  </a>
                </Card>
              ))}
            </div>
          </section>
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(300px,0.65fr)]">
            <Card className="p-5 sm:p-6">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-ink-400 text-[10px] font-bold uppercase">
                    Upload stage
                  </p>
                  <h2 className="text-ink-950 mt-1 text-lg font-bold capitalize">
                    Validate {kind} CSV
                  </h2>
                </div>
                <ShieldCheck
                  className="size-5 text-teal-600"
                  aria-hidden="true"
                />
              </div>
              <label
                htmlFor="csv-upload"
                onDragEnter={(event) => {
                  event.preventDefault();
                  setDragging(true);
                }}
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                className={cn(
                  "border-ink-300 bg-ink-50 mt-5 flex min-h-56 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-6 text-center transition",
                  dragging && "border-teal-500 bg-teal-50",
                  validateImport.isPending && "pointer-events-none opacity-70"
                )}
              >
                <input
                  ref={inputRef}
                  id="csv-upload"
                  type="file"
                  accept=".csv,text/csv"
                  className="sr-only"
                  onChange={(event) => acceptFile(event.target.files?.[0])}
                />
                <span className="grid size-12 place-items-center rounded-2xl bg-teal-50 text-teal-700">
                  {validateImport.isPending ? (
                    <RefreshCw
                      className="size-5 animate-spin"
                      aria-hidden="true"
                    />
                  ) : (
                    <CloudUpload className="size-5" aria-hidden="true" />
                  )}
                </span>
                <p className="text-ink-950 mt-4 text-sm font-bold">
                  {validateImport.isPending
                    ? "Validating private CSV"
                    : "Drop a CSV here or choose a file"}
                </p>
                <p
                  id="upload-help"
                  className="text-ink-500 mt-2 max-w-sm text-xs leading-5"
                >
                  UTF-8 only. Files are treated as inert text; formulas are
                  never evaluated. Exact headers:{" "}
                  {selectedTemplate?.headers.join(", ")}.
                </p>
                {selectedFile ? (
                  <Badge className="mt-4">
                    {selectedFile.name} ·{" "}
                    {(selectedFile.size / 1024).toFixed(1)} KiB
                  </Badge>
                ) : null}
              </label>
            </Card>
            <Card className="p-5">
              <h2 className="text-ink-950 text-lg font-bold">
                Validation policy
              </h2>
              <ul className="text-ink-600 mt-4 space-y-3 text-xs leading-5">
                {[
                  "Exact versioned English headers",
                  "UTF-8 text with strict CSV quoting",
                  "Required values, types, enums, and references",
                  "Formula-like cell neutralization",
                  "Capped safe errors and five-row preview",
                  "Final revalidation before transactional commit"
                ].map((policy) => (
                  <li key={policy} className="flex gap-2">
                    <CheckCircle2
                      className="mt-0.5 size-3.5 shrink-0 text-teal-600"
                      aria-hidden="true"
                    />
                    {policy}
                  </li>
                ))}
              </ul>
              <div className="bg-coral-50 text-coral-800 mt-5 rounded-xl p-3 text-xs leading-5">
                <strong>Private by default.</strong> Raw files and storage keys
                never appear in browser history or public download URLs.
              </div>
            </Card>
          </div>
          {preview ? (
            <ImportPreviewPanel
              preview={preview}
              committing={commitImport.isPending}
              onConfirm={() => commitImport.mutate(preview.import_id)}
            />
          ) : null}
          {historyQuery.isPending ? <ListSkeleton rows={3} /> : null}
          {historyQuery.isError ? (
            <ErrorState
              message="Import history could not be loaded."
              onRetry={() => void historyQuery.refetch()}
            />
          ) : null}
          {historyQuery.data ? (
            <ImportHistory records={historyQuery.data} />
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
