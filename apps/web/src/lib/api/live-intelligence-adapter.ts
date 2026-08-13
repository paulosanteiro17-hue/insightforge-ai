import type * as Backend from "@/lib/api/backend-contracts";
import {
  ApiProblemError,
  type AiInsight,
  type AskAnswer,
  type InsightForgeApi,
  type ReportRecord,
  type ReportTemplate,
  type WeeklySummary
} from "@/lib/api/contracts";
import { ApiHttpClient, pollUntil } from "@/lib/api/http-client";
import { rangeDates } from "@/lib/api/live-ranges";

type IntelligenceApi = Pick<
  InsightForgeApi,
  "insights" | "askData" | "reports"
>;

const terminalJobStatuses = new Set<Backend.JobStatus>([
  "succeeded",
  "failed",
  "cancelled"
]);
const terminalReportStatuses = new Set<Backend.ReportView["status"]>([
  "ready",
  "failed",
  "expired"
]);

function operationFailed(
  title: string,
  detail: string,
  code: string
): ApiProblemError {
  return new ApiProblemError({
    title,
    detail,
    status: 409,
    code,
    request_id: "client"
  });
}

export function mapInsight(value: Backend.InsightView): AiInsight {
  return {
    id: value.id,
    title: value.title,
    description: value.description,
    category: value.category,
    severity: value.severity,
    supporting_metrics: value.supporting_metrics,
    generated_at: value.generated_at,
    period_start: value.period_start,
    period_end: value.period_end,
    provider: value.provider,
    generation_mode: value.generation_mode
  };
}

export function mapWeeklySummary(
  value: Backend.WeeklySummaryView
): WeeklySummary {
  return {
    id: value.id,
    week_start: value.week_start,
    week_end: value.week_end,
    headline: value.headline,
    overview: value.overview,
    highlights: value.highlights,
    watch_items: value.watch_items,
    generated_at: value.generated_at,
    provider: value.provider,
    generation_mode: value.generation_mode,
    source_revision: String(value.source_revision)
  };
}

function mapAnswer(value: Backend.AssistantAnswerView): AskAnswer {
  return {
    id: value.id,
    question: value.question_redacted,
    intent: value.intent,
    status: value.answer_status,
    answer: value.answer,
    citations: value.citations,
    suggested_follow_ups: value.follow_ups,
    applied_range: value.applied_range,
    confidence: value.confidence,
    provider: value.provider,
    created_at: value.created_at
  };
}

function mapTemplate(value: Backend.ReportTemplateView): ReportTemplate {
  return {
    type: value.report_type,
    label: value.label,
    description: value.description,
    default_name: value.default_name,
    supported_formats: value.supported_formats
  };
}

function mapReport(value: Backend.ReportView): ReportRecord {
  const rowCount = value.result_summary?.row_count;
  return {
    id: value.id,
    name: value.name,
    type: value.report_type,
    status: value.status,
    format: value.format,
    date_from: value.filters.date_from,
    date_to: value.filters.date_to,
    granularity: value.filters.granularity,
    source_revision: String(value.source_revision),
    result_summary: value.result_summary,
    created_at: value.created_at,
    updated_at: value.updated_at,
    generated_at: value.generated_at,
    expires_at: value.expires_at,
    row_count: typeof rowCount === "number" ? rowCount : null
  };
}

async function loadInsights(
  client: ApiHttpClient,
  organizationId: string,
  signal?: AbortSignal
): Promise<AiInsight[]> {
  const response = await client.collection<Backend.InsightView>("/insights", {
    organizationId,
    query: { page: 1, page_size: 100 },
    signal
  });
  return response.data.map(mapInsight);
}

export async function loadCurrentWeeklySummary(
  client: ApiHttpClient,
  organizationId: string,
  signal?: AbortSignal
): Promise<WeeklySummary | null> {
  try {
    const response = await client.request<Backend.WeeklySummaryView>(
      "/weekly-summary/current",
      { organizationId, signal }
    );
    return mapWeeklySummary(response.data);
  } catch (error) {
    if (error instanceof ApiProblemError && error.problem.status === 404)
      return null;
    throw error;
  }
}

export async function regenerateWeeklySummary(
  client: ApiHttpClient,
  organizationId: string,
  signal?: AbortSignal
): Promise<WeeklySummary> {
  const queued = await client.request<Backend.GenerationJobView>(
    "/weekly-summary/generation-jobs",
    { method: "POST", organizationId, idempotent: true, json: {}, signal }
  );
  const completed = await pollUntil(
    async (pollSignal) =>
      (
        await client.request<Backend.GenerationJobView>(
          `/weekly-summary/generation-jobs/${queued.data.id}`,
          { organizationId, signal: pollSignal }
        )
      ).data,
    {
      signal,
      isComplete: (job) => terminalJobStatuses.has(job.status),
      isFailed: (job) => job.status === "failed" || job.status === "cancelled"
    }
  );
  if (completed.status !== "succeeded") {
    throw operationFailed(
      "Weekly summary failed",
      "The weekly summary job did not complete successfully.",
      completed.error_code ?? "weekly_summary_generation_failed"
    );
  }
  const summary = await loadCurrentWeeklySummary(
    client,
    organizationId,
    signal
  );
  if (!summary) {
    throw operationFailed(
      "Weekly summary unavailable",
      "The completed job did not produce a readable weekly summary.",
      "weekly_summary_missing"
    );
  }
  return summary;
}

