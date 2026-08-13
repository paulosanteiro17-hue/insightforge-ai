"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Check,
  Gauge,
  LoaderCircle,
  ShieldCheck,
  Sparkles
} from "lucide-react";
import { useState } from "react";
import { getApiErrorMessage } from "@/components/administration/admin-utils";
import { ListSkeleton } from "@/components/data/list-states";
import { PageHeader } from "@/components/data/page-header";
import { StatusBadge } from "@/components/data/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/states";
import type {
  BillingInvoice,
  BillingPlan,
  BillingPlanId,
  BillingUsageMetric,
  OrganizationSummary
} from "@/lib/api/contracts";
import { cn } from "@/lib/cn";
import { formatLongDate, formatMoney } from "@/lib/format";
import { insightForgeApi } from "@runtime-api";

type Feedback = { tone: "success" | "error"; message: string };

export function BillingPage({
  organization
}: {
  organization: OrganizationSummary;
}) {
  const queryClient = useQueryClient();
  const queryKey = ["organization", organization.id, "billing"];
  const billingQuery = useQuery({
    queryKey,
    queryFn: ({ signal }) =>
      insightForgeApi.billing.getOverview(organization.id, signal)
  });
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const planMutation = useMutation({
    mutationFn: (planId: BillingPlanId) =>
      insightForgeApi.billing.changePlan(organization.id, planId),
    onSuccess: async (result) => {
      setFeedback({ tone: "success", message: result.feedback });
      await queryClient.invalidateQueries({ queryKey });
    },
    onError: (error) =>
      setFeedback({
        tone: "error",
        message: getApiErrorMessage(
          error,
          "The simulated plan could not be changed."
        )
      })
  });

  if (billingQuery.isPending) return <ListSkeleton />;
  if (billingQuery.isError) {
    return (
      <ErrorState
        title="Billing could not be loaded"
        message={getApiErrorMessage(
          billingQuery.error,
          "Plan and usage details are temporarily unavailable."
        )}
        onRetry={() => void billingQuery.refetch()}
      />
    );
  }

  const billing = billingQuery.data;
  const currentPlan =
    billing.plans.find((plan) => plan.id === billing.subscription.plan) ??
    billing.plans[0]!;

  return (
    <div>
      <PageHeader
        eyebrow="Plan and capacity"
        title="Billing"
        description={`Review the simulated plan, capacity, and invoice records for ${organization.name}. This workspace never opens a checkout or collects payment.`}
        badge="No-charge demo"
      />

      <div
        className="mb-5 flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900"
        role="note"
      >
        <ShieldCheck className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
        <div>
          <p className="text-sm font-bold">Billing is safely simulated</p>
          <p className="mt-1 text-xs leading-5">{billing.demo_notice}</p>
        </div>
      </div>

      {feedback ? (
        <div
          role={feedback.tone === "error" ? "alert" : "status"}
          className={cn(
            "mb-5 rounded-xl border px-4 py-3 text-sm font-medium",
            feedback.tone === "success"
              ? "border-teal-200 bg-teal-50 text-teal-800"
              : "border-coral-200 bg-coral-50 text-coral-800"
          )}
        >
          {feedback.message}
        </div>
      ) : null}

      <Card className="mb-6 overflow-hidden">
        <div className="grid lg:grid-cols-[1fr_1.1fr]">
          <div className="bg-ink-950 p-6 text-white sm:p-7">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="border-teal-300/20 bg-teal-300/10 text-teal-200">
                Current demo plan
              </Badge>
              <StatusBadge
                status={billing.subscription.status}
                className="border-white/15 bg-white/10 text-white"
              />
            </div>
            <h2 className="mt-5 text-3xl font-bold">{currentPlan.name}</h2>
            <p className="text-ink-300 mt-2 text-sm leading-6">
              {currentPlan.description}
            </p>
            <div className="mt-6 flex items-end gap-2">
              <span className="text-4xl font-bold">
                {formatMoney(currentPlan.monthly_price_minor)}
              </span>
              <span className="text-ink-400 pb-1 text-sm">per month</span>
            </div>
            <p className="text-ink-400 mt-4 text-xs leading-5">
              Demo period ends{" "}
              {billing.subscription.current_period_end
                ? formatLongDate(billing.subscription.current_period_end)
                : "when the current demo cycle closes"}
              . It does not renew and no payment method exists.
            </p>
          </div>
          <div className="p-5 sm:p-7">
            <div className="flex items-center gap-2">
              <Gauge className="size-5 text-teal-700" aria-hidden="true" />
              <h2 className="text-ink-950 text-lg font-bold">Current usage</h2>
            </div>
            <div className="mt-5 space-y-5">
              {billing.usage.map((usage) => (
                <UsageMeter key={usage.id} usage={usage} />
              ))}
            </div>
          </div>
        </div>
      </Card>

      <section aria-labelledby="plans-heading" className="mb-7">
        <div className="mb-4">
          <h2 id="plans-heading" className="text-ink-950 text-xl font-bold">
            Compare plans
          </h2>
          <p className="text-ink-500 mt-1 text-sm">
            Selecting a plan changes only local demo state and always charges
            $0.
          </p>
        </div>
        <div className="grid gap-4 xl:grid-cols-3">
          {billing.plans.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              current={plan.id === billing.subscription.plan}
              canManage={billing.can_manage_billing}
              pending={planMutation.isPending}
              onSelect={() => {
                setFeedback(null);
                planMutation.mutate(plan.id);
              }}
            />
          ))}
        </div>
      </section>

      <section aria-labelledby="invoice-heading">
        <div className="mb-4">
          <h2 id="invoice-heading" className="text-ink-950 text-xl font-bold">
            Invoice records
          </h2>
          <p className="text-ink-500 mt-1 text-sm">
            Historical demo records document that payment was not attempted.
          </p>
        </div>
        {billing.invoices.length ? (
          <InvoicesTable invoices={billing.invoices} />
        ) : (
          <EmptyState
            title="No invoice records"
            message="Demo plan transitions create no provider invoices or payment receipts."
          />
        )}
      </section>
    </div>
  );
}

