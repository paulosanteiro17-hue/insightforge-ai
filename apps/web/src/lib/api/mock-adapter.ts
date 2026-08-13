import {
  ApiProblemError,
  type AccountPreferences,
  type AnalyticsRange,
  type AskAnswer,
  type AskCitation,
  type AskIntent,
  type BillingPlanId,
  type CsvUploadInput,
  type CustomerCreateInput,
  type CustomerListItem,
  type CustomerListQuery,
  type CustomerUpdateInput,
  type InsightForgeApi,
  type OrderListItem,
  type OrderListQuery,
  type PaginatedResponse,
  type ProductListItem,
  type ProductListQuery,
  type ProductCreateInput,
  type ProductUpdateInput,
  type OrderStatus,
  type ImportKind,
  type ImportPreview,
  type ImportValidationError,
  type OnboardingSnapshot,
  type ReportRecord,
  type SettingsSnapshot,
  type SessionView,
  type SignInInput,
  type SignUpInput,
  type TeamInvitation,
  type TeamMember
} from "@/lib/api/contracts";
import {
  mockBillingInvoices,
  mockBillingPlans,
  mockBillingSubscription,
  mockBillingUsage,
  mockOnboardingSnapshot,
  mockSettingsSnapshot,
  mockTeamInvitations,
  mockTeamMembers
} from "@/lib/api/mock-account-fixtures";
import {
  createMockAnalyticsPerformance,
  createMockCustomerDetail,
  createMockOverview,
  createMockProductDetail,
  mockCustomers,
  mockOrders,
  mockOrganizations,
  mockProducts,
  mockSession
} from "@/lib/api/mock-fixtures";
import {
  createMockInsights,
  mockAskCapabilities,
  mockAskHistory,
  mockImportHistory,
  mockImportTemplates,
  mockReports,
  mockReportTemplates
} from "@/lib/api/mock-operations-fixtures";

const mockLatency = process.env.NODE_ENV === "test" ? 0 : 280;
let insightGeneration = 0;
let askSequence = mockAskHistory.length;
let reportSequence = mockReports.length;
let importSequence = mockImportHistory.length;
const askHistoryState = [...mockAskHistory];
const reportState: ReportRecord[] = mockReports.map((report) => ({
  ...report
}));
const importHistoryState = mockImportHistory.map((record) => ({ ...record }));
const pendingImports = new Map<string, ImportPreview>();
let onboardingState: OnboardingSnapshot = structuredClone(
  mockOnboardingSnapshot
);
let teamMemberState: TeamMember[] = structuredClone(mockTeamMembers);
let teamInvitationState: TeamInvitation[] =
  structuredClone(mockTeamInvitations);
let billingSubscriptionState = structuredClone(mockBillingSubscription);
let billingUsageState = structuredClone(mockBillingUsage);
let settingsState: SettingsSnapshot = structuredClone(mockSettingsSnapshot);
const initialOrganizationState = structuredClone(mockOrganizations);
const initialSessionUser = structuredClone(mockSession.user);

export function resetAccountMockState(): void {
  onboardingState = structuredClone(mockOnboardingSnapshot);
  teamMemberState = structuredClone(mockTeamMembers);
  teamInvitationState = structuredClone(mockTeamInvitations);
  billingSubscriptionState = structuredClone(mockBillingSubscription);
  billingUsageState = structuredClone(mockBillingUsage);
  settingsState = structuredClone(mockSettingsSnapshot);
  mockOrganizations.forEach((organization, index) => {
    Object.assign(organization, initialOrganizationState[index]);
  });
  Object.assign(mockSession.user, initialSessionUser);
}

const rangeLabels: Record<AnalyticsRange, string> = {
  "7d": "Last 7 days",
  "30d": "Last 30 days",
  "90d": "Last 90 days",
  year_to_date: "Year to date"
};

async function waitForMock(signal?: AbortSignal): Promise<void> {
  if (signal?.aborted) {
    throw new DOMException("The request was cancelled.", "AbortError");
  }

  await new Promise<void>((resolve, reject) => {
    const handleAbort = () => {
      globalThis.clearTimeout(timeout);
      reject(new DOMException("The request was cancelled.", "AbortError"));
    };
    const timeout = globalThis.setTimeout(() => {
      signal?.removeEventListener("abort", handleAbort);
      resolve();
    }, mockLatency);

    signal?.addEventListener("abort", handleAbort, { once: true });
  });
}

function withIdentity(
  session: SessionView,
  displayName: string,
  email: string
): SessionView {
  return {
    ...session,
    user: {
      ...session.user,
      display_name: displayName,
      email
    }
  };
}

function assertOrganization(organizationId: string): void {
  if (
    !mockOrganizations.some(
      (organization) => organization.id === organizationId
    )
  ) {
    throw new ApiProblemError({
      title: "Workspace unavailable",
      detail: "The requested workspace could not be found.",
      status: 404,
      code: "resource_not_found",
      request_id: "req-demo-workspace-404"
    });
  }
}

function notFound(resource: string): ApiProblemError {
  return new ApiProblemError({
    title: `${resource} not found`,
    detail: `The requested ${resource.toLowerCase()} is unavailable in this workspace.`,
    status: 404,
    code: "resource_not_found",
    request_id: `req-demo-${resource.toLowerCase()}-404`
  });
}

function accountProblem(
  title: string,
  detail: string,
  status: number,
  code: string
): ApiProblemError {
  return new ApiProblemError({
    title,
    detail,
    status,
    code,
    request_id: `req-demo-${code}`
  });
}

function demoPolicyProblem(action: string): ApiProblemError {
  return accountProblem(
    "Action unavailable in demo mode",
    `${action} is disabled because this isolated workspace cannot contact external services or change protected account data.`,
    403,
    "demo_policy_restriction"
  );
}

function organizationFor(organizationId: string) {
  const organization = mockOrganizations.find(
    (item) => item.id === organizationId
  );
  if (!organization) throw notFound("Workspace");
  return organization;
}

function assertCanManageTeam(organizationId: string): void {
  const organization = organizationFor(organizationId);
  if (organization.role === "member") {
    throw accountProblem(
      "Permission required",
      "Only workspace owners and admins can manage team members.",
      403,
      "insufficient_permission"
    );
  }
}