export function createLiveIntelligenceApi(
  client: ApiHttpClient
): IntelligenceApi {
  return {
    insights: {
      async list(organizationId, query, signal) {
        const normalizedSearch = query.search
          ?.trim()
          .toLocaleLowerCase("en-US");
        const items = (
          await loadInsights(client, organizationId, signal)
        ).filter(
          (insight) =>
            (!query.category || insight.category === query.category) &&
            (!query.severity || insight.severity === query.severity) &&
            (!normalizedSearch ||
              insight.title
                .toLocaleLowerCase("en-US")
                .includes(normalizedSearch) ||
              insight.description
                .toLocaleLowerCase("en-US")
                .includes(normalizedSearch))
        );
        return {
          organization_id: organizationId,
          range: query.range,
          generated_at: items[0]?.generated_at ?? new Date(0).toISOString(),
          generation_mode: items[0]?.generation_mode ?? "deterministic",
          items
        };
      },
      async regenerate(organizationId, range, signal) {
        const queued = await client.request<Backend.GenerationJobView>(
          "/insights/generation-jobs",
          {
            method: "POST",
            organizationId,
            query: { range },
            idempotent: true,
            json: {},
            signal
          }
        );
        const completed = await pollUntil(
          async (pollSignal) =>
            (
              await client.request<Backend.GenerationJobView>(
                `/insights/generation-jobs/${queued.data.id}`,
                { organizationId, signal: pollSignal }
              )
            ).data,
          {
            signal,
            isComplete: (job) => terminalJobStatuses.has(job.status),
            isFailed: (job) =>
              job.status === "failed" || job.status === "cancelled"
          }
        );
        if (completed.status !== "succeeded") {
          throw operationFailed(
            "Insight generation failed",
            "The insight generation job did not complete successfully.",
            completed.error_code ?? "insight_generation_failed"
          );
        }
        const items = await loadInsights(client, organizationId, signal);
        return {
          organization_id: organizationId,
          range,
          generated_at:
            items[0]?.generated_at ??
            completed.completed_at ??
            completed.created_at,
          generation_mode: items[0]?.generation_mode ?? "deterministic",
          generation_id: completed.id,
          status: "succeeded",
          feedback: `${items.length} grounded insights were generated from the latest analytics snapshot.`,
          items
        };
      }
    },
    askData: {
      async getCapabilities(organizationId, signal) {
        const response = await client.request<Backend.AskCapabilitiesView>(
          "/ask-data/capabilities",
          { organizationId, signal }
        );
        return response.data;
      },
      async ask(organizationId, input, signal) {
        const response = await client.request<Backend.AssistantAnswerView>(
          "/ask-data/answers",
          {
            method: "POST",
            organizationId,
            query: { range: input.range },
            idempotent: true,
            json: { question: input.question },
            signal
          }
        );
        return mapAnswer(response.data);
      },
      async history(organizationId, signal) {
        const response = await client.collection<Backend.AssistantAnswerView>(
          "/ask-data/history",
          { organizationId, query: { page: 1, page_size: 25 }, signal }
        );
        return response.data.map(mapAnswer);
      }
    },
    reports: {
      async templates(organizationId, signal) {
        const response = await client.collection<Backend.ReportTemplateView>(
          "/reports/templates",
          { organizationId, signal }
        );
        return response.data.map(mapTemplate);
      },
      async list(organizationId, query, signal) {
        const response = await client.collection<Backend.ReportView>(
          "/reports",
          {
            organizationId,
            query: {
              page: 1,
              page_size: 100,
              report_type: query.type,
              status: query.status
            },
            signal
          }
        );
        const normalizedSearch = query.search
          ?.trim()
          .toLocaleLowerCase("en-US");
        return response.data
          .map(mapReport)
          .filter(
            (report) =>
              !normalizedSearch ||
              report.name.toLocaleLowerCase("en-US").includes(normalizedSearch)
          );
      },
      async create(organizationId, input, signal) {
        const dates = rangeDates(input.range);
        const response = await client.request<Backend.ReportView>("/reports", {
          method: "POST",
          organizationId,
          idempotent: true,
          json: {
            report_type: input.type,
            name: input.name ?? "InsightForge Report",
            format: input.format,
            filters: {
              ...dates,
              granularity: input.range === "year_to_date" ? "month" : "day"
            }
          },
          signal
        });
        const completed = await pollUntil(
          async (pollSignal) =>
            (
              await client.request<Backend.ReportView>(
                `/reports/${response.data.id}`,
                {
                  organizationId,
                  signal: pollSignal
                }
              )
            ).data,
          {
            signal,
            isComplete: (report) => terminalReportStatuses.has(report.status),
            isFailed: (report) =>
              report.status === "failed" || report.status === "expired"
          }
        );
        if (completed.status !== "ready") {
          throw operationFailed(
            "Report generation failed",
            "The report artifact was not generated successfully.",
            "report_generation_failed"
          );
        }
        return mapReport(completed);
      },
      async download(organizationId, reportId, signal) {
        const artifact = await client.download(
          `/reports/${reportId}/download`,
          {
            organizationId,
            signal
          }
        );
        return {
          filename: artifact.filename ?? `insightforge-report-${reportId}`,
          mime_type: artifact.contentType.startsWith("text/csv")
            ? "text/csv"
            : "application/json",
          content: await artifact.blob.text()
        };
      }
    }
  };
}
