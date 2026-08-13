"use client";

import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileBarChart, Plus, RefreshCw } from "lucide-react";
import { useState, type FormEvent } from "react";
import { DataToolbar } from "@/components/data/data-toolbar";
import { ListSkeleton } from "@/components/data/list-states";
import { PageHeader } from "@/components/data/page-header";
import { StatusBadge } from "@/components/data/status-badge";
import { RangeFilter } from "@/components/dashboard/range-filter";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/states";
import {
  ApiProblemError,
  type OrganizationSummary,
  type ReportFormat,
  type ReportListQuery,
  type ReportRecord,
  type ReportStatus,
  type ReportType
} from "@/lib/api/contracts";
import { formatDateTime } from "@/lib/format";
import { insightForgeApi } from "@runtime-api";
import { parseAnalyticsRange } from "@/lib/url-state";

const reportTypes: Array<{ value: ReportType; label: string }> = [
  { value: "monthly_performance", label: "Monthly Performance" },
  { value: "sales", label: "Sales Report" },
  { value: "customer", label: "Customer Report" },
  { value: "product_performance", label: "Product Performance" }
];
const reportStatuses: Array<{ value: ReportStatus; label: string }> = [
  { value: "queued", label: "Queued" },
  { value: "ready", label: "Ready" },
  { value: "generating", label: "Generating" },
  { value: "failed", label: "Failed" },
  { value: "expired", label: "Expired" }
];