function assertOwner(organizationId: string, action: string): void {
  const organization = organizationFor(organizationId);
  if (organization.role !== "owner") {
    throw accountProblem(
      "Owner permission required",
      `Only a workspace owner can ${action}.`,
      403,
      "owner_permission_required"
    );
  }
}

function cloneAccountValue<T>(value: T): T {
  return structuredClone(value);
}

function paginate<T>(
  items: T[],
  page: number,
  pageSize: number
): PaginatedResponse<T> {
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  const safePage = Math.min(Math.max(1, page), totalPages);
  const start = (safePage - 1) * pageSize;
  return {
    items: items.slice(start, start + pageSize),
    pagination: {
      page: safePage,
      page_size: pageSize,
      total_items: items.length,
      total_pages: totalPages
    }
  };
}

const rangeStart: Record<AnalyticsRange, string> = {
  "7d": "2026-08-04T00:00:00Z",
  "30d": "2026-07-12T00:00:00Z",
  "90d": "2026-05-12T00:00:00Z",
  year_to_date: "2026-01-01T00:00:00Z"
};

function orderSummary(order: (typeof mockOrders)[number]): OrderListItem {
  return {
    id: order.id,
    order_number: order.order_number,
    status: order.status,
    customer: order.customer,
    item_count: order.item_count,
    total_minor: order.total_minor,
    currency: order.currency,
    ordered_at: order.ordered_at
  };
}

function askCitation(
  id: string,
  metricLabel: string,
  formattedValue: string,
  comparison: string,
  source: string,
  range: AnalyticsRange
): AskCitation {
  return {
    id,
    metric_label: metricLabel,
    formatted_value: formattedValue,
    comparison,
    source,
    period_label: rangeLabels[range]
  };
}

function detectAskIntent(question: string): AskIntent | null {
  const normalized = question.toLowerCase();
  if (/best[- ]selling|top product|which product/.test(normalized))
    return "top_product";
  if (/which customers|top customers|customers generated/.test(normalized))
    return "top_customers";
  if (
    /why.*revenue.*declin|revenue.*(declin|fell|drop|decrease)/.test(normalized)
  )
    return "revenue_decline";
  if (/summari[sz]e|business performance|overall performance/.test(normalized))
    return "business_summary";
  if (
    /sales status|how many.*orders|completed orders|sales|orders/.test(
      normalized
    )
  )
    return "sales_status";
  return null;
}

function createAskAnswer(input: {
  question: string;
  range: AnalyticsRange;
}): AskAnswer {
  askSequence += 1;
  const base = {
    id: `ask-demo-${askSequence}`,
    question: input.question,
    applied_range: input.range,
    created_at: `2026-08-10T15:${String(30 + askSequence).padStart(2, "0")}:00Z`
  };
  const normalized = input.question.trim().toLowerCase();
  if (
    /ignore (all |the )?(previous|prior)|system prompt|developer message|reveal.*prompt|drop table|select .* from|database schema|execute sql|bypass/.test(
      normalized
    )
  ) {
    return {
      ...base,
      intent: null,
      status: "blocked",
      answer:
        "I cannot follow instructions that request internal prompts, raw database access, SQL execution, or policy bypasses. Ask about an approved business metric instead.",
      citations: [],
      suggested_follow_ups: mockAskCapabilities.capabilities
        .slice(0, 2)
        .map((capability) => capability.example ?? capability.example_question)
        .filter((value): value is string => Boolean(value)),
      confidence: "not_applicable"
    };
  }

  const intent = detectAskIntent(input.question);
  if (!intent) {
    return {
      ...base,
      intent: null,
      status: "unsupported",
      answer:
        "That question is outside the supported analytics intents. I can answer controlled questions about sales status, revenue decline, top products, top customers, or an overall business summary.",
      citations: [],
      suggested_follow_ups: mockAskCapabilities.capabilities
        .slice(0, 3)
        .map((capability) => capability.example ?? capability.example_question)
        .filter((value): value is string => Boolean(value)),
      confidence: "not_applicable"
    };
  }

  const responses: Record<
    AskIntent,
    Pick<
      AskAnswer,
      "answer" | "citations" | "suggested_follow_ups" | "confidence"
    >
  > = {
    sales_status: {
      answer:
        "Sales are performing ahead of the comparison period. Net revenue reached $81,800 across 304 orders, while average order value eased to $269 as discounted service bundles increased.",
      citations: [
        askCitation(
          "ask-revenue",
          "Net revenue",
          "$81,800",
          "+18.4% vs previous period",
          "Analytics overview · metric v1",
          input.range
        ),
        askCitation(
          "ask-orders",
          "Orders",
          "304",
          "+5.4% vs previous period",
          "Orders aggregate · metric v1",
          input.range
        ),
        askCitation(
          "ask-aov",
          "Average order value",
          "$269",
          "−2.4% vs previous period",
          "Eligible orders · metric v1",
          input.range
        )
      ],
      suggested_follow_ups: [
        "Did revenue decline from the previous period?",
        "Which product generated the most revenue?"
      ],
      confidence: "high"
    },
    top_product: {
      answer:
        "Atlas Operations Suite is the top product by eligible revenue, generating $18,420 from 96 units. Its revenue increased 21.4% from the previous period.",
      citations: [
        askCitation(
          "ask-atlas",
          "Atlas revenue",
          "$18,420",
          "+21.4% vs previous period",
          "Product performance · metric v1",
          input.range
        ),
        askCitation(
          "ask-atlas-units",
          "Atlas units sold",
          "96",
          "Revenue rank #1",
          "Product ranking · metric v1",
          input.range
        )
      ],
      suggested_follow_ups: [
        "How many completed orders are there?",
        "Give me a business performance summary."
      ],
      confidence: "high"
    },
    revenue_decline: {
      answer:
        "Revenue did not decline in the selected period. It increased primarily because Atlas Operations Suite and Growth Advisory Retainer exceeded their prior-period baselines, partly offset by lower average order value.",
      citations: [
        askCitation(
          "ask-revenue-change",
          "Net revenue",
          "$81,800",
          "+18.4% vs previous period",
          "Analytics overview · metric v1",
          input.range
        ),
        askCitation(
          "ask-completed",
          "Completed orders",
          "184",
          "+7.6% vs previous period",
          "Order status aggregate · metric v1",
          input.range
        )
      ],
      suggested_follow_ups: [
        "Which product generated the most revenue?",
        "Who are the top 5 customers?"
      ],
      confidence: "high"
    },
    top_customers: {
      answer:
        "Northwood Labs, Cedar & Coast Studio, and Rivermark Supply are the highest-value relationships in the current customer aggregate. Together they represent $57,060 in lifetime spend.",
      citations: [
        askCitation(
          "ask-northwood",
          "Northwood Labs lifetime spend",
          "$22,120",
          "14 orders",
          "Customer lifetime metrics · v1",
          input.range
        ),
        askCitation(
          "ask-cedar",
          "Cedar & Coast lifetime spend",
          "$18,460",
          "12 orders",
          "Customer lifetime metrics · v1",
          input.range
        ),
        askCitation(
          "ask-rivermark",
          "Rivermark lifetime spend",
          "$16,480",
          "11 orders",
          "Customer lifetime metrics · v1",
          input.range
        )
      ],
      suggested_follow_ups: [
        "How many completed orders are there?",
        "Give me a business performance summary."
      ],
      confidence: "high"
    },
    business_summary: {
      answer:
        "Business momentum is healthy: revenue, orders, and new customers are growing, Atlas Operations Suite leads product performance, and repeat purchase rate improved. The clearest risk is modest average-order-value pressure from discounted service bundles.",
      citations: [
        askCitation(
          "ask-summary-revenue",
          "Net revenue",
          "$81,800",
          "+18.4% vs previous period",
          "Analytics overview · metric v1",
          input.range
        ),
        askCitation(
          "ask-summary-customers",
          "New customers",
          "142",
          "+8.1% vs previous period",
          "Customer analytics · metric v1",
          input.range
        ),
        askCitation(
          "ask-summary-repeat",
          "Repeat purchase rate",
          "38.4%",
          "+3.2 pts vs previous period",
          "Customer analytics · metric v1",
          input.range
        )
      ],
      suggested_follow_ups: [
        "Did revenue decline from the previous period?",
        "Who are the top 5 customers?"
      ],
      confidence: "high"
    }
  };

  return {
    ...base,
    intent,
    status: "answered",
    ...responses[intent]
  };
}

