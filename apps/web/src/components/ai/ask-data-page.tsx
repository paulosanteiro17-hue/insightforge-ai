"use client";

import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bot,
  CheckCircle2,
  CornerDownLeft,
  DatabaseZap,
  ShieldCheck,
  Sparkles,
  UserRound
} from "lucide-react";
import { useRef, useState, type FormEvent } from "react";
import { PageHeader } from "@/components/data/page-header";
import { RangeFilter } from "@/components/dashboard/range-filter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState, LoadingBlock } from "@/components/ui/states";
import {
  ApiProblemError,
  type AskAnswer,
  type OrganizationSummary
} from "@/lib/api/contracts";
import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";
import { insightForgeApi } from "@runtime-api";
import { parseAnalyticsRange } from "@/lib/url-state";

export function AnswerPanel({ answer }: { answer: AskAnswer }) {
  const blocked = answer.status === "blocked";
  const unsupported = answer.status === "unsupported";
  const insufficient = answer.status === "insufficient_data";
  return (
    <div className="space-y-4" aria-live="polite">
      <div className="flex items-start gap-3">
        <span className="bg-ink-950 grid size-9 shrink-0 place-items-center rounded-xl text-white">
          <Bot className="size-4" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-ink-950 text-sm font-bold">
              InsightForge Assistant
            </p>
            <Badge
              className={cn(
                blocked
                  ? "border-coral-500/20 bg-coral-50 text-coral-700"
                  : unsupported
                    ? "border-amber-500/20 bg-amber-50 text-amber-700"
                    : insufficient
                      ? "border-amber-500/20 bg-amber-50 text-amber-700"
                      : "border-teal-500/20 bg-teal-50 text-teal-700"
              )}
            >
              {blocked
                ? "Safety blocked"
                : unsupported
                  ? "Unsupported intent"
                  : insufficient
                    ? "Insufficient data"
                    : "Grounded answer"}
            </Badge>
          </div>
          <p className="text-ink-700 mt-3 text-sm leading-7">{answer.answer}</p>
        </div>
      </div>
      {answer.citations.length ? (
        <div className="ml-0 grid gap-3 sm:ml-12 sm:grid-cols-2">
          {answer.citations.map((citation) => (
            <Card key={citation.metric ?? citation.id} className="p-3.5">
              <div className="flex items-start justify-between gap-2">
                <p className="text-ink-500 text-xs">
                  {citation.label ?? citation.metric_label}
                </p>
                <DatabaseZap
                  className="size-3.5 text-teal-600"
                  aria-hidden="true"
                />
              </div>
              <p className="text-ink-950 mt-1.5 text-lg font-bold">
                {citation.formatted_value ??
                  (typeof citation.value === "number"
                    ? citation.value.toLocaleString("en-US")
                    : citation.value)}
              </p>
              {citation.comparison ? (
                <p className="mt-1 text-[10px] font-semibold text-teal-700">
                  {citation.comparison}
                </p>
              ) : null}
              <p className="text-ink-400 mt-2 text-[9px]">
                {citation.unit ? `${citation.unit} · ` : ""}
                {citation.source.replace("_", " ")}
                {citation.period_label ? ` · ${citation.period_label}` : ""}
              </p>
            </Card>
          ))}
        </div>
      ) : null}
      {answer.suggested_follow_ups.length ? (
        <div className="ml-0 sm:ml-12">
          <p className="text-ink-400 text-[10px] font-bold uppercase">
            Try next
          </p>
          <ul className="mt-2 space-y-1">
            {answer.suggested_follow_ups.map((followUp) => (
              <li key={followUp} className="text-ink-600 text-xs">
                • {followUp}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

export function AskDataPage({
  organization
}: {
  organization: OrganizationSummary;
}) {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [question, setQuestion] = useState("");
  const [activeAnswer, setActiveAnswer] = useState<AskAnswer | null>(null);
  const range = parseAnalyticsRange(searchParams.get("range"));
  const capabilitiesQuery = useQuery({
    queryKey: ["organization", organization.id, "ask-data", "capabilities"],
    queryFn: ({ signal }) =>
      insightForgeApi.askData.getCapabilities(organization.id, signal)
  });
  const historyQuery = useQuery({
    queryKey: ["organization", organization.id, "ask-data", "history"],
    queryFn: ({ signal }) =>
      insightForgeApi.askData.history(organization.id, signal)
  });
  const askMutation = useMutation({
    mutationFn: (submittedQuestion: string) =>
      insightForgeApi.askData.ask(organization.id, {
        question: submittedQuestion,
        range
      }),
    onSuccess: async (answer) => {
      setActiveAnswer(answer);
      setQuestion("");
      await queryClient.invalidateQueries({
        queryKey: ["organization", organization.id, "ask-data", "history"]
      });
    }
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = question.trim();
    if (value) askMutation.mutate(value);
  }
  function chooseExample(example: string) {
    setQuestion(example);
    textareaRef.current?.focus();
  }

  return (
    <div>
      <PageHeader
        eyebrow="Controlled analytics assistant"
        title="Ask Your Data"
        description={`Ask approved business questions about ${organization.name}. Every answer maps to allowlisted analytics and cites the metrics it used.`}
        badge="No text-to-SQL"
        actions={<RangeFilter value={range} />}
      />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(310px,0.65fr)]">
        <Card className="overflow-hidden">
          <div className="border-ink-100 min-h-[430px] border-b p-4 sm:p-6">
            <div className="flex items-start gap-3">
              <span className="bg-ink-100 text-ink-600 grid size-9 shrink-0 place-items-center rounded-xl">
                <UserRound className="size-4" aria-hidden="true" />
              </span>
              <div>
                <p className="text-ink-950 text-sm font-bold">You</p>
                <p className="text-ink-500 mt-2 text-sm">
                  {activeAnswer?.question ??
                    "Choose an example or ask a supported business question below."}
                </p>
              </div>
            </div>
            <div className="border-ink-100 my-6 border-t" />
            {askMutation.isPending ? (
              <div
                role="status"
                aria-label="Analyzing question"
                className="space-y-3"
              >
                <LoadingBlock className="h-5 w-44" />
                <LoadingBlock className="h-20 w-full" />
                <LoadingBlock className="h-24 w-3/4" />
              </div>
            ) : null}
            {askMutation.isError ? (
              <ErrorState
                title="Question could not be answered"
                message={
                  askMutation.error instanceof ApiProblemError
                    ? askMutation.error.problem.detail
                    : "The controlled analytics request failed."
                }
                onRetry={() =>
                  question.trim() && askMutation.mutate(question.trim())
                }
              />
            ) : null}
            {!askMutation.isPending && !askMutation.isError && activeAnswer ? (
              <AnswerPanel answer={activeAnswer} />
            ) : null}
            {!askMutation.isPending && !activeAnswer ? (
              <div className="grid min-h-56 place-items-center text-center">
                <div>
                  <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-teal-50 text-teal-700">
                    <Sparkles className="size-5" aria-hidden="true" />
                  </span>
                  <h2 className="text-ink-950 mt-4 text-lg font-bold">
                    Grounded answers, not database guesses
                  </h2>
                  <p className="text-ink-500 mt-2 max-w-md text-sm leading-6">
                    The assistant selects a supported analytical intent,
                    calculates aggregate context, and returns evidence with
                    every answer.
                  </p>
                </div>
              </div>
            ) : null}
          </div>
          <form onSubmit={submit} className="p-4 sm:p-5">
            <label
              htmlFor="ask-question"
              className="text-ink-700 text-xs font-semibold"
            >
              Ask a business question
            </label>
            <div className="border-ink-200 mt-2 rounded-xl border bg-white p-2 focus-within:border-teal-500 focus-within:ring-3 focus-within:ring-teal-500/10">
              <textarea
                ref={textareaRef}
                id="ask-question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={3}
                maxLength={240}
                placeholder="For example: Did revenue decline from the previous period?"
                className="text-ink-900 placeholder:text-ink-400 w-full resize-none border-0 bg-transparent px-2 py-1 text-sm leading-6 outline-none"
              />
              <div className="flex items-center justify-between gap-3">
                <span className="text-ink-400 px-2 text-[10px]">
                  {question.length}/240 · Controlled intents only
                </span>
                <Button
                  type="submit"
                  size="sm"
                  disabled={!question.trim() || askMutation.isPending}
                >
                  Ask <CornerDownLeft className="size-3.5" aria-hidden="true" />
                </Button>
              </div>
            </div>
          </form>
        </Card>
        <div className="space-y-6">
          <Card className="p-5">
            <div className="flex items-center gap-2">
              <ShieldCheck
                className="size-5 text-teal-600"
                aria-hidden="true"
              />
              <h2 className="text-ink-950 font-bold">Safe by design</h2>
            </div>
            <p className="text-ink-600 mt-3 text-xs leading-5">
              {capabilitiesQuery.data?.safety_note ??
                "Loading assistant safety policy…"}
            </p>
            <ul className="text-ink-600 mt-4 space-y-2 text-xs">
              <li className="flex gap-2">
                <CheckCircle2
                  className="mt-0.5 size-3.5 shrink-0 text-teal-600"
                  aria-hidden="true"
                />{" "}
                Tenant-scoped aggregate tools
              </li>
              <li className="flex gap-2">
                <CheckCircle2
                  className="mt-0.5 size-3.5 shrink-0 text-teal-600"
                  aria-hidden="true"
                />{" "}
                No arbitrary SQL execution
              </li>
              <li className="flex gap-2">
                <CheckCircle2
                  className="mt-0.5 size-3.5 shrink-0 text-teal-600"
                  aria-hidden="true"
                />{" "}
                Metric citations in every supported answer
              </li>
            </ul>
          </Card>
          <Card className="p-5">
            <h2 className="text-ink-950 font-bold">Example questions</h2>
            <div className="mt-3 space-y-2">
              {capabilitiesQuery.data?.capabilities.map((capability) => (
                <button
                  key={capability.intent}
                  type="button"
                  onClick={() =>
                    chooseExample(
                      capability.example ?? capability.example_question ?? ""
                    )
                  }
                  className="border-ink-100 text-ink-700 w-full rounded-xl border p-3 text-left text-xs leading-5 transition-colors hover:border-teal-300 hover:bg-teal-50/50"
                >
                  <strong className="text-ink-900 block">
                    {capability.label}
                  </strong>
                  {capability.example ?? capability.example_question}
                </button>
              ))}
            </div>
          </Card>
          {historyQuery.data?.length ? (
            <Card className="p-5">
              <h2 className="text-ink-950 font-bold">Recent questions</h2>
              <div className="mt-3 space-y-2">
                {historyQuery.data.slice(0, 4).map((answer) => (
                  <button
                    key={answer.id}
                    type="button"
                    onClick={() => setActiveAnswer(answer)}
                    className="hover:bg-ink-50 w-full rounded-xl px-2 py-2 text-left"
                  >
                    <span className="text-ink-700 block truncate text-xs font-medium">
                      {answer.question}
                    </span>
                    <span className="text-ink-400 mt-1 block text-[9px]">
                      {formatDateTime(answer.created_at)} · {answer.status}
                    </span>
                  </button>
                ))}
              </div>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
