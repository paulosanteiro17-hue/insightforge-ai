import { describe, expect, it, vi } from "vitest";
import type * as Backend from "@/lib/api/backend-contracts";
import { ApiHttpClient } from "@/lib/api/http-client";
import { createLiveIntelligenceApi } from "@/lib/api/live-intelligence-adapter";

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

function collection<T>(data: T[]) {
  return {
    data,
    meta: {
      pagination: {
        page: 1,
        page_size: 100,
        total: data.length,
        total_pages: 1,
        has_next: false,
        has_previous: false
      },
      filters: {}
    }
  };
}

const insight: Backend.InsightView = {
  id: "insight-1",
  category: "growth",
  severity: "medium",
  title: "Revenue increased",
  description: "Revenue increased against the previous equivalent period.",
  supporting_metrics: [
    {
      key: "revenue_minor",
      value: 8180000,
      comparison_value: 6900000,
      unit: "minor_currency"
    }
  ],
  provider: "openai",
  model: "gpt-5.6-sol",
  prompt_version: "insights.v1",
  generation_mode: "provider",
  status: "active",
  source_revision: 4,
  period_start: "2026-07-14",
  period_end: "2026-08-13",
  generated_at: "2026-08-13T12:00:00Z",
  expires_at: null,
  superseded_at: null
};

describe("live intelligence adapter", () => {
  it("polls insight generation and maps persisted evidence", async () => {
    const fetcher = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/auth/csrf-token")) {
          return jsonResponse({ data: { csrf_token: "csrf-token" } });
        }
        if (url.includes("/insights/generation-jobs/job-1")) {
          return jsonResponse({
            data: {
              id: "job-1",
              job_type: "generate_insights",
              status: "succeeded",
              progress: {},
              result: { insight_count: 1 },
              error_code: null,
              created_at: "2026-08-13T12:00:00Z",
              started_at: "2026-08-13T12:00:01Z",
              completed_at: "2026-08-13T12:00:02Z"
            }
          });
        }
        if (url.endsWith("/insights/generation-jobs?range=30d")) {
          const headers = new Headers(init?.headers);
          expect(init?.method).toBe("POST");
          expect(headers.get("X-Organization-ID")).toBe("org-1");
          expect(headers.get("X-CSRF-Token")).toBe("csrf-token");
          expect(headers.get("Idempotency-Key")).toBeTruthy();
          return jsonResponse(
            {
              data: {
                id: "job-1",
                job_type: "generate_insights",
                status: "queued",
                progress: {},
                result: null,
                error_code: null,
                created_at: "2026-08-13T12:00:00Z",
                started_at: null,
                completed_at: null
              }
            },
            202
          );
        }
        if (url.endsWith("/insights?page=1&page_size=100")) {
          return jsonResponse(collection([insight]));
        }
        throw new Error(`Unexpected request: ${url}`);
      }
    );
    const client = new ApiHttpClient({
      baseUrl: "http://api.test/api/v1",
      fetch: fetcher as unknown as typeof fetch,
      origin: "http://web.test"
    });

    const result = await createLiveIntelligenceApi(client).insights.regenerate(
      "org-1",
      "30d"
    );

    expect(result.status).toBe("succeeded");
    expect(result.items).toHaveLength(1);
    expect(result.items[0]).toMatchObject({
      provider: "openai",
      generation_mode: "provider",
      period_start: "2026-07-14"
    });
    expect(result.items[0]?.supporting_metrics[0]).toEqual(
      insight.supporting_metrics[0]
    );
  });

  it("sends a controlled question with tenant, range, CSRF, and idempotency", async () => {
    const fetcher = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/auth/csrf-token")) {
          return jsonResponse({ data: { csrf_token: "csrf-token" } });
        }
        if (url.endsWith("/ask-data/answers?range=90d")) {
          const headers = new Headers(init?.headers);
          expect(init?.method).toBe("POST");
          expect(headers.get("X-Organization-ID")).toBe("org-9");
          expect(headers.get("X-CSRF-Token")).toBe("csrf-token");
          expect(headers.get("Idempotency-Key")).toBeTruthy();
          expect(JSON.parse(String(init?.body))).toEqual({
            question: "Which product generated the most revenue?"
          });
          return jsonResponse(
            {
              data: {
                id: "answer-1",
                question_redacted: "Which product generated the most revenue?",
                intent: "top_product",
                parameters: { limit: 1 },
                answer: "Atlas generated the most eligible revenue.",
                answer_status: "answered",
                applied_range: {
                  start: "2026-05-15T00:00:00Z",
                  end: "2026-08-13T00:00:00Z"
                },
                confidence: 0.94,
                follow_ups: ["How many units did it sell?"],
                citations: [
                  {
                    metric: "product_revenue_minor",
                    label: "Atlas revenue",
                    value: 1842000,
                    unit: "minor_currency",
                    source: "tenant_analytics"
                  }
                ],
                provider: "deterministic",
                created_at: "2026-08-13T12:00:00Z"
              }
            },
            201
          );
        }
        throw new Error(`Unexpected request: ${url}`);
      }
    );
    const client = new ApiHttpClient({
      baseUrl: "http://api.test/api/v1",
      fetch: fetcher as unknown as typeof fetch,
      origin: "http://web.test"
    });

    const answer = await createLiveIntelligenceApi(client).askData.ask(
      "org-9",
      {
        question: "Which product generated the most revenue?",
        range: "90d"
      }
    );

    expect(answer.status).toBe("answered");
    expect(answer.question).toBe("Which product generated the most revenue?");
    expect(answer.citations[0]).toMatchObject({
      metric: "product_revenue_minor",
      source: "tenant_analytics"
    });
  });
});