function parseCsvLine(line: string): string[] | null {
  const values: string[] = [];
  let value = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];
    if (character === '"') {
      if (quoted && line[index + 1] === '"') {
        value += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (character === "," && !quoted) {
      values.push(value.trim());
      value = "";
    } else {
      value += character;
    }
  }
  if (quoted) return null;
  values.push(value.trim());
  return values;
}

function validateCsv(input: CsvUploadInput): ImportPreview {
  importSequence += 1;
  const importId = `import-preview-${importSequence}`;
  const importTemplate = mockImportTemplates.find(
    (item) => item.kind === input.kind
  )!;
  const errors: ImportValidationError[] = [];
  const addError = (
    row: number,
    column: string,
    code: string,
    message: string,
    rejectedValue: string
  ) => {
    void rejectedValue;
    if (errors.length >= 25) return;
    errors.push({
      id: `${importId}-error-${errors.length + 1}`,
      row_number: row,
      column,
      code,
      message
    });
  };

  if (input.size_bytes > 10 * 1024 * 1024) {
    addError(
      0,
      "file",
      "upload_too_large",
      "CSV files must be 10 MiB or smaller.",
      input.filename
    );
  }
  if (!input.filename.toLowerCase().endsWith(".csv")) {
    addError(
      0,
      "file",
      "invalid_file_type",
      "Choose a file with the .csv extension.",
      input.filename
    );
  }
  if (input.content.includes("\0")) {
    addError(
      0,
      "file",
      "null_byte",
      "The file contains a prohibited null byte.",
      "[binary content]"
    );
  }

  const lines = input.content
    .replace(/\r\n?/g, "\n")
    .split("\n")
    .filter((line) => line.trim().length > 0);
  if (Math.max(0, lines.length - 1) > 50_000) {
    addError(
      0,
      "file",
      "row_limit_exceeded",
      "CSV files may contain at most 50,000 data rows.",
      `${lines.length - 1} rows`
    );
  }
  const parsedHeader = lines[0] ? parseCsvLine(lines[0]) : null;
  const headers = parsedHeader ?? [];
  if (
    !parsedHeader ||
    parsedHeader.join("|") !== importTemplate.headers.join("|")
  ) {
    addError(
      1,
      "headers",
      "invalid_headers",
      `Expected exact headers: ${importTemplate.headers.join(", ")}.`,
      headers.join(", ")
    );
  }

  const previewRows: Array<Record<string, string>> = [];
  const errorRowNumbers = new Set<number>();
  const allowedStatuses: Record<ImportKind, string[]> = {
    customers: ["active", "at_risk", "inactive"],
    products: ["active", "archived"],
    orders: [
      "pending",
      "paid",
      "processing",
      "completed",
      "cancelled",
      "refunded"
    ]
  };
  lines.slice(1).forEach((line, rowIndex) => {
    const rowNumber = rowIndex + 2;
    const values = parseCsvLine(line);
    if (!values || values.length !== importTemplate.headers.length) {
      addError(
        rowNumber,
        "row",
        "malformed_row",
        `Expected ${importTemplate.headers.length} columns.`,
        line
      );
      errorRowNumbers.add(rowNumber);
      return;
    }
    const row = Object.fromEntries(
      importTemplate.headers.map((header, index) => [
        header,
        values[index] ?? ""
      ])
    );
    const optionalColumns = new Set(["email", "company"]);
    for (const header of importTemplate.headers) {
      const value = row[header] ?? "";
      if (!value && !optionalColumns.has(header)) {
        addError(
          rowNumber,
          header,
          "required",
          `${header} is required.`,
          value
        );
        errorRowNumbers.add(rowNumber);
      }
      if (
        /^[=+@]/.test(value) ||
        (/^-/.test(value) && !/^\d/.test(value.slice(1)))
      ) {
        addError(
          rowNumber,
          header,
          "formula_like_value",
          "Formula-like values are not accepted.",
          value
        );
        errorRowNumbers.add(rowNumber);
        row[header] = "[blocked formula-like value]";
      }
    }
    if (row.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(row.email)) {
      addError(
        rowNumber,
        "email",
        "invalid_email",
        "Enter a valid email address.",
        row.email
      );
      errorRowNumbers.add(rowNumber);
    }
    if (row.status && !allowedStatuses[input.kind].includes(row.status)) {
      addError(
        rowNumber,
        "status",
        "invalid_status",
        `Status must be one of: ${allowedStatuses[input.kind].join(", ")}.`,
        row.status
      );
      errorRowNumbers.add(rowNumber);
    }
    if (row.quantity && !/^[1-9]\d*$/.test(row.quantity)) {
      addError(
        rowNumber,
        "quantity",
        "invalid_integer",
        "quantity must be a positive whole number.",
        row.quantity
      );
      errorRowNumbers.add(rowNumber);
    }
    for (const moneyColumn of ["unit_price", "discount", "tax"]) {
      if (row[moneyColumn] && !/^\d+\.\d{2}$/.test(row[moneyColumn])) {
        addError(
          rowNumber,
          moneyColumn,
          "invalid_money",
          `${moneyColumn} must be a non-negative decimal with exactly two minor-unit digits.`,
          row[moneyColumn]
        );
        errorRowNumbers.add(rowNumber);
      }
    }
    if (row.currency && !/^[A-Z]{3}$/.test(row.currency)) {
      addError(
        rowNumber,
        "currency",
        "invalid_currency",
        "currency must be a three-letter uppercase code.",
        row.currency
      );
      errorRowNumbers.add(rowNumber);
    }
    for (const referenceColumn of [
      "external_id",
      "sku",
      "order_number",
      "customer_external_id",
      "product_sku"
    ]) {
      if (
        row[referenceColumn] &&
        !/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(row[referenceColumn])
      ) {
        addError(
          rowNumber,
          referenceColumn,
          "invalid_reference",
          `${referenceColumn} may contain only letters, numbers, dots, underscores, and hyphens.`,
          row[referenceColumn]
        );
        errorRowNumbers.add(rowNumber);
      }
    }
    for (const dateColumn of ["acquired_at", "ordered_at"]) {
      if (
        row[dateColumn] &&
        (Number.isNaN(Date.parse(row[dateColumn])) ||
          !row[dateColumn].includes("T") ||
          !/(?:Z|[+-]\d{2}:\d{2})$/.test(row[dateColumn]))
      ) {
        addError(
          rowNumber,
          dateColumn,
          "invalid_timestamp",
          `${dateColumn} must be an ISO 8601 timestamp with a UTC offset.`,
          row[dateColumn]
        );
        errorRowNumbers.add(rowNumber);
      }
    }
    if (previewRows.length < 5) previewRows.push(row);
  });

  const totalRows = Math.max(0, lines.length - 1);
  const preview: ImportPreview = {
    import_id: importId,
    kind: input.kind,
    filename: input.filename,
    status: errors.length ? "validation_failed" : "ready",
    headers: importTemplate.headers,
    preview_rows: previewRows,
    total_rows: totalRows,
    valid_rows: Math.max(0, totalRows - errorRowNumbers.size),
    error_rows: errorRowNumbers.size || (errors.length ? 1 : 0),
    errors,
    errors_truncated: errors.length >= 25,
    duplicate_policy: "create_only"
  };
  pendingImports.set(importId, preview);
  return preview;
}