function ReportTable({
  reports,
  onDownload,
  downloadingId
}: {
  reports: ReportRecord[];
  onDownload: (report: ReportRecord) => void;
  downloadingId: string | null;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Generated report history</caption>
          <thead className="bg-ink-50/80 text-ink-500 text-[10px] font-bold tracking-[0.11em] uppercase">
            <tr>
              <th className="px-5 py-3.5">Report</th>
              <th className="px-5 py-3.5">Type</th>
              <th className="px-5 py-3.5">Range</th>
              <th className="px-5 py-3.5">Status</th>
              <th className="px-5 py-3.5">Generated</th>
              <th className="px-5 py-3.5 text-right">Rows</th>
              <th className="px-5 py-3.5 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-ink-100 divide-y">
            {reports.map((report) => (
              <tr key={report.id} className="hover:bg-ink-50/60">
                <td className="px-5 py-4">
                  <p className="text-ink-950 font-semibold">{report.name}</p>
                  <p className="text-ink-400 mt-1 max-w-xs truncate text-[10px]">
                    Source revision {report.source_revision}
                  </p>
                </td>
                <td className="text-ink-600 px-5 py-4">
                  {
                    reportTypes.find((item) => item.value === report.type)
                      ?.label
                  }
                </td>
                <td className="text-ink-600 px-5 py-4">
                  {report.date_from && report.date_to
                    ? `${new Intl.DateTimeFormat("en-US", {
                        dateStyle: "medium"
                      }).format(
                        new Date(report.date_from)
                      )} – ${new Intl.DateTimeFormat("en-US", {
                        dateStyle: "medium"
                      }).format(new Date(report.date_to))}`
                    : report.range === "year_to_date"
                      ? "YTD"
                      : report.range}
                </td>
                <td className="px-5 py-4">
                  <StatusBadge status={report.status} />
                </td>
                <td className="text-ink-500 px-5 py-4 text-xs whitespace-nowrap">
                  {report.generated_at
                    ? formatDateTime(report.generated_at)
                    : "Not generated"}
                </td>
                <td className="text-ink-700 px-5 py-4 text-right">
                  {report.row_count?.toLocaleString("en-US") ?? "—"}
                </td>
                <td className="px-5 py-4 text-right">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={
                      report.status !== "ready" || downloadingId === report.id
                    }
                    onClick={() => onDownload(report)}
                  >
                    {downloadingId === report.id ? (
                      <RefreshCw
                        className="size-3.5 animate-spin"
                        aria-hidden="true"
                      />
                    ) : (
                      <Download className="size-3.5" aria-hidden="true" />
                    )}{" "}
                    Download {report.format.toUpperCase()}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="divide-ink-100 divide-y md:hidden">
        {reports.map((report) => (
          <article key={report.id} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="text-ink-950 truncate text-sm font-bold">
                  {report.name}
                </h2>
                <p className="text-ink-400 mt-1 text-[10px]">
                  {
                    reportTypes.find((item) => item.value === report.type)
                      ?.label
                  }{" "}
                  · {report.granularity}
                </p>
              </div>
              <StatusBadge status={report.status} />
            </div>
            <p className="text-ink-600 mt-3 text-xs leading-5">
              Source revision {report.source_revision}
            </p>
            <div className="mt-4 flex items-center justify-between">
              <p className="text-ink-400 text-[10px]">
                {report.row_count?.toLocaleString("en-US") ?? "Pending"} rows ·{" "}
                {report.format.toUpperCase()}
              </p>
              <Button
                size="sm"
                variant="outline"
                disabled={
                  report.status !== "ready" || downloadingId === report.id
                }
                onClick={() => onDownload(report)}
              >
                <Download className="size-3.5" aria-hidden="true" /> Download
              </Button>
            </div>
          </article>
        ))}
      </div>
    </Card>
  );
}

export function ReportsPage({
  organization
}: {
  organization: OrganizationSummary;
}) {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [createType, setCreateType] = useState<ReportType>(
    "monthly_performance"
  );
  const [createFormat, setCreateFormat] = useState<ReportFormat>("csv");
  const [createName, setCreateName] = useState("Monthly Performance");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const range = parseAnalyticsRange(searchParams.get("range"));
  const typeValue = searchParams.get("type");
  const statusValue = searchParams.get("status");
  const query: ReportListQuery = {
    search: searchParams.get("q") || undefined,
    type: reportTypes.some((item) => item.value === typeValue)
      ? (typeValue as ReportType)
      : undefined,
    status: reportStatuses.some((item) => item.value === statusValue)
      ? (statusValue as ReportStatus)
      : undefined,
    range
  };
  const templatesQuery = useQuery({
    queryKey: ["organization", organization.id, "reports", "templates"],
    queryFn: ({ signal }) =>
      insightForgeApi.reports.templates(organization.id, signal)
  });
  const reportsQuery = useQuery({
    queryKey: ["organization", organization.id, "reports", query],
    queryFn: ({ signal }) =>
      insightForgeApi.reports.list(organization.id, query, signal)
  });
  const createReport = useMutation({
    mutationFn: () =>
      insightForgeApi.reports.create(organization.id, {
        type: createType,
        name: createName.trim(),
        format: createFormat,
        range
      }),
    onSuccess: async (report) => {
      setFeedback(`${report.name} is ready to download.`);
      await queryClient.invalidateQueries({
        queryKey: ["organization", organization.id, "reports"]
      });
    },
    onError: () => setFeedback("The report could not be generated. Try again.")
  });
  async function download(report: ReportRecord) {
    setDownloadingId(report.id);
    try {
      const artifact = await insightForgeApi.reports.download(
        organization.id,
        report.id
      );
      const blob = new Blob([artifact.content], { type: artifact.mime_type });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = artifact.filename;
      anchor.click();
      URL.revokeObjectURL(url);
      setFeedback(`${artifact.filename} downloaded successfully.`);
    } catch {
      setFeedback(
        "The report download is no longer available. Generate a fresh report."
      );
    } finally {
      setDownloadingId(null);
    }
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createReport.mutate();
  }
  const selectedTemplate = templatesQuery.data?.find(
    (template) => template.type === createType
  );

  return (
    <div>
      <PageHeader
        eyebrow="Reusable business exports"
        title="Reports"
        description={`Generate bounded, tenant-scoped reports for ${organization.name}. Downloads are created from validated analytics and expire after retention.`}
        badge="Formula-safe exports"
        actions={<RangeFilter value={range} />}
      />
      {feedback ? (
        <div
          role="status"
          className="mb-4 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm font-medium text-teal-800"
        >
          {feedback}
        </div>
      ) : null}
      <Card className="mb-5 overflow-hidden">
        <div className="grid lg:grid-cols-[1fr_1.2fr]">
          <div className="bg-ink-950 p-5 text-white sm:p-6">
            <span className="grid size-10 place-items-center rounded-xl bg-teal-500/15 text-teal-300">
              <FileBarChart className="size-5" aria-hidden="true" />
            </span>
            <h2 className="mt-5 text-xl font-bold">Create a fresh report</h2>
            <p className="text-ink-300 mt-2 text-sm leading-6">
              Choose a controlled report definition, the active reporting
              period, and an export format.
            </p>
            <div className="mt-5 space-y-2">
              <p className="text-ink-300 flex items-center gap-2 text-xs">
                <span className="size-1.5 rounded-full bg-teal-400" />
                {selectedTemplate?.supported_formats
                  ? selectedTemplate.supported_formats
                      .map((format) => format.toUpperCase())
                      .join(" and ")
                  : "Loading formats"}
              </p>
            </div>
          </div>
          <form onSubmit={submit} className="p-5 sm:p-6">
            <div className="grid gap-4 sm:grid-cols-2">
              <label>
                <span className="text-ink-700 text-xs font-semibold">
                  Report type
                </span>
                <select
                  value={createType}
                  onChange={(event) => {
                    const nextType = event.target.value as ReportType;
                    setCreateType(nextType);
                    const template = templatesQuery.data?.find(
                      (item) => item.type === nextType
                    );
                    if (template) {
                      setCreateName(
                        template.default_name ??
                          template.label ??
                          template.name ??
                          "Report"
                      );
                    }
                  }}
                  className="border-ink-200 text-ink-800 mt-2 h-11 w-full rounded-xl border bg-white px-3 text-sm"
                >
                  {templatesQuery.data?.map((template) => (
                    <option key={template.type} value={template.type}>
                      {template.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span className="text-ink-700 text-xs font-semibold">
                  Export format
                </span>
                <select
                  value={createFormat}
                  onChange={(event) =>
                    setCreateFormat(event.target.value as ReportFormat)
                  }
                  className="border-ink-200 text-ink-800 mt-2 h-11 w-full rounded-xl border bg-white px-3 text-sm"
                >
                  <option value="csv">CSV spreadsheet</option>
                  <option value="json">Structured JSON</option>
                </select>
              </label>
            </div>
            <label className="mt-4 block">
              <span className="text-ink-700 text-xs font-semibold">
                Report name
              </span>
              <input
                value={createName}
                onChange={(event) => setCreateName(event.target.value)}
                maxLength={160}
                required
                className="border-ink-200 text-ink-800 mt-2 h-11 w-full rounded-xl border bg-white px-3 text-sm"
              />
            </label>
            <div className="bg-ink-50 mt-4 rounded-xl p-4">
              <p className="text-ink-900 text-sm font-semibold">
                {selectedTemplate?.label ?? "Loading template"}
              </p>
              <p className="text-ink-500 mt-1 text-xs leading-5">
                {selectedTemplate?.description}
              </p>
            </div>
            <Button
              type="submit"
              className="mt-4"
              disabled={
                createReport.isPending ||
                templatesQuery.isPending ||
                !createName.trim()
              }
            >
              {createReport.isPending ? (
                <RefreshCw className="size-4 animate-spin" aria-hidden="true" />
              ) : (
                <Plus className="size-4" aria-hidden="true" />
              )}{" "}
              {createReport.isPending
                ? "Generating report"
                : `Generate ${createFormat.toUpperCase()} report`}
            </Button>
          </form>
        </div>
      </Card>
      <div className="mb-4">
        <DataToolbar
          searchLabel="Search reports"
          searchPlaceholder="Search report name or summary"
          filters={[
            {
              param: "type",
              label: "Report type",
              allLabel: "All report types",
              options: reportTypes
            },
            {
              param: "status",
              label: "Report status",
              allLabel: "All statuses",
              options: reportStatuses
            }
          ]}
          sortOptions={[{ value: "created_at_desc", label: "Newest first" }]}
        />
      </div>
      {reportsQuery.isPending ? <ListSkeleton /> : null}
      {reportsQuery.isError ? (
        <ErrorState
          message={
            reportsQuery.error instanceof ApiProblemError
              ? reportsQuery.error.problem.detail
              : "Reports could not be loaded."
          }
          onRetry={() => void reportsQuery.refetch()}
        />
      ) : null}
      {reportsQuery.data?.length === 0 ? (
        <EmptyState
          title="No reports match this view"
          message="Clear a filter, choose another reporting period, or generate a new report."
        />
      ) : null}
      {reportsQuery.data?.length ? (
        <ReportTable
          reports={reportsQuery.data}
          onDownload={(report) => void download(report)}
          downloadingId={downloadingId}
        />
      ) : null}
    </div>
  );
}