function UsageMeter({ usage }: { usage: BillingUsageMetric }) {
  const unlimited = usage.limit <= 0;
  const ratio = unlimited ? 0.08 : Math.min(1, usage.used / usage.limit);
  const formattedUsed = usage.used.toLocaleString("en-US");
  const formattedLimit = unlimited
    ? "Unlimited"
    : usage.limit.toLocaleString("en-US");
  return (
    <div>
      <div className="flex items-end justify-between gap-3">
        <p className="text-ink-700 text-sm font-semibold">{usage.label}</p>
        <p className="text-ink-500 text-xs">
          <span className="text-ink-900 font-bold">{formattedUsed}</span> /{" "}
          {formattedLimit}
        </p>
      </div>
      <div
        className="bg-ink-100 mt-2 h-2 overflow-hidden rounded-full"
        aria-hidden="true"
      >
        <div
          className={cn(
            "h-full rounded-full",
            ratio >= 0.9 ? "bg-coral-500" : "bg-teal-500"
          )}
          style={{ width: `${Math.max(4, ratio * 100)}%` }}
        />
      </div>
      <span className="sr-only">
        {formattedUsed} of {formattedLimit} {usage.unit} used.
      </span>
    </div>
  );
}

function PlanCard({
  plan,
  current,
  canManage,
  pending,
  onSelect
}: {
  plan: BillingPlan;
  current: boolean;
  canManage: boolean;
  pending: boolean;
  onSelect: () => void;
}) {
  return (
    <Card
      className={cn(
        "relative flex flex-col p-5 sm:p-6",
        current && "border-teal-500 ring-2 ring-teal-500/10"
      )}
    >
      {plan.id === "pro" ? (
        <Badge className="absolute top-5 right-5 border-teal-200 bg-teal-50 text-teal-800">
          <Sparkles className="size-3" aria-hidden="true" /> Recommended
        </Badge>
      ) : null}
      <p className="text-ink-950 text-xl font-bold">{plan.name}</p>
      <p className="text-ink-600 mt-2 min-h-12 pr-20 text-sm leading-6">
        {plan.description}
      </p>
      <p className="text-ink-950 mt-5 text-3xl font-bold">
        {formatMoney(plan.monthly_price_minor)}
        <span className="text-ink-500 ml-1 text-xs font-medium">/ month</span>
      </p>
      <ul className="mt-5 flex-1 space-y-3">
        {plan.features.map((feature) => (
          <li key={feature} className="text-ink-600 flex gap-2 text-sm">
            <Check
              className="mt-0.5 size-4 shrink-0 text-teal-600"
              aria-hidden="true"
            />
            {feature}
          </li>
        ))}
      </ul>
      <Button
        className="mt-6 w-full"
        variant={current ? "outline" : "primary"}
        disabled={current || !canManage || pending}
        onClick={onSelect}
      >
        {pending && !current ? (
          <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
        ) : null}
        {current ? "Current demo plan" : `Use ${plan.name} in demo`}
      </Button>
      {!canManage ? (
        <p className="text-ink-500 mt-2 text-center text-xs">
          Owner permission is required.
        </p>
      ) : null}
    </Card>
  );
}

function InvoicesTable({ invoices }: { invoices: BillingInvoice[] }) {
  return (
    <Card className="overflow-hidden">
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Demo invoice records</caption>
          <thead className="bg-ink-50/80 text-ink-500 text-[10px] font-bold tracking-[0.11em] uppercase">
            <tr>
              <th className="px-5 py-3.5">Record</th>
              <th className="px-5 py-3.5">Issued</th>
              <th className="px-5 py-3.5">Status</th>
              <th className="px-5 py-3.5 text-right">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-ink-100 divide-y">
            {invoices.map((invoice) => (
              <tr key={invoice.id}>
                <td className="px-5 py-4">
                  <p className="text-ink-950 font-semibold">{invoice.number}</p>
                </td>
                <td className="text-ink-600 px-5 py-4 text-xs">
                  {formatLongDate(invoice.issued_at)}
                </td>
                <td className="px-5 py-4">
                  <StatusBadge status={invoice.status} />
                </td>
                <td className="text-ink-950 px-5 py-4 text-right font-semibold">
                  {formatMoney(invoice.amount_minor)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="divide-ink-100 divide-y md:hidden">
        {invoices.map((invoice) => (
          <article key={invoice.id} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-ink-950 text-sm font-bold">
                  {invoice.number}
                </p>
                <p className="text-ink-500 mt-1 text-xs">
                  {formatLongDate(invoice.issued_at)}
                </p>
              </div>
              <StatusBadge status={invoice.status} />
            </div>
            <div className="mt-4 flex items-center justify-between gap-3">
              <p className="text-ink-950 font-bold">
                {formatMoney(invoice.amount_minor)}
              </p>
              <span className="text-ink-500 text-xs">Demo billing record</span>
            </div>
          </article>
        ))}
      </div>
    </Card>
  );
}