class MockInsightForgeApi implements InsightForgeApi {
  auth = {
    signIn: async (
      input: SignInInput,
      signal?: AbortSignal
    ): Promise<SessionView> => {
      await waitForMock(signal);

      if (input.email.toLowerCase() === "locked@northstar.example") {
        throw new ApiProblemError({
          title: "Sign in failed",
          detail: "Invalid email or password.",
          status: 401,
          code: "invalid_credentials",
          request_id: "req-demo-auth-401"
        });
      }

      return withIdentity(mockSession, "Jordan Blake", input.email);
    },
    signUp: async (
      input: SignUpInput,
      signal?: AbortSignal
    ): Promise<SessionView> => {
      await waitForMock(signal);
      return withIdentity(mockSession, input.display_name, input.email);
    },
    createDemoSession: async (signal?: AbortSignal): Promise<SessionView> => {
      await waitForMock(signal);
      return mockSession;
    },
    requestPasswordReset: async (_email: string, signal?: AbortSignal) => {
      void _email;
      await waitForMock(signal);
      return {
        message:
          "If an account exists for that address, password reset instructions are ready.",
        recovery_path: "/reset-password?token=mock-recovery-token"
      };
    },
    confirmPasswordReset: async (
      _token: string,
      _password: string,
      signal?: AbortSignal
    ): Promise<void> => {
      void _token;
      void _password;
      await waitForMock(signal);
    },
    signOut: async (signal?: AbortSignal): Promise<void> => {
      await waitForMock(signal);
    }
  };

  organizations = {
    list: async (signal?: AbortSignal) => {
      await waitForMock(signal);
      return mockOrganizations;
    },
    getBySlug: async (slug: string, signal?: AbortSignal) => {
      await waitForMock(signal);
      return (
        mockOrganizations.find((organization) => organization.slug === slug) ??
        null
      );
    },
    create: async (
      input: Parameters<InsightForgeApi["organizations"]["create"]>[0],
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      const slug =
        input.slug ?? input.name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
      return {
        id: `mock-organization-${mockOrganizations.length + 1}`,
        name: input.name,
        slug,
        role: "owner" as const,
        status: "active" as const,
        onboarding_state: "organization" as const,
        reporting_currency: input.reporting_currency,
        timezone: input.timezone,
        is_demo: false,
        demo_expires_at: null
      };
    }
  };

  analytics = {
    getOverview: async (
      organizationId: string,
      range: AnalyticsRange,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      return createMockOverview(organizationId, range);
    },
    getPerformance: async (
      organizationId: string,
      range: AnalyticsRange,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      return createMockAnalyticsPerformance(organizationId, range);
    },
    regenerateWeeklySummary: async (
      organizationId: string,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      return createMockOverview(organizationId, "30d").weekly_summary!;
    }
  };

  orders = {
    list: async (
      organizationId: string,
      query: OrderListQuery,
      signal?: AbortSignal
    ): Promise<PaginatedResponse<OrderListItem>> => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const normalizedSearch = query.search?.trim().toLowerCase();
      const items = mockOrders
        .filter((order) => order.ordered_at >= rangeStart[query.range])
        .filter((order) => !query.status || order.status === query.status)
        .filter(
          (order) =>
            !normalizedSearch ||
            order.order_number.toLowerCase().includes(normalizedSearch) ||
            order.customer.name.toLowerCase().includes(normalizedSearch) ||
            (order.customer.email ?? "")
              .toLowerCase()
              .includes(normalizedSearch)
        )
        .map(orderSummary)
        .sort((left, right) => {
          switch (query.sort) {
            case "ordered_at_asc":
              return left.ordered_at.localeCompare(right.ordered_at);
            case "total_desc":
              return right.total_minor - left.total_minor;
            case "total_asc":
              return left.total_minor - right.total_minor;
            default:
              return right.ordered_at.localeCompare(left.ordered_at);
          }
        });
      return paginate(items, query.page, query.page_size);
    },
    getById: async (
      organizationId: string,
      orderId: string,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const order = mockOrders.find((item) => item.id === orderId);
      if (!order) throw notFound("Order");
      return order;
    },
    updateStatus: async (
      organizationId: string,
      orderId: string,
      status: OrderStatus,
      _ifMatch: string,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const order = mockOrders.find((item) => item.id === orderId);
      if (!order) throw notFound("Order");
      order.status = status;
      return structuredClone(order);
    },
    cancel: async (
      organizationId: string,
      orderId: string,
      _reason: string,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const order = mockOrders.find((item) => item.id === orderId);
      if (!order) throw notFound("Order");
      order.status = "cancelled";
      return structuredClone(order);
    },
    refund: async (
      organizationId: string,
      orderId: string,
      _reason: string,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const order = mockOrders.find((item) => item.id === orderId);
      if (!order) throw notFound("Order");
      order.status = "refunded";
      return structuredClone(order);
    }
  };

  customers = {
    list: async (
      organizationId: string,
      query: CustomerListQuery,
      signal?: AbortSignal
    ): Promise<PaginatedResponse<CustomerListItem>> => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const normalizedSearch = query.search?.trim().toLowerCase();
      const items = mockCustomers
        .filter((customer) => !query.status || customer.status === query.status)
        .filter(
          (customer) => !query.segment || customer.segment === query.segment
        )
        .filter(
          (customer) =>
            !normalizedSearch ||
            customer.name.toLowerCase().includes(normalizedSearch) ||
            (customer.email ?? "").toLowerCase().includes(normalizedSearch) ||
            (customer.company ?? "").toLowerCase().includes(normalizedSearch)
        )
        .sort((left, right) => {
          switch (query.sort) {
            case "total_spent_asc":
              return left.total_spent_minor - right.total_spent_minor;
            case "name_asc":
              return left.name.localeCompare(right.name);
            case "last_order_desc":
              return (right.last_order_at ?? "").localeCompare(
                left.last_order_at ?? ""
              );
            default:
              return right.total_spent_minor - left.total_spent_minor;
          }
        });
      return paginate(items, query.page, query.page_size);
    },
    getById: async (
      organizationId: string,
      customerId: string,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const customer = createMockCustomerDetail(customerId);
      if (!customer) throw notFound("Customer");
      return customer;
    },
    create: async (
      organizationId: string,
      input: CustomerCreateInput,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const now = new Date().toISOString();
      return {
        id: `mock-customer-${mockCustomers.length + 1}`,
        external_id: input.external_id ?? null,
        name: input.name,
        initials: input.name.slice(0, 2).toUpperCase(),
        email: input.email ?? null,
        company: input.company ?? null,
        status: input.status ?? "active",
        segment: "new" as const,
        acquired_at: now,
        total_spent_minor: 0,
        order_count: 0,
        last_order_at: null,
        version: 1,
        created_at: now,
        updated_at: now,
        archived_at: null
      };
    },
    update: async (
      organizationId: string,
      customerId: string,
      input: CustomerUpdateInput,
      _ifMatch: string,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const customer = mockCustomers.find((item) => item.id === customerId);
      if (!customer) throw notFound("Customer");
      Object.assign(customer, input, { version: customer.version + 1 });
      return structuredClone(customer);
    },
    archive: async (
      organizationId: string,
      customerId: string,
      _ifMatch: string,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      if (!mockCustomers.some((item) => item.id === customerId)) {
        throw notFound("Customer");
      }
    }
  };

  products = {
    list: async (
      organizationId: string,
      query: ProductListQuery,
      signal?: AbortSignal
    ): Promise<PaginatedResponse<ProductListItem>> => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const normalizedSearch = query.search?.trim().toLowerCase();
      const scale =
        query.range === "7d"
          ? 0.286
          : query.range === "30d"
            ? 1
            : query.range === "90d"
              ? 2.289
              : 6.025;
      const items = mockProducts
        .filter((product) => !query.status || product.status === query.status)
        .filter(
          (product) => !query.category || product.category === query.category
        )
        .filter(
          (product) =>
            !normalizedSearch ||
            product.name.toLowerCase().includes(normalizedSearch) ||
            product.sku.toLowerCase().includes(normalizedSearch)
        )
        .map((product) => ({
          ...product,
          units_sold: Math.max(1, Math.round(product.units_sold * scale)),
          revenue_minor: Math.round(product.revenue_minor * scale)
        }))
        .sort((left, right) => {
          switch (query.sort) {
            case "revenue_asc":
              return left.revenue_minor - right.revenue_minor;
            case "units_desc":
              return right.units_sold - left.units_sold;
            case "name_asc":
              return left.name.localeCompare(right.name);
            case "price_desc":
              return right.unit_price_minor - left.unit_price_minor;
            default:
              return right.revenue_minor - left.revenue_minor;
          }
        });
      return paginate(items, query.page, query.page_size);
    },
    getById: async (
      organizationId: string,
      productId: string,
      range: AnalyticsRange,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const product = createMockProductDetail(productId, range);
      if (!product) throw notFound("Product");
      return product;
    },
    create: async (
      organizationId: string,
      input: ProductCreateInput,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const now = new Date().toISOString();
      return {
        id: `mock-product-${mockProducts.length + 1}`,
        external_id: input.external_id ?? null,
        ...input,
        status: "active" as const,
        average_price_minor: null,
        units_sold: 0,
        revenue_minor: 0,
        version: 1,
        created_at: now,
        updated_at: now,
        archived_at: null
      };
    },
    update: async (
      organizationId: string,
      productId: string,
      input: ProductUpdateInput,
      _ifMatch: string,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const product = mockProducts.find((item) => item.id === productId);
      if (!product) throw notFound("Product");
      Object.assign(product, input, { version: product.version + 1 });
      return structuredClone(product);
    },
    archive: async (
      organizationId: string,
      productId: string,
      _ifMatch: string,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      if (!mockProducts.some((item) => item.id === productId)) {
        throw notFound("Product");
      }
    }
  };

  insights = {
    list: async (
      organizationId: string,
      query: Parameters<InsightForgeApi["insights"]["list"]>[1],
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const normalizedSearch = query.search?.trim().toLowerCase();
      const generatedAt = `2026-08-10T15:${String(30 + insightGeneration).padStart(2, "0")}:00Z`;
      const items = createMockInsights(query.range, generatedAt).filter(
        (insight) =>
          (!query.category || insight.category === query.category) &&
          (!query.severity || insight.severity === query.severity) &&
          (!normalizedSearch ||
            insight.title.toLowerCase().includes(normalizedSearch) ||
            insight.description.toLowerCase().includes(normalizedSearch))
      );
      return {
        organization_id: organizationId,
        range: query.range,
        generated_at: generatedAt,
        generation_mode: "deterministic" as const,
        items
      };
    },
    regenerate: async (
      organizationId: string,
      range: AnalyticsRange,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      insightGeneration += 1;
      const generatedAt = `2026-08-10T15:${String(30 + insightGeneration).padStart(2, "0")}:00Z`;
      const items = createMockInsights(range, generatedAt);
      return {
        organization_id: organizationId,
        range,
        generated_at: generatedAt,
        generation_mode: "deterministic" as const,
        generation_id: `insight-generation-${insightGeneration}`,
        status: "succeeded" as const,
        feedback: `${items.length} grounded insights were recalculated from the latest demo aggregates.`,
        items
      };
    }
  };

  askData = {
    getCapabilities: async (organizationId: string, signal?: AbortSignal) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      return mockAskCapabilities;
    },
    ask: async (
      organizationId: string,
      input: Parameters<InsightForgeApi["askData"]["ask"]>[1],
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const answer = createAskAnswer(input);
      askHistoryState.unshift(answer);
      return answer;
    },
    history: async (organizationId: string, signal?: AbortSignal) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      return askHistoryState.slice(0, 8);
    }
  };

  reports = {
    templates: async (organizationId: string, signal?: AbortSignal) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      return mockReportTemplates;
    },
    list: async (
      organizationId: string,
      query: Parameters<InsightForgeApi["reports"]["list"]>[1],
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const normalizedSearch = query.search?.trim().toLowerCase();
      return reportState
        .filter((report) => report.range === query.range)
        .filter((report) => !query.type || report.type === query.type)
        .filter((report) => !query.status || report.status === query.status)
        .filter(
          (report) =>
            !normalizedSearch ||
            report.name.toLowerCase().includes(normalizedSearch) ||
            report.summary?.toLowerCase().includes(normalizedSearch)
        )
        .sort((left, right) => right.created_at.localeCompare(left.created_at));
    },
    create: async (
      organizationId: string,
      input: Parameters<InsightForgeApi["reports"]["create"]>[1],
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      reportSequence += 1;
      const reportTemplate = mockReportTemplates.find(
        (item) => item.type === input.type
      )!;
      const generatedAt = `2026-08-10T16:${String(reportSequence).padStart(2, "0")}:00Z`;
      const report: ReportRecord = {
        id: `report-demo-${reportSequence}`,
        name: `${reportTemplate.name} · ${rangeLabels[input.range]}`,
        type: input.type,
        status: "ready",
        format: input.format,
        range: input.range,
        source_revision: "demo-seed-2026-08",
        created_by: "Jordan Blake",
        created_at: generatedAt,
        generated_at: generatedAt,
        expires_at: "2026-09-09T16:00:00Z",
        row_count:
          input.type === "sales"
            ? 304
            : input.type === "customer"
              ? 142
              : input.type === "product_performance"
                ? 10
                : 38,
        summary: `The ${(reportTemplate.name ?? reportTemplate.label ?? "report").toLowerCase()} completed using source revision demo-seed-2026-08.`
      };
      reportState.unshift(report);
      return report;
    },
    download: async (
      organizationId: string,
      reportId: string,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const report = reportState.find((item) => item.id === reportId);
      if (!report) throw notFound("Report");
      if (report.status !== "ready") {
        throw new ApiProblemError({
          title: "Report unavailable",
          detail: "Only ready reports can be downloaded.",
          status: 409,
          code: "report_not_ready",
          request_id: "req-demo-report-409"
        });
      }
      const safeBaseName = report.name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
      if (report.format === "json") {
        return {
          filename: `${safeBaseName}.json`,
          mime_type: "application/json" as const,
          content: JSON.stringify(
            {
              report_id: report.id,
              name: report.name,
              range: report.range,
              summary: report.summary,
              source_revision: "demo-seed-2026-08"
            },
            null,
            2
          )
        };
      }
      return {
        filename: `${safeBaseName}.csv`,
        mime_type: "text/csv" as const,
        content:
          'metric,value,comparison\n"Net revenue","$81,800","+18.4%"\n"Orders","304","+5.4%"\n"Customers","142","+8.1%"\n'
      };
    }
  };

  imports = {
    templates: async (signal?: AbortSignal) => {
      await waitForMock(signal);
      return mockImportTemplates;
    },
    history: async (organizationId: string, signal?: AbortSignal) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      return importHistoryState.slice(0, 10);
    },
    validate: async (
      organizationId: string,
      input: CsvUploadInput,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      return validateCsv(input);
    },
    commit: async (
      organizationId: string,
      importId: string,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const preview = pendingImports.get(importId);
      if (!preview || preview.status !== "ready") {
        throw new ApiProblemError({
          title: "Import cannot be confirmed",
          detail: "Resolve validation errors before confirming this import.",
          status: 409,
          code: "import_not_ready",
          request_id: "req-demo-import-409"
        });
      }
      const record = {
        id: preview.import_id,
        kind: preview.kind,
        filename: preview.filename,
        status: "completed" as const,
        total_rows: preview.total_rows,
        imported_rows: preview.valid_rows,
        error_rows: 0,
        created_at: "2026-08-10T15:40:00Z",
        completed_at: "2026-08-10T15:41:00Z"
      };
      importHistoryState.unshift(record);
      pendingImports.delete(importId);
      return record;
    }
  };

  onboarding = {
    get: async (organizationId: string, signal?: AbortSignal) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      return cloneAccountValue({
        ...onboardingState,
        organization_id: organizationId
      });
    },
    saveOrganization: async (
      organizationId: string,
      input: Parameters<InsightForgeApi["onboarding"]["saveOrganization"]>[1],
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOwner(organizationId, "edit onboarding organization details");
      const name = input.name.trim();
      const slug = input.slug.trim().toLowerCase();
      if (name.length < 2 || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) {
        throw accountProblem(
          "Check organization details",
          "Enter an organization name and a lowercase slug using letters, numbers, and single hyphens.",
          422,
          "invalid_organization_details"
        );
      }
      onboardingState = {
        ...onboardingState,
        organization_id: organizationId,
        current_step: "data",
        organization: { ...input, name, slug }
      };
      return cloneAccountValue(onboardingState);
    },
    chooseData: async (
      organizationId: string,
      input: Parameters<InsightForgeApi["onboarding"]["chooseData"]>[1],
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOwner(organizationId, "choose onboarding data");
      onboardingState = {
        ...onboardingState,
        organization_id: organizationId,
        current_step: "profile",
        data_choice: input.choice
      };
      return cloneAccountValue(onboardingState);
    },
    saveProfile: async (
      organizationId: string,
      input: Parameters<InsightForgeApi["onboarding"]["saveProfile"]>[1],
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOwner(organizationId, "save onboarding preferences");
      if (input.profile.display_name.trim().length < 2) {
        throw accountProblem(
          "Check profile details",
          "Enter the name you want teammates to see.",
          422,
          "invalid_profile"
        );
      }
      onboardingState = {
        ...onboardingState,
        organization_id: organizationId,
        current_step: "complete",
        profile: {
          ...input.profile,
          display_name: input.profile.display_name.trim()
        },
        preferences: cloneAccountValue(input.preferences)
      };
      return cloneAccountValue(onboardingState);
    },
    complete: async (organizationId: string, signal?: AbortSignal) => {
      await waitForMock(signal);
      assertOwner(organizationId, "complete onboarding");
      if (!onboardingState.data_choice) {
        throw accountProblem(
          "Onboarding is incomplete",
          "Choose how to populate the workspace before completing setup.",
          409,
          "onboarding_incomplete"
        );
      }
      onboardingState = {
        ...onboardingState,
        organization_id: organizationId,
        current_step: "complete",
        completed_at: "2026-08-10T18:45:00Z"
      };
      settingsState = {
        ...settingsState,
        organization_id: organizationId,
        profile: {
          ...settingsState.profile,
          ...onboardingState.profile
        },
        organization: {
          ...settingsState.organization,
          ...onboardingState.organization
        },
        preferences: cloneAccountValue(onboardingState.preferences)
      };
      return cloneAccountValue(onboardingState);
    }
  };

  team = {
    previewInvitation: async (token: string, signal?: AbortSignal) => {
      await waitForMock(signal);
      if (token.length < 32) throw notFound("Invitation");
      return {
        organization_name: mockOrganizations[0]!.name,
        email_hint: "j***@example.com",
        role: "member",
        expires_at: "2026-08-20T12:00:00Z"
      };
    },
    acceptInvitation: async (token: string, signal?: AbortSignal) => {
      await waitForMock(signal);
      if (token.length < 32) throw notFound("Invitation");
      return {
        organization_id: mockOrganizations[0]!.id,
        organization_name: mockOrganizations[0]!.name,
        member: { ...teamMemberState[0]!, is_current_user: true }
      };
    },
    getOverview: async (organizationId: string, signal?: AbortSignal) => {
      await waitForMock(signal);
      const organization = organizationFor(organizationId);
      return {
        organization_id: organizationId,
        current_user_role: organization.role,
        can_manage_members: organization.role !== "member",
        demo_policy:
          "Role and removal changes are simulated locally. Sending external invitations is disabled in demo mode.",
        members: cloneAccountValue(teamMemberState),
        invitations: cloneAccountValue(teamInvitationState)
      };
    },
    invite: async (
      organizationId: string,
      input: Parameters<InsightForgeApi["team"]["invite"]>[1],
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertCanManageTeam(organizationId);
      void input;
      throw demoPolicyProblem("Sending an external invitation");
    },
    changeRole: async (
      organizationId: string,
      memberId: string,
      role: TeamMember["role"],
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOwner(organizationId, "change team roles");
      const member = teamMemberState.find((item) => item.id === memberId);
      if (!member) throw notFound("Team member");
      if (role === "owner" && member.role !== "owner") {
        throw demoPolicyProblem("Transferring workspace ownership");
      }
      if (member.role === "owner" && role !== "owner") {
        const ownerCount = teamMemberState.filter(
          (item) => item.role === "owner"
        ).length;
        if (ownerCount <= 1) {
          throw accountProblem(
            "Final owner required",
            "The workspace must keep at least one owner. Add another owner before changing this role.",
            409,
            "final_owner_required"
          );
        }
      }
      member.role = role;
      return cloneAccountValue(member);
    },
    removeMember: async (
      organizationId: string,
      memberId: string,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertCanManageTeam(organizationId);
      const organization = organizationFor(organizationId);
      const memberIndex = teamMemberState.findIndex(
        (item) => item.id === memberId
      );
      if (memberIndex < 0) throw notFound("Team member");
      const member = teamMemberState[memberIndex]!;
      if (member.role === "owner") {
        throw accountProblem(
          "Final owner required",
          "The final workspace owner cannot be removed.",
          409,
          "final_owner_required"
        );
      }
      if (member.is_current_user) {
        throw accountProblem(
          "Member cannot be removed",
          "Use the leave-workspace flow to remove your own membership.",
          409,
          "self_removal_not_allowed"
        );
      }
      if (organization.role === "admin" && member.role !== "member") {
        throw accountProblem(
          "Owner permission required",
          "Admins can remove members, but only owners can remove admins.",
          403,
          "owner_permission_required"
        );
      }
      teamMemberState.splice(memberIndex, 1);
    },
    resendInvitation: async (
      organizationId: string,
      invitationId: string,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertCanManageTeam(organizationId);
      if (!teamInvitationState.some((item) => item.id === invitationId)) {
        throw notFound("Invitation");
      }
      throw demoPolicyProblem("Resending an external invitation");
    },
    revokeInvitation: async (
      organizationId: string,
      invitationId: string,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertCanManageTeam(organizationId);
      const invitation = teamInvitationState.find(
        (item) => item.id === invitationId
      );
      if (!invitation) throw notFound("Invitation");
      if (invitation.status === "revoked") {
        throw accountProblem(
          "Invitation already revoked",
          "This invitation is no longer active.",
          409,
          "invitation_already_revoked"
        );
      }
      invitation.status = "revoked";
    }
  };

  billing = {
    getOverview: async (organizationId: string, signal?: AbortSignal) => {
      await waitForMock(signal);
      const organization = organizationFor(organizationId);
      return {
        organization_id: organizationId,
        subscription: cloneAccountValue(billingSubscriptionState),
        plans: cloneAccountValue(mockBillingPlans),
        usage: cloneAccountValue(billingUsageState),
        invoices: cloneAccountValue(mockBillingInvoices),
        demo_notice:
          "Billing is simulated in this isolated demo. Plan changes collect no payment and create no provider checkout.",
        can_manage_billing: organization.role === "owner"
      };
    },
    changePlan: async (
      organizationId: string,
      planId: BillingPlanId,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOwner(organizationId, "change the workspace plan");
      const plan = mockBillingPlans.find((item) => item.id === planId);
      if (!plan) throw notFound("Plan");
      billingSubscriptionState = {
        ...billingSubscriptionState,
        plan: plan.id
      };
      billingUsageState = billingUsageState.map((usage) => ({
        ...usage,
        limit: plan.limits[usage.id]
      }));
      return {
        subscription: cloneAccountValue(billingSubscriptionState),
        feedback: `${plan.name} is now the simulated plan. No payment was collected.`,
        charged_amount_minor: 0 as const
      };
    }
  };

  settings = {
    get: async (organizationId: string, signal?: AbortSignal) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      return cloneAccountValue({
        ...settingsState,
        organization_id: organizationId
      });
    },
    updateProfile: async (
      organizationId: string,
      input: Parameters<InsightForgeApi["settings"]["updateProfile"]>[1],
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      const displayName = input.display_name.trim();
      if (displayName.length < 2) {
        throw accountProblem(
          "Check profile details",
          "Enter a full name with at least two characters.",
          422,
          "invalid_profile"
        );
      }
      settingsState = {
        ...settingsState,
        organization_id: organizationId,
        profile: {
          ...settingsState.profile,
          display_name: displayName,
          locale: input.locale,
          time_zone: input.time_zone
        }
      };
      mockSession.user.display_name = displayName;
      return cloneAccountValue(settingsState);
    },
    updateOrganization: async (
      organizationId: string,
      input: Parameters<InsightForgeApi["settings"]["updateOrganization"]>[1],
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      const organization = organizationFor(organizationId);
      if (organization.role === "member") {
        throw accountProblem(
          "Permission required",
          "Only workspace owners and admins can edit organization details.",
          403,
          "insufficient_permission"
        );
      }
      const name = input.name.trim();
      if (name.length < 2) {
        throw accountProblem(
          "Check organization details",
          "Enter an organization name with at least two characters.",
          422,
          "invalid_organization_details"
        );
      }
      settingsState = {
        ...settingsState,
        organization_id: organizationId,
        organization: {
          ...settingsState.organization,
          name,
          timezone: input.timezone
        }
      };
      organization.name = name;
      organization.timezone = input.timezone;
      return cloneAccountValue(settingsState);
    },
    updatePreferences: async (
      organizationId: string,
      input: AccountPreferences,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      settingsState = {
        ...settingsState,
        organization_id: organizationId,
        preferences: cloneAccountValue(input)
      };
      return cloneAccountValue(settingsState);
    },
    changePassword: async (
      organizationId: string,
      input: Parameters<InsightForgeApi["settings"]["changePassword"]>[1],
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      void input;
      throw demoPolicyProblem("Changing credentials");
    },
    requestExport: async (organizationId: string, signal?: AbortSignal) => {
      await waitForMock(signal);
      assertOrganization(organizationId);
      return {
        filename: "northstar-workspace-export-2026-08-10.json",
        mime_type: "application/json" as const,
        content: JSON.stringify(
          {
            exported_at: "2026-08-10T18:47:00Z",
            organization: settingsState.organization,
            profile: settingsState.profile,
            preferences: settingsState.preferences,
            team_members: teamMemberState.map(({ id, role, joined_at }) => ({
              id,
              role,
              joined_at
            })),
            billing: {
              provider: "demo",
              plan: billingSubscriptionState.plan,
              payment_collected: false
            }
          },
          null,
          2
        ),
        generated_at: "2026-08-10T18:47:00Z"
      };
    },
    deleteOrganization: async (
      organizationId: string,
      confirmation: string,
      signal?: AbortSignal
    ) => {
      await waitForMock(signal);
      assertOwner(organizationId, "delete the workspace");
      void confirmation;
      throw demoPolicyProblem("Deleting an organization");
    }
  };
}

export const insightForgeApi: InsightForgeApi = new MockInsightForgeApi();
